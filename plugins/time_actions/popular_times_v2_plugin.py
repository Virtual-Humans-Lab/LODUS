from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np
from pyproj import Geod

from core.environment import EnvNode
from core.plugin import ActionPlugin
from core.population import PopulationTemplate
from core.simulator import LodusSimulation
from util.math import (
    DistanceType,
    distance2D,
    geopy_distance_metre,
)


class PopularTimesV2Plugin(ActionPlugin):
    """Weekly, flood-aware POI visits with an explicit one-hour lifecycle."""

    ACTION_TYPE = "popular_times_v2"
    CONFIG_KEY = "popular_times_v2_plugin"

    ACTIVE = "popular_times_v2_active"
    VISIT_ID = "popular_times_v2_visit_id"
    RETURN_NODE = "popular_times_v2_return_node"
    PAIRED_HOME = "popular_times_v2_paired_home"
    EXPIRY_STEP = "popular_times_v2_expiry_step"
    POI_TYPE = "popular_times_v2_poi_type"

    DEFAULT_PROFILE_FILES = {
        "marketplace": "marketplace.csv",
        "restaurant": "restaurant.csv",
        "pharmacy": "pharmacy.csv",
    }
    DEFAULT_WEEKLY_RATES = {
        "marketplace": 1.0,
        "restaurant": 1.0,
        "pharmacy": 0.25,
    }
    TRACEABLE_DEFAULTS = {
        ACTIVE: False,
        VISIT_ID: -1,
        RETURN_NODE: -1,
        PAIRED_HOME: -1,
        EXPIRY_STEP: -1,
        POI_TYPE: "",
    }

    def __init__(self):
        super().__init__()
        self.simulation: LodusSimulation | None = None
        self.env_graph = None
        self.config: dict[str, Any] = {}
        self.data_path = Path(__file__).parents[2] / "data_input" / "popular_times"
        self.profiles: dict[str, dict[tuple[int, int], float]] = {}
        self.weekly_rates = dict(self.DEFAULT_WEEKLY_RATES)
        self.multiplier_overrides: dict[str, float] = {}
        self._demand_cache: dict[tuple[str, str, str], dict[tuple[int, int], int]] = {}
        self._visit_sequence = 0
        self.demand_records: list[dict[str, Any]] = []
        self.visit_records: list[dict[str, Any]] = []
        self._home_nodes: list[EnvNode] = []
        self._source_candidate_cache: dict[
            tuple[int, str], list[tuple[EnvNode, float]]
        ] = {}
        self._geod = Geod(ellps="WGS84")

    def load_plugin(self, simulation: LodusSimulation):
        self.simulation = simulation
        self.env_graph = simulation.env_graph
        self.config = dict(simulation.experiment_config.get(self.CONFIG_KEY, {}))
        self.data_path = self._resolve_data_path(
            self.config.get("data_path", self.data_path)
        )
        self.weekly_rates.update(self.config.get("weekly_visit_rates", {}))
        self._validate_configuration()
        self._load_profiles()
        if self.config.get("demand_basis", "initial_population") == "multiplier_csv":
            self._load_multiplier_overrides()

        for key, value in self.TRACEABLE_DEFAULTS.items():
            self.env_graph.add_blobs_traceable_property(key, value)
        self._home_nodes = [
            node for node in self.env_graph.node_list if node.node_type == "home"
        ]

        simulation.add_action_type_to_function(
            self.ACTION_TYPE, self.popular_times_v2_action, True
        )

    def _resolve_data_path(self, value: str | Path) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        project_relative = Path(__file__).parents[2] / path
        return project_relative if project_relative.exists() else path

    def _validate_configuration(self) -> None:
        basis = self.config.get("demand_basis", "initial_population")
        if basis not in {"initial_population", "multiplier_csv"}:
            raise ValueError(
                "popular_times_v2_plugin.demand_basis must be "
                "'initial_population' or 'multiplier_csv'"
            )
        return_mode = self.config.get("return_mode", "prior_node")
        if return_mode not in {"prior_node", "paired_home"}:
            raise ValueError(
                "popular_times_v2_plugin.return_mode must be "
                "'prior_node' or 'paired_home'"
            )
        for node_type, rate in self.weekly_rates.items():
            if not isinstance(rate, (int, float)) or rate < 0:
                raise ValueError(f"Weekly visit rate for {node_type} must be non-negative")

    def _load_profiles(self) -> None:
        configured = self.config.get("profile_files", {})
        profile_files = {**self.DEFAULT_PROFILE_FILES, **configured}
        for node_type in self.weekly_rates:
            if node_type not in profile_files:
                raise ValueError(f"No weekly profile configured for {node_type}")
            profile_path = Path(profile_files[node_type])
            if not profile_path.is_absolute():
                profile_path = self.data_path / profile_path
            self.profiles[node_type] = self.load_weekly_profile(profile_path)

    @staticmethod
    def load_weekly_profile(profile_path: str | Path) -> dict[tuple[int, int], float]:
        path = Path(profile_path)
        if not path.is_file():
            raise FileNotFoundError(f"Popular Times V2 profile not found: {path}")

        raw_weights: dict[tuple[int, int], float] = {}
        with path.open("r", encoding="utf8", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            required = {"ciclo", "hora", "quantidade"}
            if reader.fieldnames is None or not required.issubset(reader.fieldnames):
                raise ValueError(
                    f"Profile {path} must contain ciclo, hora, quantidade columns"
                )
            for row in reader:
                day = int(row["ciclo"])
                hour = int(row["hora"])
                weight = float(row["quantidade"])
                if not 0 <= day <= 6 or not 0 <= hour <= 23:
                    raise ValueError(f"Invalid weekly profile coordinate: {(day, hour)}")
                if weight < 0:
                    raise ValueError("Weekly profile weights cannot be negative")
                if (day, hour) in raw_weights:
                    raise ValueError(f"Duplicate weekly profile coordinate: {(day, hour)}")
                if weight > 0:
                    raw_weights[(day, hour)] = weight

        total_weight = sum(raw_weights.values())
        if total_weight <= 0:
            raise ValueError(f"Profile {path} has no positive demand weights")
        return {key: value / total_weight for key, value in raw_weights.items()}

    def _load_multiplier_overrides(self) -> None:
        filename = self.config.get(
            "multiplier_file", "Setores-13Bairros-Dia.csv"
        )
        path = Path(filename)
        if not path.is_absolute():
            path = self.data_path / path
        if not path.is_file():
            raise FileNotFoundError(f"Popular Times V2 multiplier file not found: {path}")

        with path.open("r", encoding="utf8", newline="") as csvfile:
            for row in csv.reader(csvfile):
                if len(row) < 2:
                    continue
                try:
                    self.multiplier_overrides[row[0].strip().lower()] = float(row[1])
                except ValueError:
                    continue

    @staticmethod
    def paired_home_name(region: str, poi_unique_name: str) -> str:
        parts = poi_unique_name.rsplit("_", 1)
        if len(parts) != 2 or not parts[1]:
            raise ValueError(
                f"POI {region}//{poi_unique_name} does not have a pairable suffix"
            )
        return f"{region}//home_{parts[1]}"

    def _effective_population(
        self, paired_home: EnvNode, pop_template: PopulationTemplate
    ) -> float:
        basis = self.config.get("demand_basis", "initial_population")
        if basis == "multiplier_csv":
            key = paired_home.get_complete_name().lower()
            if key not in self.multiplier_overrides:
                raise ValueError(f"No multiplier configured for {key}")
            scale = float(self.config.get("multiplier_population_scale", 700))
            if scale <= 0:
                raise ValueError("multiplier_population_scale must be positive")
            return self.multiplier_overrides[key] * scale

        original = paired_home.original_node_population
        if original is not None:
            return float(original.get_population_size(pop_template))
        return float(paired_home.get_population_size(pop_template))

    def _weekly_schedule(
        self,
        paired_home: EnvNode,
        node_type: str,
        pop_template: PopulationTemplate,
    ) -> dict[tuple[int, int], int]:
        cache_key = (paired_home.get_complete_name(), node_type, str(pop_template))
        if cache_key in self._demand_cache:
            return self._demand_cache[cache_key]

        if node_type not in self.profiles:
            raise ValueError(f"Unsupported Popular Times V2 node type: {node_type}")
        weekly_total = int(
            round(
                self._effective_population(paired_home, pop_template)
                * float(self.weekly_rates[node_type])
            )
        )
        profile = self.profiles[node_type]
        coordinates = sorted(profile)
        quantities = self._largest_remainder_distribution(
            weekly_total, [profile[key] for key in coordinates]
        )
        schedule = dict(zip(coordinates, quantities))
        self._demand_cache[cache_key] = schedule
        return schedule

    @staticmethod
    def _largest_remainder_distribution(total: int, weights: list[float]) -> list[int]:
        if total <= 0:
            return [0] * len(weights)
        raw = [total * weight for weight in weights]
        result = [int(value) for value in raw]
        remainder = total - sum(result)
        order = sorted(
            range(len(raw)), key=lambda index: raw[index] - result[index], reverse=True
        )
        for index in order[:remainder]:
            result[index] += 1
        return result

    def get_hourly_demand(
        self,
        destination: EnvNode,
        pop_template: PopulationTemplate,
        cycle_step: int,
        simulation_step: int,
    ) -> int:
        if self.simulation is None or self.env_graph is None:
            raise RuntimeError("PopularTimesV2Plugin has not been loaded")
        cycle_length = self.simulation.time_status.cycle_length
        weekday = (simulation_step // cycle_length) % 7
        home_name = self.paired_home_name(
            destination.containing_region_name, destination.unique_name
        )
        paired_home = self.env_graph.get_node_by_complete_name(home_name)
        schedule = self._weekly_schedule(
            paired_home, destination.node_type, pop_template
        )
        return schedule.get((weekday, cycle_step), 0)

    def _source_allocations(
        self,
        destination: EnvNode,
        quantity: int,
        pop_template: PopulationTemplate,
    ) -> list[tuple[EnvNode, int]]:
        if quantity <= 0:
            return []

        # Rank a bounded candidate set after considering every home.  Runtime
        # allocations are then a deterministic weighted greedy selection.  This
        # preserves inverse-distance x availability weighting without splitting
        # small hourly requests into one-person blobs across hundreds of homes.
        candidates = self._source_candidates(destination, pop_template)
        allocations = self._weighted_greedy_allocations(
            candidates, quantity, pop_template
        )
        fulfilled = sum(amount for _, amount in allocations)
        if fulfilled >= quantity:
            return allocations

        selected_ids = {node.id for node, _ in allocations}
        fallback = [
            (node, self._distance_between(destination, node))
            for node in self._home_nodes
            if node.id not in selected_ids
        ]
        allocations.extend(
            self._weighted_greedy_allocations(
                fallback, quantity - fulfilled, pop_template
            )
        )
        return allocations

    def _source_candidates(
        self, destination: EnvNode, pop_template: PopulationTemplate
    ) -> list[tuple[EnvNode, float]]:
        key = (destination.id, str(pop_template))
        if key in self._source_candidate_cache:
            return self._source_candidate_cache[key]

        distances = self._home_distances(destination)
        distance_type = DistanceType(
            self.config.get("distance_type", DistanceType.METRES_PYPROJ.value)
        )
        distance_floor = 0.000001 if distance_type == DistanceType.LONG_LAT else 1.0
        upper_availability = np.fromiter(
            (
                node.original_node_population.get_population_size(pop_template)
                if node.original_node_population is not None
                else node.get_population_size(pop_template)
                for node in self._home_nodes
            ),
            dtype=float,
            count=len(self._home_nodes),
        )
        weights = upper_availability / np.maximum(distances, distance_floor)
        limit = min(
            max(1, int(self.config.get("source_candidate_limit", 64))),
            len(self._home_nodes),
        )
        if limit == len(self._home_nodes):
            indices = np.argsort(weights)[::-1]
        else:
            unordered = np.argpartition(weights, -limit)[-limit:]
            indices = unordered[np.argsort(weights[unordered])[::-1]]
        candidates = [
            (self._home_nodes[int(index)], float(distances[int(index)]))
            for index in indices
            if weights[int(index)] > 0
        ]
        self._source_candidate_cache[key] = candidates
        return candidates

    def _home_distances(self, destination: EnvNode) -> np.ndarray:
        if not self._home_nodes:
            return np.array([], dtype=float)
        destination_position = destination.long_lat
        home_positions = np.asarray(
            [node.long_lat for node in self._home_nodes], dtype=float
        )
        distance_type = DistanceType(
            self.config.get("distance_type", DistanceType.METRES_PYPROJ.value)
        )
        if distance_type == DistanceType.LONG_LAT:
            return np.hypot(
                home_positions[:, 0] - destination_position[0],
                home_positions[:, 1] - destination_position[1],
            )
        if distance_type == DistanceType.METRES_PYPROJ:
            if len(home_positions) == 1:
                return np.asarray(
                    [
                        self._geod.inv(
                            destination_position[0],
                            destination_position[1],
                            home_positions[0][0],
                            home_positions[0][1],
                        )[2]
                    ],
                    dtype=float,
                )
            _, _, distances = self._geod.inv(
                np.full(len(home_positions), destination_position[0]),
                np.full(len(home_positions), destination_position[1]),
                home_positions[:, 0],
                home_positions[:, 1],
            )
            return np.asarray(distances, dtype=float)
        return np.asarray(
            [
                geopy_distance_metre(destination_position, position)
                for position in home_positions
            ],
            dtype=float,
        )

    def _weighted_greedy_allocations(
        self,
        candidates: list[tuple[EnvNode, float]],
        quantity: int,
        pop_template: PopulationTemplate,
    ) -> list[tuple[EnvNode, int]]:
        distance_type = DistanceType(
            self.config.get("distance_type", DistanceType.METRES_PYPROJ.value)
        )
        distance_floor = 0.000001 if distance_type == DistanceType.LONG_LAT else 1.0
        ranked = []
        for node, distance in candidates:
            if not node.is_enabled():
                continue
            available = node.get_population_size(pop_template)
            if available <= 0:
                continue
            ranked.append((available / max(distance, distance_floor), node, available))
        ranked.sort(key=lambda item: (-item[0], item[1].id))

        remaining = quantity
        result = []
        for _, node, available in ranked:
            moved = min(available, remaining)
            if moved > 0:
                result.append((node, moved))
                remaining -= moved
            if remaining == 0:
                break
        return result

    def _distance_between(self, first: EnvNode, second: EnvNode) -> float:
        distance_type = DistanceType(
            self.config.get("distance_type", DistanceType.METRES_PYPROJ.value)
        )
        if distance_type == DistanceType.LONG_LAT:
            return distance2D(first.long_lat, second.long_lat)
        if distance_type == DistanceType.METRES_GEOPY:
            return geopy_distance_metre(first.long_lat, second.long_lat)
        return self._geod.inv(
            first.long_lat[0],
            first.long_lat[1],
            second.long_lat[0],
            second.long_lat[1],
        )[2]

    def popular_times_v2_action(
        self,
        pop_template: PopulationTemplate,
        values: dict,
        cycle_step: int,
        simulation_step: int,
    ):
        region_name = values.get("region")
        unique_name = values.get("node") or values.get("node_unique_name")
        if not region_name or not unique_name:
            raise ValueError("popular_times_v2 requires region and node/node_unique_name")

        destination = self.env_graph.get_node_by_unique_name(region_name, unique_name)
        if destination.node_type not in self.profiles:
            return
        requested = self.get_hourly_demand(
            destination, pop_template, cycle_step, simulation_step
        )
        record = {
            "simulation_step": simulation_step,
            "cycle_step": cycle_step,
            "weekday": (simulation_step // self.simulation.time_status.cycle_length) % 7,
            "region": destination.containing_region_name,
            "destination": destination.get_complete_name(),
            "node_type": destination.node_type,
            "paired_home": self.paired_home_name(region_name, unique_name),
            "destination_enabled": destination.is_enabled(),
            "requested": requested,
            "fulfilled": 0,
            "unmet": requested,
            "reason": "closed" if requested == 0 else "",
        }
        if requested == 0:
            self.demand_records.append(record)
            return
        if not destination.is_enabled() or self._will_flood_before_expiry(
            destination, simulation_step
        ):
            record["reason"] = "disabled_destination"
            record["anticipated_disable"] = destination.is_enabled()
            self.demand_records.append(record)
            return

        paired_home = self.env_graph.get_node_by_complete_name(
            self.paired_home_name(region_name, unique_name)
        )
        allocations = self._source_allocations(destination, requested, pop_template)
        if not allocations:
            record["reason"] = (
                "no_enabled_origins"
                if not any(node.is_enabled() for node in self._home_nodes)
                else "insufficient_population"
            )
            self.demand_records.append(record)
            return

        fulfilled = 0
        for origin, allocation in allocations:
            moved = self._start_visit(
                origin,
                destination,
                paired_home,
                allocation,
                pop_template,
                simulation_step,
            )
            fulfilled += moved

        record["fulfilled"] = fulfilled
        record["unmet"] = requested - fulfilled
        if fulfilled < requested:
            record["reason"] = "insufficient_population"
        self.demand_records.append(record)

    def _will_flood_before_expiry(
        self, destination: EnvNode, simulation_step: int
    ) -> bool:
        if not self.config.get("suppress_if_flooded_before_expiry", False):
            return False
        water_config = self.simulation.experiment_config.get(
            "water_level_data_plugin",
            self.simulation.experiment_config.get("water_level_plugin", {}),
        )
        target_types = water_config.get("target_node_types")
        if isinstance(target_types, str):
            target_types = [target_types]
        if target_types is not None and destination.node_type not in target_types:
            return False
        target_regions = water_config.get("target_regions")
        if isinstance(target_regions, str):
            target_regions = [target_regions]
        if (
            target_regions is not None
            and destination.containing_region_name not in target_regions
        ):
            return False
        threshold = destination.attributes.get("water_level")
        water_for_step = self.env_graph.data_action_map.get(
            "water_level_for_step"
        )
        if threshold is None or water_for_step is None:
            return False
        next_step = simulation_step + 1
        cycle_length = self.simulation.time_status.cycle_length
        future_level = water_for_step(next_step % cycle_length, next_step)
        return (
            future_level is not None
            and float(future_level) >= float(threshold)
        )

    def _start_visit(
        self,
        origin: EnvNode,
        destination: EnvNode,
        paired_home: EnvNode,
        quantity: int,
        pop_template: PopulationTemplate,
        simulation_step: int,
    ) -> int:
        blobs = origin.grab_population(quantity, pop_template)
        if not blobs:
            return 0
        self._visit_sequence += 1
        visit_id = self._visit_sequence
        expiry = simulation_step + 1
        moved = 0
        for blob in blobs:
            blob.set_traceable_characteristic(self.ACTIVE, True)
            blob.set_traceable_characteristic(self.VISIT_ID, visit_id)
            blob.set_traceable_characteristic(self.RETURN_NODE, origin.id)
            blob.set_traceable_characteristic(self.PAIRED_HOME, paired_home.id)
            blob.set_traceable_characteristic(self.EXPIRY_STEP, expiry)
            blob.set_traceable_characteristic(self.POI_TYPE, destination.node_type)
            blob.previous_node = origin.id
            blob.frame_origin_node = origin.id
            moved += blob.get_population_size()
        self.env_graph.log_blob_movement(origin, destination, blobs)
        destination.add_blobs(blobs)
        self.visit_records.append(
            {
                "event": "start",
                "visit_id": visit_id,
                "simulation_step": simulation_step,
                "expiry_step": expiry,
                "origin": origin.get_complete_name(),
                "destination": destination.get_complete_name(),
                "paired_home": paired_home.get_complete_name(),
                "poi_type": destination.node_type,
                "quantity": moved,
                "distance": self._distance_between(origin, destination),
                "rerouted": False,
                "reroute_reason": "",
            }
        )
        return moved

    def update_time_step(self, cycle_step: int, simulation_step: int):
        if self.env_graph is None:
            return
        due = [
            (node, blob)
            for node in self.env_graph.node_list
            for blob in list(node.contained_blobs)
            if blob.get_traceable_characteristic(self.ACTIVE)
            and blob.get_traceable_characteristic(self.EXPIRY_STEP)
            <= simulation_step
        ]
        for origin, blob in due:
            self._release_visit(origin, blob, cycle_step, simulation_step)

    def _release_visit(self, origin: EnvNode, blob, cycle_step: int, simulation_step: int):
        visit_id = blob.get_traceable_characteristic(self.VISIT_ID)
        expiry_step = blob.get_traceable_characteristic(self.EXPIRY_STEP)
        paired_home_id = blob.get_traceable_characteristic(self.PAIRED_HOME)
        poi_type = blob.get_traceable_characteristic(self.POI_TYPE)
        return_mode = self.config.get("return_mode", "prior_node")
        target_id = (
            blob.get_traceable_characteristic(self.RETURN_NODE)
            if return_mode == "prior_node"
            else blob.get_traceable_characteristic(self.PAIRED_HOME)
        )
        destination = self._enabled_node_by_id(target_id)
        rerouted = False
        reroute_reason = ""
        if destination is None:
            destination = self._enabled_node_by_id(blob.node_of_origin)
            rerouted = destination is not None
            reroute_reason = "permanent_home" if rerouted else ""
        if destination is None:
            destination = self._nearest_enabled_home(origin)
            rerouted = destination is not None
            reroute_reason = "nearest_enabled_home" if rerouted else ""
        if destination is None:
            self.visit_records.append(
                {
                    "event": "release_blocked",
                    "visit_id": visit_id,
                    "simulation_step": simulation_step,
                    "expiry_step": expiry_step,
                    "origin": origin.get_complete_name(),
                    "destination": "",
                    "paired_home": self.env_graph.get_node_by_id(
                        paired_home_id
                    ).get_complete_name(),
                    "poi_type": poi_type,
                    "quantity": blob.get_population_size(),
                    "distance": 0.0,
                    "rerouted": False,
                    "reroute_reason": "no_enabled_home",
                }
            )
            return

        origin.remove_blob(blob)
        quantity = blob.get_population_size()
        # Movement observers must see that this is an expiring Popular Times
        # visit, including when flooding disabled the POI immediately before
        # the mandatory one-hour release.
        self.env_graph.log_blob_movement(origin, destination, [blob])
        for key, value in self.TRACEABLE_DEFAULTS.items():
            blob.set_traceable_characteristic(key, value)
        blob.previous_node = origin.id
        blob.frame_origin_node = origin.id
        destination.add_blob(blob)
        self.visit_records.append(
            {
                "event": "release",
                "visit_id": visit_id,
                "simulation_step": simulation_step,
                "expiry_step": expiry_step,
                "cycle_step": cycle_step,
                "origin": origin.get_complete_name(),
                "destination": destination.get_complete_name(),
                "paired_home": self.env_graph.get_node_by_id(
                    paired_home_id
                ).get_complete_name(),
                "poi_type": poi_type,
                "quantity": quantity,
                "distance": self._distance_between(origin, destination),
                "rerouted": rerouted,
                "reroute_reason": reroute_reason,
            }
        )

    def _enabled_node_by_id(self, node_id: int) -> EnvNode | None:
        if node_id not in self.env_graph.node_id_dict:
            return None
        node = self.env_graph.get_node_by_id(node_id)
        return node if node.is_enabled() else None

    def _nearest_enabled_home(self, origin: EnvNode) -> EnvNode | None:
        distance_type = DistanceType(
            self.config.get("distance_type", DistanceType.METRES_PYPROJ.value)
        )
        distances = self.env_graph.get_node_distances(origin, distance_type)
        candidates = [
            node
            for node in self.env_graph.node_list
            if node.node_type == "home" and node.is_enabled()
        ]
        return min(
            candidates,
            key=lambda node: distances.distance_to_others.get(
                node.get_complete_name(), float("inf")
            ),
            default=None,
        )

    def unload_plugin(self):
        return
