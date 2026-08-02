from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.plugin import LoggerPlugin
from core.population import PopulationTemplate
from core.simulator import LodusSimulation

if TYPE_CHECKING:
    from plugins.time_actions.levy_walk_v2_plugin import LevyWalkV2Plugin


class LevyWalkV2Logger(LoggerPlugin):
    """Incremental demand, lifecycle, and invariant audit for Levy Walk V2."""

    DEMAND_COLUMNS = [
        "simulation_step", "cycle_step", "cycle", "group", "node_type",
        "origin", "original_home", "original_population",
        "requested_destination", "receiving_destination", "requested",
        "fulfilled", "unmet", "reason", "packet_size", "blob_count",
        "destination_rerouted", "reroute_reason", "reroute_distance",
        "movement_distance", "receiving_load", "expiry_step",
    ]
    MOVEMENT_COLUMNS = [
        "event", "commute_id", "simulation_step", "cycle_step", "cycle",
        "group", "origin", "destination", "requested_destination",
        "receiving_destination", "original_home", "expiry_step", "quantity",
        "blob_count", "distance", "rerouted", "reroute_reason",
        "reroute_distance",
    ]
    STEP_COLUMNS = [
        "simulation_step", "cycle_step", "cycle", "group", "requested",
        "fulfilled", "unmet", "packet_count", "actual_blob_fragments",
        "departures", "population_moved", "returns", "population_returned",
        "temporary_returns", "return_blocked", "repatriations",
        "occupancy", "outbound_traveler_distance", "return_traveler_distance",
        "temporary_home_traveler_distance", "repatriation_traveler_distance",
        "destination_reroutes", "rerouted_fulfilled", "receiving_load",
    ]

    VALID_UNMET_REASONS = {
        "origin_disabled",
        "insufficient_population",
        "destination_disabled",
        "anticipated_destination_disable",
        "no_enabled_alternative",
        "no_destination_candidate",
    }

    def __init__(self):
        super().__init__()
        self.simulation: LodusSimulation | None = None
        self.plugin: LevyWalkV2Plugin | None = None
        self.env_graph = None
        self.sim_step = -1
        self.cycle_length = 24
        self.base_path = Path()
        self.data_path = Path()
        self.initial_population = 0
        self.minimum_population = 0
        self.maximum_population = 0
        self._files = []
        self._writers: dict[str, csv.DictWriter] = {}
        self._step_rows: list[dict[str, Any]] = []
        self._summary: dict[str, dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        self._cycle_requested: dict[tuple[int, str], int] = defaultdict(int)
        self._hour_requested: dict[tuple[str, int], int] = defaultdict(int)
        self._departures: dict[int, dict[str, int]] = {}
        self._returned: dict[int, int] = defaultdict(int)
        self._duration_errors: list[dict[str, Any]] = []
        self._blocked_commutes: set[int] = set()
        self._packet_errors: list[dict[str, Any]] = []
        self._unmet_reason_errors: list[dict[str, Any]] = []
        self._reroute_errors: list[dict[str, Any]] = []
        self._movement_violation_count = 0
        self._record_counts = defaultdict(int)

    def load_plugin(self, simulation: LodusSimulation):
        self.simulation = simulation
        self.env_graph = simulation.env_graph
        self.cycle_length = simulation.time_status.cycle_length
        plugins = [
            plugin
            for plugin in simulation.plugin_controller.loaded_action_plugins
            if getattr(plugin, "ACTION_TYPE", None) == "levy_walk_v2"
        ]
        if not plugins:
            raise ValueError("LevyWalkV2Logger requires LevyWalkV2Plugin")
        self.plugin = plugins[0]
        self.base_path = Path("output_logs") / simulation.experiment_name
        self.data_path = self.base_path / "data_frames"
        self.initial_population = self.env_graph.get_population_size()
        self.minimum_population = self.initial_population
        self.maximum_population = self.initial_population
        self.env_graph.movement_logger_dict["levy_walk_v2_enabled_audit"] = (
            self._audit_movement
        )

    def setup_logger(self):
        self.data_path.mkdir(parents=True, exist_ok=True)
        self._open_writer("demand", "levy_v2_demand.csv", self.DEMAND_COLUMNS)
        self._open_writer(
            "movements", "levy_v2_movements.csv", self.MOVEMENT_COLUMNS
        )

    def _open_writer(self, key: str, filename: str, columns: list[str]):
        stream = (self.data_path / filename).open(
            "w", encoding="utf-8-sig", newline=""
        )
        writer = csv.DictWriter(stream, fieldnames=columns, delimiter=";")
        writer.writeheader()
        self._files.append(stream)
        self._writers[key] = writer

    def update_time_step(self, cycle_step: int, simulation_step: int):
        self.sim_step = simulation_step

    def log_simulation_step(self):
        self._drain_records()
        population = self.env_graph.get_population_size()
        self.minimum_population = min(self.minimum_population, population)
        self.maximum_population = max(self.maximum_population, population)

    def _drain_records(self):
        if self.plugin is None:
            return
        demands = self.plugin.demand_records
        movements = self.plugin.movement_records
        self.plugin.demand_records = []
        self.plugin.movement_records = []

        demand_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
        movement_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in demands:
            self._writers["demand"].writerow(
                {column: record.get(column, "") for column in self.DEMAND_COLUMNS}
            )
            self._record_counts["demand"] += 1
            group = record["group"]
            demand_by_group[group].append(record)
            self._cycle_requested[(int(record["cycle"]), group)] += int(
                record["requested"]
            )
            self._hour_requested[(group, int(record["cycle_step"]))] += int(
                record["requested"]
            )
            if not 0 < int(record["packet_size"]) <= self.plugin.config["packet_size"]:
                self._packet_errors.append(record)
            if int(record["unmet"]) > 0 and record["reason"] not in self.VALID_UNMET_REASONS:
                self._unmet_reason_errors.append(record)
            if record.get("destination_rerouted"):
                requested = self.env_graph.get_node_by_complete_name(
                    record["requested_destination"]
                )
                receiving = self.env_graph.get_node_by_complete_name(
                    record["receiving_destination"]
                )
                if (
                    requested.id == receiving.id
                    or requested.node_type != receiving.node_type
                    or not receiving.is_enabled()
                    or not record.get("reroute_reason")
                ):
                    self._reroute_errors.append(record)

        for record in movements:
            self._writers["movements"].writerow(
                {column: record.get(column, "") for column in self.MOVEMENT_COLUMNS}
            )
            self._record_counts["movement"] += 1
            group = record["group"]
            movement_by_group[group].append(record)
            commute_id = int(record["commute_id"])
            quantity = int(record["quantity"])
            if record["event"] == "departure":
                self._departures[commute_id] = {
                    "expiry_step": int(record["expiry_step"]),
                    "quantity": quantity,
                    "group": group,
                }
            elif record["event"] in {"return", "temporary_return"}:
                self._returned[commute_id] += quantity
                departure = self._departures.get(commute_id)
                if departure is None or (
                    int(record["simulation_step"]) != departure["expiry_step"]
                    and commute_id not in self._blocked_commutes
                ):
                    self._duration_errors.append(record)
            elif record["event"] == "return_blocked":
                self._blocked_commutes.add(commute_id)

        groups = set(demand_by_group) | set(movement_by_group)
        for group in sorted(groups):
            group_demands = demand_by_group[group]
            group_movements = movement_by_group[group]
            row = {
                "simulation_step": self.sim_step,
                "cycle_step": self.sim_step % self.cycle_length,
                "cycle": self.sim_step // self.cycle_length,
                "group": group,
                "requested": sum(int(item["requested"]) for item in group_demands),
                "fulfilled": sum(int(item["fulfilled"]) for item in group_demands),
                "unmet": sum(int(item["unmet"]) for item in group_demands),
                "packet_count": len(group_demands),
                "actual_blob_fragments": sum(int(item["blob_count"]) for item in group_demands),
                "departures": sum(item["event"] == "departure" for item in group_movements),
                "population_moved": self._event_quantity(group_movements, "departure"),
                "returns": sum(item["event"] == "return" for item in group_movements),
                "population_returned": self._event_quantity(group_movements, "return"),
                "temporary_returns": self._event_quantity(group_movements, "temporary_return"),
                "return_blocked": self._event_quantity(group_movements, "return_blocked"),
                "repatriations": self._event_quantity(group_movements, "repatriation"),
                "occupancy": self._group_occupancy(group),
                "outbound_traveler_distance": self._event_distance(group_movements, "departure"),
                "return_traveler_distance": self._event_distance(group_movements, "return"),
                "temporary_home_traveler_distance": self._event_distance(group_movements, "temporary_return"),
                "repatriation_traveler_distance": self._event_distance(group_movements, "repatriation"),
                "destination_reroutes": sum(bool(item.get("destination_rerouted")) for item in group_demands),
                "rerouted_fulfilled": sum(int(item["fulfilled"]) for item in group_demands if item.get("destination_rerouted")),
                "receiving_load": max((int(item["receiving_load"]) for item in group_demands), default=0),
            }
            self._step_rows.append(row)
            summary = self._summary[group]
            for key in self.STEP_COLUMNS[4:]:
                if key == "receiving_load":
                    summary[key] = max(summary[key], row[key])
                else:
                    summary[key] += row[key]

    @staticmethod
    def _event_quantity(records, event: str) -> int:
        return sum(int(item["quantity"]) for item in records if item["event"] == event)

    @staticmethod
    def _event_distance(records, event: str) -> float:
        return sum(
            int(item["quantity"]) * float(item["distance"])
            for item in records
            if item["event"] == event
        )

    def _group_occupancy(self, group: str) -> int:
        return self.env_graph.get_population_size(
            PopulationTemplate(
                traceable_characteristics={
                    self.plugin.ACTIVE: True,
                    self.plugin.GROUP: group,
                }
            )
        )

    def _audit_movement(self, origin, destination, blobs):
        is_levy_v2 = any(
            blob.get_traceable_characteristic(self.plugin.COMMUTE_ID) != -1
            for blob in blobs
        )
        if is_levy_v2 and (not origin.is_enabled() or not destination.is_enabled()):
            self._movement_violation_count += 1

    def stop_logger(self):
        self._drain_records()
        self._write_aggregates()
        for stream in self._files:
            stream.close()
        self.env_graph.movement_logger_dict.pop("levy_walk_v2_enabled_audit", None)

    def _write_aggregates(self):
        self._write_rows("levy_v2_step_group.csv", self.STEP_COLUMNS, self._step_rows)
        summary_columns = [
            "group", "original_population", "cycle_attendance_rate",
            "exact_cycle_demand", "requested", "fulfilled", "unmet",
            "fulfillment_rate", *self.STEP_COLUMNS[7:],
            "mean_outbound_distance", "mean_return_distance",
        ]
        summary_rows = []
        for group, group_config in self.plugin.groups.items():
            values = self._summary[group]
            original = sum(
                self.plugin._original_population(home, group)
                for home in self.plugin._home_nodes
            )
            requested = values["requested"]
            moved = values["population_moved"]
            summary_rows.append(
                {
                    "group": group,
                    "original_population": original,
                    "cycle_attendance_rate": group_config["cycle_attendance_rate"],
                    "exact_cycle_demand": self.plugin.get_cycle_target(group),
                    **{key: values[key] for key in self.STEP_COLUMNS[4:]},
                    "fulfillment_rate": values["fulfilled"] / requested if requested else 1.0,
                    "mean_outbound_distance": values["outbound_traveler_distance"] / moved if moved else 0.0,
                    "mean_return_distance": (
                        values["return_traveler_distance"]
                        / values["population_returned"]
                        if values["population_returned"]
                        else 0.0
                    ),
                }
            )
        self._write_rows("levy_v2_summary.csv", summary_columns, summary_rows)

        weights_rows = []
        for group, config in self.plugin.groups.items():
            for hour, weight in config["hourly_weights"].items():
                weights_rows.append(
                    {"group": group, "hour": hour, "normalized_weight": weight}
                )
        self._write_rows(
            "levy_v2_hourly_weights.csv",
            ["group", "hour", "normalized_weight"],
            weights_rows,
        )
        validation = self._validation_results()
        (self.data_path / "levy_v2_validation.json").write_text(
            json.dumps(validation, indent=2, ensure_ascii=False) + "\n",
            encoding="utf8",
        )

    def _validation_results(self) -> dict[str, Any]:
        cycle_checks = []
        for cycle in range(self.simulation.time_status.total_cycles):
            for group in self.plugin.groups:
                expected = self.plugin.get_cycle_target(group)
                actual = self._cycle_requested[(cycle, group)]
                cycle_checks.append(
                    {
                        "cycle": cycle, "group": group, "expected": expected,
                        "actual": actual, "passed": actual == expected,
                    }
                )
        normalized = {
            group: abs(sum(config["hourly_weights"].values()) - 1.0) < 1e-12
            for group, config in self.plugin.groups.items()
        }
        incomplete = [
            {"commute_id": commute_id, **departure, "returned": self._returned[commute_id]}
            for commute_id, departure in self._departures.items()
            if departure["expiry_step"]
            < self.simulation.time_status.cycle_length
            * self.simulation.time_status.total_cycles
            and self._returned[commute_id] != departure["quantity"]
        ]
        final_population = self.env_graph.get_population_size()
        checks = {
            "population_conserved": final_population == self.initial_population,
            "population_constant_at_logged_steps": self.minimum_population == self.maximum_population == self.initial_population,
            "exact_cycle_demand": all(item["passed"] for item in cycle_checks),
            "hourly_weights_normalized": all(normalized.values()),
            "packet_size_valid": not self._packet_errors,
            "no_duplicate_attendance": self.plugin.duplicate_attendance_population == 0,
            "all_unmet_has_valid_reason": not self._unmet_reason_errors,
            "no_disabled_node_movement": self._movement_violation_count == 0,
            "stay_durations_valid": not self._duration_errors,
            "completed_commutes_returned": not incomplete,
            "rerouted_destinations_valid": not self._reroute_errors,
            "legacy_levy_not_loaded": not any(
                plugin.__class__.__name__ == "LevyWalkPlugin"
                for plugin in self.simulation.plugin_controller.loaded_action_plugins
            ),
        }
        return {
            "passed": all(checks.values()),
            "checks": checks,
            "initial_population": self.initial_population,
            "final_population": final_population,
            "minimum_population": self.minimum_population,
            "maximum_population": self.maximum_population,
            "record_counts": dict(self._record_counts),
            "normalized_hourly_weights": normalized,
            "cycle_demand": cycle_checks,
            "packet_errors": self._packet_errors[:100],
            "unmet_reason_errors": self._unmet_reason_errors[:100],
            "duration_errors": self._duration_errors[:100],
            "incomplete_commutes": incomplete[:100],
            "reroute_errors": self._reroute_errors[:100],
            "movement_violation_count": self._movement_violation_count,
            "duplicate_attendance_population": self.plugin.duplicate_attendance_population,
        }

    def _write_rows(self, filename: str, columns: list[str], rows):
        with (self.data_path / filename).open(
            "w", encoding="utf-8-sig", newline=""
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)

    def unload_plugin(self):
        if self.env_graph is not None:
            self.env_graph.movement_logger_dict.pop("levy_walk_v2_enabled_audit", None)
