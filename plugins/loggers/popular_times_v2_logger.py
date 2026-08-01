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
    from plugins.time_actions.popular_times_v2_plugin import PopularTimesV2Plugin


class PopularTimesV2Logger(LoggerPlugin):
    """Incremental audit logger for Popular Times V2 mobility studies."""

    DEMAND_COLUMNS = [
        "simulation_step",
        "cycle_step",
        "cycle",
        "week",
        "weekday",
        "region",
        "destination",
        "requested_destination",
        "receiving_destination",
        "node_type",
        "paired_home",
        "destination_enabled",
        "requested",
        "fulfilled",
        "unmet",
        "reason",
        "destination_rerouted",
        "reroute_reason",
        "reroute_distance",
        "receiving_load",
        "destination_occupancy",
    ]
    VISIT_COLUMNS = [
        "event",
        "visit_id",
        "simulation_step",
        "cycle_step",
        "cycle",
        "week",
        "expiry_step",
        "origin",
        "destination",
        "requested_destination",
        "receiving_destination",
        "paired_home",
        "poi_type",
        "quantity",
        "distance",
        "rerouted",
        "reroute_reason",
        "reroute_distance",
        "destination_was_rerouted",
    ]
    STEP_COLUMNS = [
        "simulation_step",
        "cycle_step",
        "cycle",
        "week",
        "weekday",
        "node_type",
        "poi_count",
        "closed_poi_count",
        "disabled_destination_count",
        "requested",
        "fulfilled",
        "unmet",
        "visit_starts",
        "travelers_started",
        "releases",
        "travelers_released",
        "release_reroutes",
        "release_blocked",
        "occupied_destinations",
        "destination_occupancy",
        "travel_distance",
        "reroute_events",
        "rerouted_requested",
        "rerouted_fulfilled",
        "rerouted_unmet",
        "reroute_traveler_distance",
    ]
    REROUTING_COLUMNS = [
        "simulation_step",
        "cycle_step",
        "cycle",
        "week",
        "weekday",
        "node_type",
        "requested_destination",
        "receiving_destination",
        "reroute_reason",
        "requested",
        "fulfilled",
        "unmet",
        "reroute_distance",
        "reroute_traveler_distance",
        "receiving_load",
        "destination_occupancy",
    ]
    MOVEMENT_VIOLATION_COLUMNS = [
        "simulation_step",
        "origin",
        "destination",
        "origin_enabled",
        "destination_enabled",
        "quantity",
        "popular_times_visit",
        "mandatory_release_exception",
    ]

    def __init__(self):
        super().__init__()
        self.simulation: LodusSimulation | None = None
        self.plugin: PopularTimesV2Plugin | None = None
        self.env_graph = None
        self.config: dict[str, Any] = {}
        self.sim_step = -1
        self.cycle_length = 24
        self.initial_population = 0
        self.minimum_population = 0
        self.maximum_population = 0
        self._files = []
        self._writers: dict[str, csv.DictWriter] = {}
        self._step_rows: list[dict[str, Any]] = []
        self._summary: dict[str, dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        self._weekly_requested: dict[tuple[int, str], int] = defaultdict(int)
        self._hourly_requested: dict[tuple[str, int, int], int] = defaultdict(int)
        self._od: dict[tuple[str, str, str], dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        self._visit_starts: dict[int, dict[str, int]] = {}
        self._visit_duration_errors: list[dict[str, int]] = []
        self._reroute_errors: list[dict[str, Any]] = []
        self._rerouting_summary: dict[
            tuple[str, str, str], dict[str, float]
        ] = defaultdict(lambda: defaultdict(float))
        self._closed_request_errors = 0
        self._unmet_reason_errors = 0
        self._movement_violation_count = 0
        self._mandatory_release_exception_count = 0
        self._demand_record_count = 0
        self._raw_demand_record_count = 0
        self._visit_record_count = 0

    def load_plugin(self, simulation: LodusSimulation):
        self.simulation = simulation
        self.env_graph = simulation.env_graph
        self.cycle_length = simulation.time_status.cycle_length
        self.config = dict(
            simulation.experiment_config.get("popular_times_v2_logger", {})
        )
        plugins = [
            plugin
            for plugin in simulation.plugin_controller.loaded_action_plugins
            if getattr(plugin, "ACTION_TYPE", None) == "popular_times_v2"
        ]
        if not plugins:
            raise ValueError(
                "PopularTimesV2Logger requires PopularTimesV2Plugin to be loaded first"
            )
        self.plugin = plugins[0]
        self.base_path = Path("output_logs") / simulation.experiment_name
        self.data_path = self.base_path / "data_frames"
        self.initial_population = self.env_graph.get_population_size()
        self.minimum_population = self.initial_population
        self.maximum_population = self.initial_population
        self.env_graph.movement_logger_dict[
            "popular_times_v2_enabled_audit"
        ] = self._audit_movement

    def setup_logger(self):
        self.data_path.mkdir(parents=True, exist_ok=True)
        self._open_writer("demand", "popular_times_demand.csv", self.DEMAND_COLUMNS)
        self._open_writer("visits", "popular_times_visits.csv", self.VISIT_COLUMNS)
        self._open_writer(
            "violations",
            "popular_times_disabled_movement.csv",
            self.MOVEMENT_VIOLATION_COLUMNS,
        )
        self._open_writer(
            "rerouting",
            "popular_times_rerouting.csv",
            self.REROUTING_COLUMNS,
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
        demand_records = self.plugin.demand_records
        visit_records = self.plugin.visit_records
        self.plugin.demand_records = []
        self.plugin.visit_records = []

        demand_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        destinations: dict[str, str] = {}
        for record in demand_records:
            self._demand_record_count += 1
            node_type = record["node_type"]
            demand_by_type[node_type].append(record)
            receiving_destination = record.get(
                "receiving_destination", record["destination"]
            )
            destinations[receiving_destination] = node_type
            week = record["simulation_step"] // (7 * self.cycle_length)
            self._weekly_requested[(week, node_type)] += record["requested"]
            self._hourly_requested[
                (node_type, record["weekday"], record["cycle_step"])
            ] += record["requested"]
            summary = self._summary[node_type]
            for field in ("requested", "fulfilled", "unmet"):
                summary[field] += record[field]
            summary["poi_action_count"] += 1
            if record["reason"] == "closed":
                summary["closed_poi_count"] += 1
                if record["requested"] != 0:
                    self._closed_request_errors += 1
            if record["reason"] == "disabled_destination":
                summary["disabled_destination_count"] += 1
            if record["unmet"] > 0 and record["reason"] not in {
                "disabled_destination",
                "no_enabled_alternative",
                "no_enabled_origins",
                "insufficient_population",
            }:
                self._unmet_reason_errors += 1
            if record.get("destination_rerouted", False):
                summary["reroute_events"] += 1
                summary["rerouted_requested"] += record["requested"]
                summary["rerouted_fulfilled"] += record["fulfilled"]
                summary["rerouted_unmet"] += record["unmet"]
                summary["reroute_traveler_distance"] += (
                    record["fulfilled"] * float(record["reroute_distance"])
                )
                requested_node = self.env_graph.get_node_by_complete_name(
                    record["requested_destination"]
                )
                receiving_node = self.env_graph.get_node_by_complete_name(
                    receiving_destination
                )
                if (
                    requested_node.id == receiving_node.id
                    or requested_node.node_type != receiving_node.node_type
                    or not receiving_node.is_enabled()
                    or not record.get("reroute_reason")
                ):
                    self._reroute_errors.append(
                        {
                            "simulation_step": record["simulation_step"],
                            "requested_destination": record[
                                "requested_destination"
                            ],
                            "receiving_destination": receiving_destination,
                        }
                    )

        visit_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in visit_records:
            self._visit_record_count += 1
            node_type = record["poi_type"]
            visit_by_type[node_type].append(record)
            row = dict(record)
            row.setdefault("cycle_step", record["simulation_step"] % self.cycle_length)
            row["cycle"] = record["simulation_step"] // self.cycle_length
            row["week"] = record["simulation_step"] // (7 * self.cycle_length)
            self._writers["visits"].writerow(
                {column: row.get(column, "") for column in self.VISIT_COLUMNS}
            )
            summary = self._summary[node_type]
            quantity = int(record["quantity"])
            if record["event"] == "start":
                summary["travelers_started"] += quantity
                summary["visit_starts"] += 1
                summary["travel_distance"] += quantity * float(record["distance"])
                self._visit_starts[record["visit_id"]] = {
                    "simulation_step": int(record["simulation_step"]),
                    "quantity": quantity,
                }
                od = self._od[(record["origin"], record["destination"], node_type)]
                od["trips"] += 1
                od["travelers"] += quantity
                od["traveler_distance"] += quantity * float(record["distance"])
            elif record["event"] == "release":
                summary["travelers_released"] += quantity
                summary["releases"] += 1
                if record["rerouted"]:
                    summary["release_reroutes"] += quantity
                start = self._visit_starts.get(record["visit_id"])
                if start is None or record["simulation_step"] - start["simulation_step"] != 1:
                    self._visit_duration_errors.append(
                        {
                            "visit_id": int(record["visit_id"]),
                            "start_step": -1 if start is None else start["simulation_step"],
                            "release_step": int(record["simulation_step"]),
                        }
                    )
                if start is not None:
                    start["quantity"] -= quantity
                    if start["quantity"] <= 0:
                        self._visit_starts.pop(record["visit_id"], None)
            elif record["event"] == "release_blocked":
                summary["release_blocked"] += quantity

        all_types = set(demand_by_type) | set(visit_by_type)
        for node_type in sorted(all_types):
            demands = demand_by_type[node_type]
            visits = visit_by_type[node_type]
            step = self.sim_step
            aggregate = {
                "simulation_step": step,
                "cycle_step": step % self.cycle_length,
                "cycle": step // self.cycle_length,
                "week": step // (7 * self.cycle_length),
                "weekday": (step // self.cycle_length) % 7,
                "node_type": node_type,
                "poi_count": len(demands),
                "closed_poi_count": sum(r["reason"] == "closed" for r in demands),
                "disabled_destination_count": sum(
                    r["reason"] == "disabled_destination" for r in demands
                ),
                "requested": sum(r["requested"] for r in demands),
                "fulfilled": sum(r["fulfilled"] for r in demands),
                "unmet": sum(r["unmet"] for r in demands),
                "visit_starts": sum(r["event"] == "start" for r in visits),
                "travelers_started": sum(
                    r["quantity"] for r in visits if r["event"] == "start"
                ),
                "releases": sum(r["event"] == "release" for r in visits),
                "travelers_released": sum(
                    r["quantity"] for r in visits if r["event"] == "release"
                ),
                "release_reroutes": sum(
                    r["quantity"]
                    for r in visits
                    if r["event"] == "release" and r["rerouted"]
                ),
                "release_blocked": sum(
                    r["quantity"]
                    for r in visits
                    if r["event"] == "release_blocked"
                ),
                "occupied_destinations": 0,
                "destination_occupancy": 0,
                "travel_distance": sum(
                    r["quantity"] * float(r["distance"])
                    for r in visits
                    if r["event"] == "start"
                ),
                "reroute_events": sum(
                    bool(r.get("destination_rerouted", False)) for r in demands
                ),
                "rerouted_requested": sum(
                    r["requested"]
                    for r in demands
                    if r.get("destination_rerouted", False)
                ),
                "rerouted_fulfilled": sum(
                    r["fulfilled"]
                    for r in demands
                    if r.get("destination_rerouted", False)
                ),
                "rerouted_unmet": sum(
                    r["unmet"]
                    for r in demands
                    if r.get("destination_rerouted", False)
                ),
                "reroute_traveler_distance": sum(
                    r["fulfilled"] * float(r.get("reroute_distance", 0.0))
                    for r in demands
                    if r.get("destination_rerouted", False)
                ),
            }
            self._step_rows.append(aggregate)

        active_template = PopulationTemplate(
            traceable_characteristics={self.plugin.ACTIVE: True}
        )
        occupancy_by_destination = {}
        for destination_name, node_type in destinations.items():
            destination = self.env_graph.get_node_by_complete_name(destination_name)
            occupancy = destination.get_population_size(active_template)
            occupancy_by_destination[destination_name] = occupancy
            if occupancy:
                row = next(
                    item
                    for item in reversed(self._step_rows)
                    if item["simulation_step"] == self.sim_step
                    and item["node_type"] == node_type
                )
                row["occupied_destinations"] += 1
                row["destination_occupancy"] += occupancy
        for record in demand_records:
            receiving_destination = record.get(
                "receiving_destination", record["destination"]
            )
            occupancy = occupancy_by_destination[receiving_destination]
            if record["requested"] > 0 or record["unmet"] > 0:
                raw = dict(record)
                raw["cycle"] = record["simulation_step"] // self.cycle_length
                raw["week"] = record["simulation_step"] // (7 * self.cycle_length)
                raw["destination_occupancy"] = occupancy
                self._writers["demand"].writerow(
                    {column: raw.get(column, "") for column in self.DEMAND_COLUMNS}
                )
                self._raw_demand_record_count += 1
                if record.get("destination_rerouted", False):
                    reroute = {
                        **raw,
                        "reroute_traveler_distance": (
                            record["fulfilled"]
                            * float(record["reroute_distance"])
                        ),
                    }
                    self._writers["rerouting"].writerow(
                        {
                            column: reroute.get(column, "")
                            for column in self.REROUTING_COLUMNS
                        }
                    )
                    key = (
                        record["requested_destination"],
                        record["receiving_destination"],
                        record["node_type"],
                    )
                    values = self._rerouting_summary[key]
                    values["reroute_events"] += 1
                    values["requested"] += record["requested"]
                    values["fulfilled"] += record["fulfilled"]
                    values["unmet"] += record["unmet"]
                    values["reroute_traveler_distance"] += reroute[
                        "reroute_traveler_distance"
                    ]
                    values["peak_receiving_load"] = max(
                        values["peak_receiving_load"],
                        float(record.get("receiving_load", occupancy)),
                    )

    def _audit_movement(self, origin, destination, blobs):
        if origin.is_enabled() and destination.is_enabled():
            return
        quantity = sum(blob.get_population_size() for blob in blobs)
        popular_visit = any(
            bool(blob.get_traceable_characteristic(self.plugin.ACTIVE))
            for blob in blobs
        )
        mandatory_release = (
            popular_visit and not origin.is_enabled() and destination.is_enabled()
        )
        self._writers.get("violations") and self._writers["violations"].writerow(
            {
                "simulation_step": self.sim_step,
                "origin": origin.get_complete_name(),
                "destination": destination.get_complete_name(),
                "origin_enabled": origin.is_enabled(),
                "destination_enabled": destination.is_enabled(),
                "quantity": quantity,
                "popular_times_visit": popular_visit,
                "mandatory_release_exception": mandatory_release,
            }
        )
        if mandatory_release:
            self._mandatory_release_exception_count += 1
        else:
            self._movement_violation_count += 1

    def stop_logger(self):
        self._drain_records()
        self._write_aggregates()
        for stream in self._files:
            stream.close()
        self.env_graph.movement_logger_dict.pop(
            "popular_times_v2_enabled_audit", None
        )

    def _write_aggregates(self):
        self._write_rows(
            "popular_times_step_type.csv", self.STEP_COLUMNS, self._step_rows
        )
        summary_columns = [
            "node_type",
            "requested",
            "fulfilled",
            "unmet",
            "fulfillment_rate",
            "poi_action_count",
            "closed_poi_count",
            "disabled_destination_count",
            "visit_starts",
            "travelers_started",
            "releases",
            "travelers_released",
            "release_reroutes",
            "release_blocked",
            "travel_distance",
            "mean_distance_per_traveler",
            "reroute_events",
            "rerouted_requested",
            "rerouted_fulfilled",
            "rerouted_unmet",
            "reroute_traveler_distance",
            "mean_reroute_distance_per_traveler",
        ]
        summary_rows = []
        for node_type, values in sorted(self._summary.items()):
            requested = values["requested"]
            travelers = values["travelers_started"]
            summary_rows.append(
                {
                    "node_type": node_type,
                    **{key: values[key] for key in summary_columns[1:] if key not in {"fulfillment_rate", "mean_distance_per_traveler", "mean_reroute_distance_per_traveler"}},
                    "fulfillment_rate": values["fulfilled"] / requested if requested else 1.0,
                    "mean_distance_per_traveler": values["travel_distance"] / travelers if travelers else 0.0,
                    "mean_reroute_distance_per_traveler": values["reroute_traveler_distance"] / values["rerouted_fulfilled"] if values["rerouted_fulfilled"] else 0.0,
                }
            )
        self._write_rows(
            "popular_times_summary.csv", summary_columns, summary_rows
        )

        od_columns = [
            "origin",
            "destination",
            "node_type",
            "trips",
            "travelers",
            "traveler_distance",
            "mean_distance_per_traveler",
        ]
        od_rows = []
        for (origin, destination, node_type), values in sorted(self._od.items()):
            od_rows.append(
                {
                    "origin": origin,
                    "destination": destination,
                    "node_type": node_type,
                    **values,
                    "mean_distance_per_traveler": values["traveler_distance"] / values["travelers"] if values["travelers"] else 0.0,
                }
            )
        self._write_rows("popular_times_od.csv", od_columns, od_rows)

        rerouting_columns = [
            "requested_destination",
            "receiving_destination",
            "node_type",
            "reroute_events",
            "requested",
            "fulfilled",
            "unmet",
            "reroute_traveler_distance",
            "mean_reroute_distance_per_traveler",
            "peak_receiving_load",
        ]
        rerouting_rows = []
        for (requested_destination, receiving_destination, node_type), values in sorted(
            self._rerouting_summary.items()
        ):
            rerouting_rows.append(
                {
                    "requested_destination": requested_destination,
                    "receiving_destination": receiving_destination,
                    "node_type": node_type,
                    **values,
                    "mean_reroute_distance_per_traveler": (
                        values["reroute_traveler_distance"] / values["fulfilled"]
                        if values["fulfilled"]
                        else 0.0
                    ),
                }
            )
        self._write_rows(
            "popular_times_rerouting_summary.csv",
            rerouting_columns,
            rerouting_rows,
        )

        validation = self._validation_results()
        (self.data_path / "popular_times_validation.json").write_text(
            json.dumps(validation, indent=2, ensure_ascii=False) + "\n",
            encoding="utf8",
        )

    def _validation_results(self) -> dict[str, Any]:
        final_population = self.env_graph.get_population_size()
        expected_weekly = self._expected_weekly_demand()
        weeks = self.simulation.time_status.total_cycles // 7
        weekly_checks = []
        for week in range(weeks):
            for node_type, expected in expected_weekly.items():
                actual = self._weekly_requested[(week, node_type)]
                weekly_checks.append(
                    {
                        "week": week,
                        "node_type": node_type,
                        "expected": expected,
                        "actual": actual,
                        "difference": actual - expected,
                        "passed": actual == expected,
                    }
                )

        release_quantity_errors = [
            {
                "visit_id": visit_id,
                "unreleased": start["quantity"],
                "start_step": start["simulation_step"],
            }
            for visit_id, start in self._visit_starts.items()
            if start["quantity"] != 0
        ]
        peak_checks = []
        covered_weekdays = set(
            range(min(7, self.simulation.time_status.total_cycles))
        )
        for node_type, profile in self.plugin.profiles.items():
            covered_profile = {
                key: value
                for key, value in profile.items()
                if key[0] in covered_weekdays
            }
            expected_weight = max(covered_profile.values())
            expected = sorted(
                key
                for key, value in covered_profile.items()
                if value == expected_weight
            )
            observed_values = {
                (weekday, hour): value
                for (kind, weekday, hour), value in self._hourly_requested.items()
                if kind == node_type
            }
            observed_max = max(observed_values.values(), default=0)
            observed = sorted(
                key for key, value in observed_values.items() if value == observed_max
            )
            peak_checks.append(
                {
                    "node_type": node_type,
                    "expected_peak_hours": expected,
                    "observed_peak_hours": observed,
                    "passed": bool(set(expected) & set(observed)),
                }
            )

        checks = {
            "population_conserved": final_population == self.initial_population,
            "population_constant_at_logged_steps": self.minimum_population == self.maximum_population == self.initial_population,
            "visits_last_exactly_one_hour": not self._visit_duration_errors,
            "visit_quantities_released": not release_quantity_errors,
            "closed_pois_request_zero": self._closed_request_errors == 0,
            "weekly_requested_totals_match": all(item["passed"] for item in weekly_checks),
            "hourly_peaks_match_profiles": all(item["passed"] for item in peak_checks),
            "disabled_nodes_do_not_move": self._movement_violation_count == 0,
            "all_unmet_requests_have_reason": self._unmet_reason_errors == 0,
            "rerouted_destinations_valid": not self._reroute_errors,
        }
        return {
            "passed": all(checks.values()),
            "checks": checks,
            "initial_population": self.initial_population,
            "final_population": final_population,
            "minimum_population": self.minimum_population,
            "maximum_population": self.maximum_population,
            "demand_record_count": self._demand_record_count,
            "raw_demand_record_count": self._raw_demand_record_count,
            "visit_record_count": self._visit_record_count,
            "movement_violation_count": self._movement_violation_count,
            "mandatory_release_exception_count": self._mandatory_release_exception_count,
            "visit_duration_errors": self._visit_duration_errors[:100],
            "release_quantity_errors": release_quantity_errors[:100],
            "weekly_demand": weekly_checks,
            "weekly_requested_totals_applicable": weeks > 0,
            "peak_checks": peak_checks,
            "reroute_errors": self._reroute_errors[:100],
        }

    def _expected_weekly_demand(self) -> dict[str, int]:
        template = PopulationTemplate()
        expected = defaultdict(int)
        template_key = str(template)
        for (_, node_type, cached_template), schedule in self.plugin._demand_cache.items():
            if cached_template == template_key:
                expected[node_type] += sum(schedule.values())
        return dict(expected)

    def _write_rows(self, filename: str, columns: list[str], rows):
        with (self.data_path / filename).open(
            "w", encoding="utf-8-sig", newline=""
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)

    def unload_plugin(self):
        if self.env_graph is not None:
            self.env_graph.movement_logger_dict.pop(
                "popular_times_v2_enabled_audit", None
            )
