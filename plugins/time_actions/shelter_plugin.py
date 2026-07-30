"""Flood exposure, evacuation, shelter admission, and wait-list reallocation."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import time
from typing import Any, Callable
import unicodedata

from core.environment import EnvNode, EnvironmentGraph
from core.plugin import ActionPlugin
from core.population import PopulationTemplate
from core.routine import Action
from core.simulator import LodusSimulation
from util.math import distribute_ints_from_weights, pyproj_distance_metre
from util.random_instance import FixedRandom


class ShelterPlugin(ActionPlugin):
    """Models static flood exposure and capacity-constrained sheltering.

    Region names are resolved by normalized exact matching and then by the
    versioned alias table below. Scientific runs never use fuzzy matching.
    """

    ACTION_MOVE = "move_to_shelters"
    ACTION_ADMIT = "shelter_population"
    ACTION_REALLOCATE = "reallocate_shelter_waitlist"
    NODE_TYPE = "shelter"

    STATUS = "flooding_status"
    SAFE = "safe"
    IN_DANGER = "in_danger"
    SHELTERED = "sheltered"

    ALIAS_VERSION = "porto-alegre-v1"
    REGION_ALIASES = {
        "cel aparicio borges": "Cel. Aparício Borges",
        "jardim dona leopoldina": "Jardim Leopoldina",
        "jardim ypu": "Jardim Itú",
        "passo da areia": "Passo D'Areia",
        "passo dareia": "Passo D'Areia",
        "passo d areia": "Passo D'Areia",
        "passo das pedras": "Passo das Pedras",
        "rio banco": "Rio Branco",
        "vila sao jose": "São José",
    }

    def __init__(self):
        super().__init__()
        self.simulation: LodusSimulation | None = None
        self.env_graph: EnvironmentGraph | None = None
        self.config: dict[str, Any] = {}
        self.shelters: list[EnvNode] = []
        self.shelter_data: list[dict[str, Any]] = []
        self.affected_regions = []
        self.exposure_by_region: dict[str, int] = {}
        self.requested_exposure_by_region: dict[str, int] = {}
        self.input_audit: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self._event_callbacks: dict[str, Callable[[dict], None]] = {}
        self._last_reallocation_step: int | None = None
        self.cycle_step = 0
        self.simulation_step = 0
        self.random = FixedRandom.instance
        self.data_path = Path(__file__).resolve().parents[2] / "data_input"
        self.safe_template = self._status_template(self.SAFE)
        self.in_danger_template = self._status_template(self.IN_DANGER)
        self.sheltered_template = self._status_template(self.SHELTERED)

    def add_event_listener(self, name: str, callback: Callable[[dict], None]):
        """Register a listener and replay retained initialization events."""
        self._event_callbacks[name] = callback
        for event in self.events:
            callback(event.copy())

    def remove_event_listener(self, name: str):
        self._event_callbacks.pop(name, None)

    def load_plugin(self, simulation: LodusSimulation):
        self.simulation = simulation
        self.env_graph = simulation.env_graph
        self.config = self._load_configuration(
            simulation.experiment_config.get("shelter_plugin", {})
        )
        outsiders = self._config_int("outsiders_initially_sheltered", 0)
        if outsiders:
            raise ValueError(
                "outsiders_initially_sheltered is unsupported until its "
                "population semantics are defined"
            )

        simulation.add_action_type_to_function(
            self.ACTION_MOVE, self.move_to_shelters, False
        )
        simulation.add_action_type_to_function(
            self.ACTION_ADMIT, self.shelter_population, True
        )
        simulation.add_action_type_to_function(
            self.ACTION_REALLOCATE, self.reallocate_shelter_waitlist, False
        )
        self.env_graph.add_blobs_traceable_property(self.STATUS, self.SAFE)
        self.env_graph.movement_logger_dict["shelter_plugin"] = (
            self._record_shelter_movement
        )

        self.selected_initially_affected_population()
        self.shelter_data = self.load_initial_shelter_data()
        self.create_initial_shelters()

    def update_time_step(self, cycle_step: int, simulation_step: int):
        self.cycle_step = cycle_step
        self.simulation_step = simulation_step
        if simulation_step == 0:
            self.request_initial_population_to_shelters()

    def unload_plugin(self):
        if self.env_graph is not None:
            self.env_graph.movement_logger_dict.pop("shelter_plugin", None)
        self._event_callbacks.clear()

    def move_to_shelters(
        self,
        pop_template: PopulationTemplate,
        values: dict,
        cycle_step: int,
        simulation_step: int,
    ) -> list[Action]:
        """Create Levy movement requests from an affected home."""
        started = time.perf_counter()
        node = self._action_node(values)
        if (
            node is None
            or not node.is_enabled()
            or node.node_type != "home"
            or node.containing_region_name not in self.exposure_by_region
        ):
            return []

        percentage = float(
            self.config.get(
                "daily_evacuation_rate",
                values.get("population_percentage_to_move", 0),
            )
        )
        if not 0 <= percentage <= 1:
            raise ValueError("population_percentage_to_move must be in [0, 1]")
        mode = int(self.config.get("evacuation_mode", values.get("mode", 0)))
        if mode == 0:
            requested = math.ceil(
                self.exposure_by_region[node.containing_region_name] * percentage
            )
        elif mode == 1:
            requested = math.ceil(
                node.get_population_size(self.in_danger_template) * percentage
            )
        else:
            raise ValueError("shelter evacuation mode must be 0 or 1")

        available = node.get_population_size(self.in_danger_template)
        quantity = min(requested, available)
        if quantity:
            self._emit(
                "evacuation_requested",
                quantity,
                origin=node,
                details={"requested_population": requested, "mode": mode},
                cycle_step=cycle_step,
                simulation_step=simulation_step,
            )
        self.add_execution_time(self.ACTION_MOVE, time.perf_counter() - started)
        if quantity == 0:
            return []
        if not any(node.is_enabled() for node in self.shelters):
            self._emit(
                "admission_denied",
                quantity,
                origin=node,
                reason="no_enabled_shelters",
                cycle_step=cycle_step,
                simulation_step=simulation_step,
            )
            return []
        return [
            Action(
                "levy_walk_direct",
                self.in_danger_template.copy(),
                {
                    "region": node.containing_region_name,
                    "node": node.unique_name,
                    "quantity": quantity,
                    "target_node_type": [self.NODE_TYPE],
                    "target_enabled_only": True,
                    "population_group_size": int(
                        values.get(
                            "population_group_size",
                            self.config.get("population_group_size", 1),
                        )
                    ),
                    "movement_probability": float(
                        values.get("movement_probability", 1.0)
                    ),
                    "use_original_population": False,
                    "target_node_type_contains": False,
                },
            )
        ]

    def shelter_population(
        self,
        pop_template: PopulationTemplate,
        values: dict,
        cycle_step: int,
        simulation_step: int,
    ):
        """Admit waiting people without exceeding an enabled shelter's capacity."""
        started = time.perf_counter()
        node = self._action_node(values)
        if node is None or node.node_type != self.NODE_TYPE:
            return
        waiting = node.get_population_size(self.in_danger_template)
        if waiting == 0:
            return
        if not node.is_enabled():
            self._emit(
                "admission_denied",
                waiting,
                shelter=node,
                reason="disabled",
                cycle_step=cycle_step,
                simulation_step=simulation_step,
            )
            return

        capacity = int(node.get_attribute("capacity"))
        sheltered = node.get_population_size(self.sheltered_template)
        free_beds = max(0, capacity - sheltered)
        admitted = min(waiting, free_beds)
        admitted_actual = self._change_status(
            node, self.IN_DANGER, self.SHELTERED, admitted
        )
        if admitted_actual:
            self._emit(
                "admitted",
                admitted_actual,
                shelter=node,
                cycle_step=cycle_step,
                simulation_step=simulation_step,
            )
        denied = waiting - admitted_actual
        if denied:
            self._emit(
                "admission_denied",
                denied,
                shelter=node,
                reason="capacity",
                cycle_step=cycle_step,
                simulation_step=simulation_step,
            )
        if node.get_population_size(self.sheltered_template) > capacity:
            raise RuntimeError(f"shelter capacity exceeded at {node.get_complete_name()}")
        self.add_execution_time(self.ACTION_ADMIT, time.perf_counter() - started)

    def reallocate_shelter_waitlist(
        self,
        pop_template: PopulationTemplate,
        values: dict,
        cycle_step: int,
        simulation_step: int,
    ) -> list[Action]:
        """Move at most ``min(waitlist, free beds)`` between shelters once a step."""
        started = time.perf_counter()
        if self._last_reallocation_step == simulation_step:
            return []
        self._last_reallocation_step = simulation_step

        origins = [
            node
            for node in self.shelters
            if node.is_enabled()
            and node.get_population_size(self.in_danger_template) > 0
        ]
        targets = [
            node
            for node in self.shelters
            if node.is_enabled() and self._free_beds(node) > 0
        ]
        self.random.shuffle(origins)
        self.random.shuffle(targets)

        actions: list[Action] = []
        target_free = {
            target: self._free_beds(target) for target in targets
        }
        for origin in origins:
            waiting = origin.get_population_size(self.in_danger_template)
            for target in targets:
                if waiting == 0:
                    break
                if target is origin:
                    continue
                quantity = min(waiting, target_free[target])
                if quantity:
                    actions.append(
                        Action(
                            "move_population",
                            self.in_danger_template.copy(),
                            {
                                "origin_region": origin.containing_region_name,
                                "origin_node": origin.unique_name,
                                "destination_region": target.containing_region_name,
                                "destination_node": target.unique_name,
                                "quantity": quantity,
                            },
                        )
                    )
                    self._emit(
                        "reallocation_requested",
                        quantity,
                        origin=origin,
                        shelter=target,
                        cycle_step=cycle_step,
                        simulation_step=simulation_step,
                    )
                    waiting -= quantity
                    target_free[target] -= quantity
        self.add_execution_time(
            self.ACTION_REALLOCATE, time.perf_counter() - started
        )
        return actions

    def request_initial_population_to_shelters(self):
        """Move the configured observed occupancy and mark actual arrivals sheltered."""
        if self.simulation is None:
            return
        for row in self.shelter_data:
            requested = int(row["shelteredPeople"])
            node = row["node"]
            if requested <= 0 or not node.is_enabled():
                continue
            sources = sorted(
                (
                    source
                    for source in self.env_graph.node_list
                    if source.node_type != self.NODE_TYPE
                    and source.get_population_size(self.in_danger_template) > 0
                ),
                key=lambda source: pyproj_distance_metre(
                    source.long_lat, node.long_lat
                ),
            )
            remaining = requested
            for source in sources:
                quantity = min(
                    remaining,
                    source.get_population_size(self.in_danger_template),
                )
                if quantity:
                    self.simulation.direct_action_invoke(
                        Action(
                            "move_population",
                            self.in_danger_template.copy(),
                            {
                                "origin_region": source.containing_region_name,
                                "origin_node": source.unique_name,
                                "destination_region": node.containing_region_name,
                                "destination_node": node.unique_name,
                                "quantity": quantity,
                            },
                        ),
                        self.cycle_step,
                        self.simulation_step,
                    )
                    remaining -= quantity
                if remaining == 0:
                    break
            arrived = requested - remaining
            admitted = min(arrived, self._free_beds(node))
            actual = self._change_status(
                node, self.IN_DANGER, self.SHELTERED, admitted
            )
            if actual:
                self._emit("admitted", actual, shelter=node, reason="initial")
            if actual < requested:
                self._audit(
                    "initial_occupancy_shortfall",
                    input_name=node.unique_name,
                    requested=requested,
                    applied=actual,
                    shortfall=requested - actual,
                )

    def selected_initially_affected_population(self):
        """Select exposed home population with per-region caps and an audit trail."""
        if self.env_graph is None:
            return
        affected = self.config.get("affected_areas")
        if not isinstance(affected, dict):
            raise ValueError("shelter_plugin.affected_areas is required")
        mode = int(affected.get("mode", 0))
        raw_by_region: dict[str, int] = {}

        if mode == 0:
            path = self._data_file(affected.get("affected_regions_file"))
            with path.open(encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream):
                    if self._as_bool(row.get("Affected")):
                        region = self._resolve_region(row.get("RegionName", ""), path)
                        homes = region.get_nodes_by_type("home")
                        raw_by_region[region.name] = sum(
                            node.get_population_size(self.safe_template)
                            for node in homes
                        )
        elif mode == 1:
            path = self._data_file(
                affected.get("affected_census_sectors_file")
            )
            with path.open(encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream):
                    if not self._as_bool(row.get("Inundação")):
                        continue
                    region = self._resolve_region(row.get("Bairro", ""), path)
                    raw_by_region[region.name] = raw_by_region.get(
                        region.name, 0
                    ) + self._parse_int(row.get("Total de pessoas"))
        else:
            raise ValueError("affected_areas.mode must be 0 or 1")

        if not raw_by_region:
            raise ValueError("affected-area input selected no regions")
        requested_total = self._config_int("initially_affected_people", 0)
        if requested_total == 0:
            requested_total = sum(raw_by_region.values())
        exposure_multiplier = float(self.config.get("exposure_multiplier", 1))
        if exposure_multiplier < 0:
            raise ValueError("exposure_multiplier must be nonnegative")
        requested_total = round(requested_total * exposure_multiplier)
        requested = list(
            distribute_ints_from_weights(
                requested_total, list(raw_by_region.values())
            )
        )

        self.affected_regions = [
            self.env_graph.region_dict[name] for name in raw_by_region
        ]
        for index, region in enumerate(self.affected_regions):
            region_requested = int(requested[index])
            self.requested_exposure_by_region[region.name] = region_requested
            homes = region.get_nodes_by_type("home")
            available = sum(
                node.get_population_size(self.safe_template) for node in homes
            )
            selected = min(region_requested, available)
            remaining = selected
            for home in homes:
                quantity = min(
                    remaining, home.get_population_size(self.safe_template)
                )
                actual = self._change_status(
                    home, self.SAFE, self.IN_DANGER, quantity
                )
                remaining -= actual
                if remaining == 0:
                    break
            applied = selected - remaining
            self.exposure_by_region[region.name] = applied
            self._emit(
                "affected_selected",
                applied,
                origin=homes[0] if homes else None,
                details={
                    "origin_region": region.name,
                    "requested_population": region_requested,
                },
                simulation_step=-1,
                cycle_step=-1,
            )
            shortfall = region_requested - applied
            if shortfall:
                self._audit(
                    "population_shortfall",
                    input_name=region.name,
                    requested=region_requested,
                    available=available,
                    applied=applied,
                    shortfall=shortfall,
                )

    def load_initial_shelter_data(self) -> list[dict[str, Any]]:
        filename = self.config.get("shelter_data")
        if not filename:
            return []
        path = self._data_file(filename)
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = [
                dict(row)
                for row in csv.DictReader(stream)
                if str(row.get("abrigo", "")).strip().casefold() == "sim"
                and "evacuado" not in str(row.get("name", "")).casefold()
            ]

        for row in rows:
            row["capacity"] = max(
                self._parse_int(row.get("capacity")),
                self._parse_int(row.get("shelteredPeople")),
            )
            row["shelteredPeople"] = self._parse_int(
                row.get("shelteredPeople")
            )
            row["region"] = self._resolve_region_name(
                row.get("region", ""), path
            )

        configured_capacity = self._config_int("initial_shelter_capacity", 0)
        known_capacity = sum(int(row["capacity"]) for row in rows)
        undefined = [row for row in rows if int(row["capacity"]) == 0]
        missing_capacity = configured_capacity - known_capacity
        if missing_capacity > 0:
            if not undefined:
                raise ValueError(
                    "configured initial_shelter_capacity exceeds known capacity "
                    "but no zero-capacity shelters are available for imputation"
                )
            allocations = distribute_ints_from_weights(
                missing_capacity, [1] * len(undefined)
            )
            for row, allocation in zip(undefined, allocations):
                row["capacity"] = int(allocation)
                self._audit(
                    "capacity_imputation",
                    input_name=row.get("name", row.get("id", "")),
                    applied=int(allocation),
                )
        else:
            retained = []
            for row in rows:
                if int(row["capacity"]) <= 0:
                    self._audit(
                        "dropped_shelter",
                        input_name=row.get("name", row.get("id", "")),
                        reason="zero_capacity",
                    )
                else:
                    retained.append(row)
            rows = retained

        configured_occupancy = self._config_int(
            "initially_sheltered_people", 0
        )
        known_occupancy = sum(int(row["shelteredPeople"]) for row in rows)
        if configured_occupancy > known_occupancy:
            self._allocate_occupancy(
                rows, configured_occupancy - known_occupancy
            )
        capacity_multiplier = float(
            self.config.get("capacity_multiplier", 1)
        )
        if capacity_multiplier < 0:
            raise ValueError("capacity_multiplier must be nonnegative")
        if capacity_multiplier != 1:
            for row in rows:
                original = int(row["capacity"])
                row["capacity"] = max(0, round(original * capacity_multiplier))
                self._audit(
                    "capacity_multiplier",
                    input_name=row.get("name", row.get("id", "")),
                    requested=original,
                    applied=row["capacity"],
                    details=capacity_multiplier,
                )
        occupancy_mode = self.config.get("initial_occupancy_mode", "observed")
        if occupancy_mode == "empty":
            for row in rows:
                row["shelteredPeople"] = 0
        elif occupancy_mode in {"half", "half_capacity"}:
            for row in rows:
                row["shelteredPeople"] = round(int(row["capacity"]) * 0.5)
        elif occupancy_mode != "observed":
            raise ValueError(
                "initial_occupancy_mode must be observed, empty, or half_capacity"
            )
        for row in rows:
            if int(row["shelteredPeople"]) > int(row["capacity"]):
                original = int(row["shelteredPeople"])
                row["shelteredPeople"] = int(row["capacity"])
                self._audit(
                    "occupancy_capacity_cap",
                    input_name=row.get("name", row.get("id", "")),
                    requested=original,
                    applied=row["shelteredPeople"],
                    shortfall=original - row["shelteredPeople"],
                )
        return rows

    def create_initial_shelters(self):
        if self.env_graph is None:
            return
        for index, row in enumerate(self.shelter_data):
            shelter_id = str(row.get("id") or index + 1).strip()
            unique_name = f"shelter_{shelter_id}"
            node = EnvNode(self.NODE_TYPE, unique_name)
            node.set_long_lat_position(
                float(row["Longitude"]), float(row["Latitude"])
            )
            node.add_attribute("shelter", True)
            node.add_attribute("capacity", int(row["capacity"]))
            node.add_attribute("shelter_id", shelter_id)
            node.add_attribute("shelter_name", row.get("name", unique_name))
            node.add_attribute("address", row.get("address", ""))
            node.add_attribute(
                "initial_sheltered", int(row["shelteredPeople"])
            )
            self.env_graph.add_envnode(row["region"], node)
            row["node"] = node
            self.shelters.append(node)
            self._audit(
                "shelter_loaded",
                input_name=row.get("name", unique_name),
                resolved_name=node.get_complete_name(),
                capacity=int(row["capacity"]),
                occupancy=int(row["shelteredPeople"]),
            )
        self._apply_failure_scenario()

    def _apply_failure_scenario(self):
        scenario = str(self.config.get("failure_scenario", "none"))
        if scenario == "none" or not self.shelters:
            return
        if scenario == "largest":
            disabled = [
                max(
                    self.shelters,
                    key=lambda node: int(node.get_attribute("capacity")),
                )
            ]
        elif scenario == "top_10_percent_capacity":
            count = max(1, math.ceil(len(self.shelters) * 0.1))
            disabled = sorted(
                self.shelters,
                key=lambda node: int(node.get_attribute("capacity")),
                reverse=True,
            )[:count]
        elif scenario.startswith("region:"):
            region_name = self._resolve_region_name(
                scenario.split(":", 1)[1], Path("<failure_scenario>")
            )
            disabled = [
                node for node in self.shelters
                if node.containing_region_name == region_name
            ]
        else:
            raise ValueError(f"unknown shelter failure_scenario {scenario!r}")
        for node in disabled:
            node.disable("shelter_failure")
            self._audit(
                "disabled_shelter",
                input_name=node.get_complete_name(),
                reason=scenario,
                capacity=node.get_attribute("capacity"),
            )

    def _allocate_occupancy(
        self, rows: list[dict[str, Any]], quantity: int
    ):
        free = [
            int(row["capacity"]) - int(row["shelteredPeople"]) for row in rows
        ]
        if quantity > sum(free):
            raise ValueError(
                "configured initially_sheltered_people exceeds total capacity"
            )
        remaining = quantity
        while remaining:
            allocations = list(
                distribute_ints_from_weights(remaining, free)
            )
            progress = 0
            for index, allocation in enumerate(allocations):
                applied = min(int(allocation), free[index])
                rows[index]["shelteredPeople"] += applied
                free[index] -= applied
                remaining -= applied
                progress += applied
            if not progress:
                index = next(i for i, slots in enumerate(free) if slots)
                rows[index]["shelteredPeople"] += 1
                free[index] -= 1
                remaining -= 1

    def _record_shelter_movement(
        self, origin: EnvNode, destination: EnvNode, blobs
    ):
        groups: dict[int, int] = {}
        for blob in blobs:
            groups[blob.mother_blob_id] = groups.get(
                blob.mother_blob_id, 0
            ) + blob.get_population_size()
        for mother_id, population in groups.items():
            if population == 0:
                continue
            population_origin = (
                self.env_graph.region_id_dict.get(mother_id)
                if self.env_graph is not None
                else None
            )
            details = {
                "population_origin_region": (
                    population_origin.name if population_origin else ""
                )
            }
            if destination.node_type == self.NODE_TYPE:
                details["distance_km"] = (
                    pyproj_distance_metre(origin.long_lat, destination.long_lat)
                    / 1000
                )
                event_type = (
                    "reallocated"
                    if origin.node_type == self.NODE_TYPE
                    else "arrived"
                )
                self._emit(
                    event_type,
                    population,
                    origin=origin,
                    shelter=destination,
                    details=details,
                )
            elif origin.node_type == self.NODE_TYPE:
                self._emit(
                    "departed",
                    population,
                    origin=origin,
                    shelter=origin,
                    details=details,
                )

    def _action_node(self, values: dict) -> EnvNode | None:
        if self.env_graph is None:
            return None
        if "node_id" in values:
            return self.env_graph.get_node_by_id(values["node_id"])
        if "region" in values and (
            "node_unique_name" in values or "node" in values
        ):
            return self.env_graph.get_node_by_unique_name(
                values["region"],
                values.get("node_unique_name", values.get("node")),
            )
        return None

    def _free_beds(self, node: EnvNode) -> int:
        if not node.is_enabled():
            return 0
        return max(
            0,
            int(node.get_attribute("capacity"))
            - node.get_population_size(self.sheltered_template),
        )

    def _change_status(
        self, node: EnvNode, old_status: str, new_status: str, quantity: int
    ) -> int:
        """Apply a status transition exactly despite integer blob splitting."""
        template = self._status_template(old_status)
        remaining = quantity
        changed_total = 0
        while remaining > 0:
            before = node.get_population_size(template)
            if before == 0:
                break
            changed = node.change_multiple_blobs_traceable_property(
                self.STATUS, new_status, remaining, template
            )
            changed_now = sum(blob.get_population_size() for blob in changed)
            if changed_now <= 0:
                break
            changed_total += changed_now
            remaining -= changed_now
        return changed_total

    def _load_configuration(self, direct: dict[str, Any]) -> dict[str, Any]:
        direct = dict(direct)
        filename = direct.get("configuration_file")
        if not filename:
            return direct
        with self._data_file(filename).open(encoding="utf-8") as stream:
            loaded = json.load(stream)
        if not isinstance(loaded, dict):
            raise ValueError("shelter configuration_file must contain an object")
        return {**loaded, **direct}

    def _resolve_region(self, name: str, source: Path):
        if self.env_graph is None:
            raise RuntimeError("plugin is not loaded")
        return self.env_graph.region_dict[
            self._resolve_region_name(name, source)
        ]

    def _resolve_region_name(self, name: str, source: Path) -> str:
        if self.env_graph is None:
            raise RuntimeError("plugin is not loaded")
        value = str(name).strip()
        normalized = self._normalize(value)
        canonical = {
            self._normalize(region_name): region_name
            for region_name in self.env_graph.region_dict
        }
        if normalized in canonical:
            resolved = canonical[normalized]
            if value != resolved:
                self._audit(
                    "normalized_region_match",
                    source=str(source),
                    input_name=value,
                    resolved_name=resolved,
                )
            return resolved
        alias = self.REGION_ALIASES.get(normalized)
        if alias and alias in self.env_graph.region_dict:
            self._audit(
                "region_alias",
                source=str(source),
                input_name=value,
                resolved_name=alias,
                alias_version=self.ALIAS_VERSION,
            )
            return alias
        self._audit(
            "unresolved_region",
            source=str(source),
            input_name=value,
            alias_version=self.ALIAS_VERSION,
        )
        raise ValueError(
            f"unresolved shelter region {value!r} in {source}; "
            f"alias table {self.ALIAS_VERSION}"
        )

    @staticmethod
    def _normalize(value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", str(value))
        ascii_value = "".join(
            char for char in decomposed if not unicodedata.combining(char)
        )
        return " ".join(
            "".join(
                char if char.isalnum() else " " for char in ascii_value.casefold()
            ).split()
        )

    def _data_file(self, filename: Any) -> Path:
        if not filename:
            raise ValueError("required shelter input file is not configured")
        path = Path(str(filename))
        if not path.is_absolute():
            path = self.data_path / path
        if not path.is_file():
            raise FileNotFoundError(path)
        return path

    def _config_int(self, key: str, default: int) -> int:
        value = self.config.get(key, self.config.get(f"_{key}", default))
        parsed = self._parse_int(value)
        if parsed < 0:
            raise ValueError(f"{key} must be nonnegative")
        return parsed

    @staticmethod
    def _parse_int(value: Any) -> int:
        if value is None or str(value).strip() == "":
            return 0
        return int(float(str(value).replace(",", ".")))

    @staticmethod
    def _as_bool(value: Any) -> bool:
        return str(value).strip().casefold() in {"true", "1", "yes", "sim"}

    @classmethod
    def _status_template(cls, status: str) -> PopulationTemplate:
        return PopulationTemplate(
            traceable_characteristics={cls.STATUS: status}
        )

    def _audit(self, audit_type: str, **details):
        self.input_audit.append({"audit_type": audit_type, **details})

    def _emit(
        self,
        event_type: str,
        population: int,
        origin: EnvNode | None = None,
        shelter: EnvNode | None = None,
        reason: str = "",
        details: dict[str, Any] | None = None,
        cycle_step: int | None = None,
        simulation_step: int | None = None,
    ):
        step = self.simulation_step if simulation_step is None else simulation_step
        frame = self.cycle_step if cycle_step is None else cycle_step
        cycle_length = (
            self.simulation.time_status.cycle_length
            if self.simulation is not None
            else 24
        )
        event = {
            "simulation_step": step,
            "cycle_step": frame,
            "cycle": step // cycle_length if step >= 0 else -1,
            "event_type": event_type,
            "population": int(population),
            "origin_id": origin.id if origin else "",
            "origin": origin.get_complete_name() if origin else "",
            "origin_region": (
                origin.containing_region_name if origin else ""
            ),
            "shelter_id": shelter.id if shelter else "",
            "shelter": shelter.get_complete_name() if shelter else "",
            "shelter_region": (
                shelter.containing_region_name if shelter else ""
            ),
            "reason": reason,
        }
        if details:
            event.update(details)
        self.events.append(event)
        for callback in tuple(self._event_callbacks.values()):
            callback(event.copy())
