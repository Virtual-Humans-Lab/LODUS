from __future__ import annotations

import math
from typing import Any

import numpy as np
from pyproj import Geod

from core.environment import EnvNode
from core.population import PopulationTemplate
from core.simulator import LodusSimulation
from plugins.time_actions.levy_walk_plugin import LevyWalkPlugin
from util.math import DistanceType, distance2D, geopy_distance_metre


class LevyWalkV2Plugin(LevyWalkPlugin):
    """Cycle-budgeted, flood-aware work and school mobility."""

    ACTION_TYPE = "levy_walk_v2"
    CONFIG_KEY = "levy_walk_v2_plugin"

    ACTIVE = "levy_walk_v2_active"
    COMMUTE_ID = "levy_walk_v2_commute_id"
    ORIGINAL_HOME = "levy_walk_v2_original_home"
    EXPIRY_STEP = "levy_walk_v2_expiry_step"
    GROUP = "levy_walk_v2_group"
    REQUESTED_DESTINATION = "levy_walk_v2_requested_destination"
    RECEIVING_DESTINATION = "levy_walk_v2_receiving_destination"
    LAST_ATTENDANCE_CYCLE = "levy_walk_v2_last_attendance_cycle"
    TEMPORARILY_DISPLACED = "levy_walk_v2_temporarily_displaced"

    TRACEABLE_DEFAULTS = {
        ACTIVE: False,
        COMMUTE_ID: -1,
        ORIGINAL_HOME: -1,
        EXPIRY_STEP: -1,
        GROUP: "",
        REQUESTED_DESTINATION: -1,
        RECEIVING_DESTINATION: -1,
        LAST_ATTENDANCE_CYCLE: -1,
        TEMPORARILY_DISPLACED: False,
    }

    DEFAULT_GROUPS = {
        "worker": {
            "population_template": {"occupation": ["worker"]},
            "target_node_type": "work",
            "cycle_attendance_rate": 1.0,
            "stay_duration_steps": 8,
            "hourly_weights": {
                "0": 0.025,
                "1": 0.025,
                "2": 0.025,
                "3": 0.025,
                "4": 0.025,
                "5": 0.025,
                "6": 0.1,
                "7": 0.25,
                "8": 0.4,
                "9": 0.4,
                "10": 0.4,
                "11": 0.1,
                "12": 0.35,
                "13": 0.1,
                "14": 0.1,
                "15": 0.1,
                "16": 0.35,
                "17": 0.1,
                "18": 0.1,
                "19": 0.1,
                "20": 0.2,
                "21": 0.025,
                "22": 0.025,
                "23": 0.025,
            },
        },
        "student": {
            "population_template": {"occupation": ["student"]},
            "target_node_type": "school",
            "cycle_attendance_rate": 1.0,
            "stay_duration_steps": 4,
            "hourly_weights": {"8": 1.65, "13": 1.65, "19": 0.9},
        },
    }

    def __init__(self):
        super().__init__()
        self.simulation: LodusSimulation | None = None
        self.config: dict[str, Any] = {}
        self.groups: dict[str, dict[str, Any]] = {}
        self._home_nodes: list[EnvNode] = []
        self._schedule: dict[tuple[str, int, int], int] = {}
        self._cycle_targets: dict[str, int] = {}
        self._commute_sequence = 0
        self._future_disable_cache: dict[tuple[int, int, int], bool] = {}
        self._reroute_cache: dict[int, list[tuple[EnvNode, float]]] = {}
        self._bucket_sampling_cache: dict[
            tuple[int, str], tuple[list[int], list[float], float]
        ] = {}
        self.dist_buckets: dict[tuple, dict[int, np.ndarray]] = {}
        self.distance_lists: dict[tuple, list[tuple[str, float]]] = {}
        self._target_node_cache: dict[tuple, list[EnvNode]] = {}
        self._geod = Geod(ellps="WGS84")
        self.sampled_distances: list[float] = []
        self.duplicate_attendance_population = 0
        self.demand_records: list[dict[str, Any]] = []
        self.movement_records: list[dict[str, Any]] = []

    def load_plugin(self, simulation: LodusSimulation):
        self.simulation = simulation
        self.env_graph = simulation.env_graph
        self.config = dict(simulation.experiment_config.get(self.CONFIG_KEY, {}))
        self._load_configuration()

        for key, value in self.TRACEABLE_DEFAULTS.items():
            self.env_graph.add_blobs_traceable_property(key, value)

        self._home_nodes = sorted(
            self.env_graph.get_nodes_by_type("home"),
            key=lambda node: node.get_complete_name(),
        )
        self._build_cycle_schedule()
        self._configure_distance_sampler()
        simulation.add_action_type_to_function(
            self.ACTION_TYPE, self.levy_walk_v2_action, True
        )

    def _load_configuration(self) -> None:
        if self.config.get("demand_basis", "original_population") != "original_population":
            raise ValueError(
                "levy_walk_v2_plugin.demand_basis must be 'original_population'"
            )
        packet_size = self.config.get("packet_size", 50)
        if not isinstance(packet_size, int) or packet_size <= 0:
            raise ValueError("levy_walk_v2_plugin.packet_size must be a positive integer")
        self.config["packet_size"] = packet_size

        origin_policy = self.config.get("disabled_origin_policy", "suppress")
        if origin_policy != "suppress":
            raise ValueError(
                "levy_walk_v2_plugin.disabled_origin_policy must be 'suppress'"
            )
        destination_policy = self.config.get(
            "disabled_destination_policy", "suppress"
        )
        if destination_policy not in {"suppress", "nearest_enabled_same_type"}:
            raise ValueError(
                "levy_walk_v2_plugin.disabled_destination_policy must be "
                "'suppress' or 'nearest_enabled_same_type'"
            )
        return_policy = self.config.get(
            "return_home_policy", "nearest_enabled_home"
        )
        if return_policy != "nearest_enabled_home":
            raise ValueError(
                "levy_walk_v2_plugin.return_home_policy must be "
                "'nearest_enabled_home'"
            )
        for key in (
            "suppress_if_disabled_before_return",
            "repatriate_on_reenable",
        ):
            value = self.config.get(key, True)
            if not isinstance(value, bool):
                raise ValueError(f"levy_walk_v2_plugin.{key} must be a boolean")
            self.config[key] = value

        configured_groups = self.config.get("groups", {})
        if not isinstance(configured_groups, dict):
            raise ValueError("levy_walk_v2_plugin.groups must be an object")
        for name, defaults in self.DEFAULT_GROUPS.items():
            values = {**defaults, **configured_groups.get(name, {})}
            rate = values.get("cycle_attendance_rate")
            duration = values.get("stay_duration_steps")
            if not isinstance(rate, (int, float)) or not 0 <= rate <= 1:
                raise ValueError(f"Cycle attendance rate for {name} must be in [0, 1]")
            if not isinstance(duration, int) or duration <= 0:
                raise ValueError(f"Stay duration for {name} must be a positive integer")
            raw_weights = values.get("hourly_weights")
            if not isinstance(raw_weights, dict) or not raw_weights:
                raise ValueError(f"Hourly weights for {name} must be a non-empty object")
            weights: dict[int, float] = {}
            for raw_hour, raw_weight in raw_weights.items():
                hour = int(raw_hour)
                weight = float(raw_weight)
                if not 0 <= hour < 24 or weight < 0:
                    raise ValueError(f"Invalid hourly weight for {name}: {raw_hour}")
                weights[hour] = weight
            total_weight = sum(weights.values())
            if total_weight <= 0:
                raise ValueError(f"Hourly weights for {name} must sum above zero")
            values["hourly_weights"] = {
                hour: weight / total_weight for hour, weight in sorted(weights.items())
            }
            template = values.get("population_template")
            if not isinstance(template, dict) or not template:
                raise ValueError(f"Population template for {name} must be an object")
            target_type = values.get("target_node_type")
            if not isinstance(target_type, str) or not target_type:
                raise ValueError(f"Target node type for {name} must be a string")
            self.groups[name] = values

    def _configure_distance_sampler(self) -> None:
        from scipy.stats import levy as scipy_levy
        from util.random_instance import FixedRandom

        self.distribution_sampler = scipy_levy
        self.random = FixedRandom.instance
        self.distance_type = DistanceType(
            self.config.get("distance_type", DistanceType.METRES_PYPROJ.value)
        )
        self.use_buckets = bool(self.config.get("use_buckets", True))
        self.bucket_size = float(self.config.get("distance_bucket_size", 500))
        self.distribution_location = float(
            self.config.get("distribution_location", 0.0)
        )
        self.distribution_scale = float(self.config.get("distribution_scale", 1000))
        if self.bucket_size <= 0 or self.distribution_scale <= 0:
            raise ValueError("Levy V2 distance bucket and scale must be positive")

    @staticmethod
    def _largest_remainder(total: int, weights: list[float]) -> list[int]:
        if total <= 0:
            return [0] * len(weights)
        weight_total = sum(weights)
        if weight_total <= 0:
            return [0] * len(weights)
        exact = [total * weight / weight_total for weight in weights]
        allocated = [math.floor(value) for value in exact]
        remaining = total - sum(allocated)
        order = sorted(
            range(len(weights)), key=lambda index: (-(exact[index] % 1), index)
        )
        for index in order[:remaining]:
            allocated[index] += 1
        return allocated

    def _group_template(self, group: str, cycle: int | None = None) -> PopulationTemplate:
        traceable = {}
        if cycle is not None:
            traceable = {
                self.ACTIVE: False,
                self.LAST_ATTENDANCE_CYCLE: lambda value: value != cycle,
            }
        return PopulationTemplate(
            sampled_characteristics=self.groups[group]["population_template"],
            traceable_characteristics=traceable,
        )

    def _original_population(self, home: EnvNode, group: str) -> int:
        if home.original_node_population is None:
            return 0
        return home.original_node_population.get_population_size(
            self._group_template(group)
        )

    def _build_cycle_schedule(self) -> None:
        for group, config in self.groups.items():
            populations = [self._original_population(home, group) for home in self._home_nodes]
            total_population = sum(populations)
            target = round(total_population * float(config["cycle_attendance_rate"]))
            self._cycle_targets[group] = target
            home_targets = self._largest_remainder(target, populations)
            hours = list(config["hourly_weights"])
            hour_weights = list(config["hourly_weights"].values())
            for home, home_target in zip(self._home_nodes, home_targets):
                hourly = self._largest_remainder(home_target, hour_weights)
                for hour, quantity in zip(hours, hourly):
                    self._schedule[(group, home.id, hour)] = quantity

    def get_cycle_target(self, group: str) -> int:
        return self._cycle_targets[group]

    def get_scheduled_demand(self, group: str, home: EnvNode, hour: int) -> int:
        return self._schedule.get((group, home.id, hour), 0)

    def levy_walk_v2_action(
        self,
        pop_template: PopulationTemplate,
        values: dict,
        cycle_step: int,
        simulation_step: int,
    ) -> None:
        group = values.get("group")
        if group not in self.groups:
            raise ValueError(f"Unknown Levy V2 group: {group}")
        node_id = values.get("node_id")
        if node_id is None:
            raise ValueError("levy_walk_v2 requires node_id")
        home = self.env_graph.get_node_by_id(node_id)
        if home.node_type != "home":
            return
        requested = self.get_scheduled_demand(group, home, cycle_step)
        if requested <= 0:
            return

        packet_size = self.config["packet_size"]
        remaining = requested
        while remaining > 0:
            quantity = min(packet_size, remaining)
            self._process_packet(home, group, quantity, cycle_step, simulation_step)
            remaining -= quantity

    def _process_packet(
        self,
        home: EnvNode,
        group: str,
        quantity: int,
        cycle_step: int,
        simulation_step: int,
    ) -> None:
        cycle = simulation_step // self.simulation.time_status.cycle_length
        group_config = self.groups[group]
        target_type = group_config["target_node_type"]
        duration = int(group_config["stay_duration_steps"])
        requested_destination = self._sample_requested_destination(home, target_type)
        base = {
            "simulation_step": simulation_step,
            "cycle_step": cycle_step,
            "cycle": cycle,
            "group": group,
            "node_type": target_type,
            "origin": home.get_complete_name(),
            "original_home": home.get_complete_name(),
            "original_population": self._original_population(home, group),
            "requested_destination": (
                requested_destination.get_complete_name()
                if requested_destination is not None
                else ""
            ),
            "receiving_destination": "",
            "requested": quantity,
            "fulfilled": 0,
            "unmet": quantity,
            "reason": "",
            "packet_size": quantity,
            "blob_count": 0,
            "destination_rerouted": False,
            "reroute_reason": "",
            "reroute_distance": 0.0,
            "movement_distance": 0.0,
            "receiving_load": 0,
            "expiry_step": simulation_step + duration,
        }
        if requested_destination is None:
            base["reason"] = "no_destination_candidate"
            self.demand_records.append(base)
            return
        base["receiving_destination"] = requested_destination.get_complete_name()

        if not home.is_enabled():
            base["reason"] = "origin_disabled"
            self.demand_records.append(base)
            return

        anticipated = self._will_disable_before_return(
            requested_destination, simulation_step, duration
        )
        unavailable = not requested_destination.is_enabled() or anticipated
        receiving_destination = requested_destination
        if unavailable:
            base["reason"] = (
                "anticipated_destination_disable"
                if requested_destination.is_enabled()
                else "destination_disabled"
            )
            if self.config.get("disabled_destination_policy", "suppress") == "suppress":
                self.demand_records.append(base)
                return
            alternative = self._nearest_available_destination(
                requested_destination, simulation_step, duration
            )
            if alternative is None:
                base["reason"] = "no_enabled_alternative"
                self.demand_records.append(base)
                return
            receiving_destination, displacement = alternative
            base["receiving_destination"] = receiving_destination.get_complete_name()
            base["destination_rerouted"] = True
            base["reroute_reason"] = base["reason"]
            base["reroute_distance"] = displacement
            base["reason"] = ""

        template = self._group_template(group, cycle)
        blobs = home.grab_population(quantity, template)
        moved = sum(blob.get_population_size() for blob in blobs)
        if moved:
            self._commute_sequence += 1
            commute_id = self._commute_sequence
            expiry = simulation_step + duration
            for blob in blobs:
                if blob.get_traceable_characteristic(self.LAST_ATTENDANCE_CYCLE) == cycle:
                    self.duplicate_attendance_population += blob.get_population_size()
                blob.set_traceable_characteristic(self.ACTIVE, True)
                blob.set_traceable_characteristic(self.COMMUTE_ID, commute_id)
                blob.set_traceable_characteristic(self.ORIGINAL_HOME, home.id)
                blob.set_traceable_characteristic(self.EXPIRY_STEP, expiry)
                blob.set_traceable_characteristic(self.GROUP, group)
                blob.set_traceable_characteristic(
                    self.REQUESTED_DESTINATION, requested_destination.id
                )
                blob.set_traceable_characteristic(
                    self.RECEIVING_DESTINATION, receiving_destination.id
                )
                blob.set_traceable_characteristic(
                    self.LAST_ATTENDANCE_CYCLE, cycle
                )
                blob.set_traceable_characteristic(self.TEMPORARILY_DISPLACED, False)
                blob.previous_node = home.id
                blob.frame_origin_node = home.id
            self.env_graph.log_blob_movement(home, receiving_destination, blobs)
            receiving_destination.add_blobs(blobs)
            distance = self._distance_between(home, receiving_destination)
            self.movement_records.append(
                {
                    "event": "departure",
                    "commute_id": commute_id,
                    "simulation_step": simulation_step,
                    "cycle_step": cycle_step,
                    "cycle": cycle,
                    "group": group,
                    "origin": home.get_complete_name(),
                    "destination": receiving_destination.get_complete_name(),
                    "requested_destination": requested_destination.get_complete_name(),
                    "receiving_destination": receiving_destination.get_complete_name(),
                    "original_home": home.get_complete_name(),
                    "expiry_step": expiry,
                    "quantity": moved,
                    "blob_count": len(blobs),
                    "distance": distance,
                    "rerouted": requested_destination.id != receiving_destination.id,
                    "reroute_reason": base["reroute_reason"],
                    "reroute_distance": base["reroute_distance"],
                }
            )
            base["movement_distance"] = distance
        base["fulfilled"] = moved
        base["unmet"] = quantity - moved
        base["blob_count"] = len(blobs)
        base["receiving_load"] = receiving_destination.get_population_size(
            PopulationTemplate(traceable_characteristics={self.ACTIVE: True})
        )
        if moved < quantity:
            base["reason"] = "insufficient_population"
        self.demand_records.append(base)

    def _sample_requested_destination(
        self, origin: EnvNode, target_type: str
    ) -> EnvNode | None:
        if self.use_buckets:
            distances = self.get_node_distance_bucket(
                origin, self.env_graph, [target_type], False
            )
            if not self._has_distance_targets(distances):
                return None
            return self._sample_bucket_destination(origin, target_type, distances)
        else:
            distances = self.get_node_distance(
                origin, self.env_graph, [target_type], False
            )
        if not self._has_distance_targets(distances):
            return None
        name = self.select_valid_target(
            self.distribution_location,
            self.distribution_scale,
            self.use_buckets,
            distances,
        )
        return self.env_graph.get_node_by_complete_name(name)

    def _sample_bucket_destination(
        self,
        origin: EnvNode,
        target_type: str,
        distances: dict[int, np.ndarray],
    ) -> EnvNode:
        """Sample the legacy Levy distribution conditional on occupied buckets.

        The legacy implementation repeatedly draws until it hits a non-empty
        distance bucket. Computing each occupied bucket's CDF mass once is the
        same conditional distribution and avoids millions of rejected SciPy
        draws in the production matrix.
        """
        key = (origin.id, target_type)
        cached = self._bucket_sampling_cache.get(key)
        if cached is None:
            buckets = sorted(distances)
            cumulative = []
            running = 0.0
            for bucket in buckets:
                lower = bucket * self.bucket_size
                upper = (bucket + 1) * self.bucket_size
                mass = float(
                    self.distribution_sampler.cdf(
                        upper,
                        loc=self.distribution_location,
                        scale=self.distribution_scale,
                    )
                    - self.distribution_sampler.cdf(
                        lower,
                        loc=self.distribution_location,
                        scale=self.distribution_scale,
                    )
                )
                running += max(0.0, mass)
                cumulative.append(running)
            if running <= 0:
                raise ValueError("Levy V2 target buckets have zero probability mass")
            cached = (buckets, cumulative, running)
            self._bucket_sampling_cache[key] = cached
        buckets, cumulative, total = cached
        draw = self.random.random() * total
        selected_index = next(
            index for index, threshold in enumerate(cumulative) if draw <= threshold
        )
        bucket = buckets[selected_index]
        candidates = distances[bucket]
        candidate_id = int(candidates[self.random.randint(0, len(candidates) - 1)])
        self.sampled_distances.append((bucket + 0.5) * self.bucket_size)
        return self.env_graph.get_node_by_id(candidate_id)

    def _nearest_available_destination(
        self, requested: EnvNode, simulation_step: int, duration: int
    ) -> tuple[EnvNode, float] | None:
        if requested.id not in self._reroute_cache:
            candidates = [
                node
                for node in self.env_graph.node_list
                if node.id != requested.id and node.node_type == requested.node_type
            ]
            ranked = [(node, self._distance_between(requested, node)) for node in candidates]
            ranked.sort(key=lambda item: (item[1], item[0].get_complete_name()))
            self._reroute_cache[requested.id] = ranked
        return next(
            (
                (node, distance)
                for node, distance in self._reroute_cache[requested.id]
                if node.is_enabled()
                and not self._will_disable_before_return(node, simulation_step, duration)
            ),
            None,
        )

    def _will_disable_before_return(
        self, node: EnvNode, simulation_step: int, duration: int
    ) -> bool:
        if not self.config.get("suppress_if_disabled_before_return", True):
            return False
        key = (node.id, simulation_step, duration)
        if key in self._future_disable_cache:
            return self._future_disable_cache[key]
        water_config = self.simulation.experiment_config.get("water_level_data_plugin", {})
        targets = water_config.get("target_node_types")
        if isinstance(targets, str):
            targets = [targets]
        if targets is not None and node.node_type not in targets:
            self._future_disable_cache[key] = False
            return False
        threshold = node.attributes.get("water_level")
        water_for_step = self.env_graph.data_action_map.get("water_level_for_step")
        if threshold is None or water_for_step is None:
            self._future_disable_cache[key] = False
            return False
        cycle_length = self.simulation.time_status.cycle_length
        result = False
        for future_step in range(simulation_step + 1, simulation_step + duration + 1):
            level = water_for_step(future_step % cycle_length, future_step)
            if level is not None and float(level) >= float(threshold):
                result = True
                break
        self._future_disable_cache[key] = result
        return result

    def update_time_step(self, cycle_step: int, simulation_step: int):
        if self.env_graph is None:
            return
        self._future_disable_cache.clear()
        if cycle_step == 0:
            self._reset_attendance_markers()
        self._release_due_commuters(cycle_step, simulation_step)
        if self.config.get("repatriate_on_reenable", True):
            self._repatriate(cycle_step, simulation_step)

    def _reset_attendance_markers(self) -> None:
        """Discard prior-cycle eligibility markers before the new cycle starts."""
        for node in self.env_graph.node_list:
            for blob in node.contained_blobs:
                if blob.get_traceable_characteristic(self.LAST_ATTENDANCE_CYCLE) != -1:
                    blob.set_traceable_characteristic(
                        self.LAST_ATTENDANCE_CYCLE, -1
                    )

    def _release_due_commuters(self, cycle_step: int, simulation_step: int) -> None:
        due = [
            (node, blob)
            for node in self.env_graph.node_list
            for blob in list(node.contained_blobs)
            if blob.get_traceable_characteristic(self.ACTIVE)
            and blob.get_traceable_characteristic(self.EXPIRY_STEP) <= simulation_step
        ]
        for origin, blob in due:
            self._release_commuter(origin, blob, cycle_step, simulation_step)

    def _release_commuter(
        self, origin: EnvNode, blob, cycle_step: int, simulation_step: int
    ) -> None:
        home = self.env_graph.get_node_by_id(
            blob.get_traceable_characteristic(self.ORIGINAL_HOME)
        )
        destination = home if home.is_enabled() else self._nearest_enabled_home(origin)
        if not origin.is_enabled() or destination is None:
            self.movement_records.append(
                self._movement_record(
                    "return_blocked", origin, None, blob, cycle_step, simulation_step
                )
            )
            return
        origin.remove_blob(blob)
        expiry_step = blob.get_traceable_characteristic(self.EXPIRY_STEP)
        self.env_graph.log_blob_movement(origin, destination, [blob])
        temporary = destination.id != home.id
        blob.set_traceable_characteristic(self.ACTIVE, False)
        blob.set_traceable_characteristic(self.EXPIRY_STEP, -1)
        blob.set_traceable_characteristic(self.TEMPORARILY_DISPLACED, temporary)
        blob.previous_node = origin.id
        blob.frame_origin_node = origin.id
        event = "temporary_return" if temporary else "return"
        record = self._movement_record(
            event,
            origin,
            destination,
            blob,
            cycle_step,
            simulation_step,
            expiry_step=expiry_step,
        )
        if not temporary:
            self._clear_completed_commute(blob)
        destination.add_blob(blob)
        self.movement_records.append(record)

    def _repatriate(self, cycle_step: int, simulation_step: int) -> None:
        displaced = [
            (node, blob)
            for node in self.env_graph.node_list
            for blob in list(node.contained_blobs)
            if blob.get_traceable_characteristic(self.TEMPORARILY_DISPLACED)
            and not blob.get_traceable_characteristic(self.ACTIVE)
        ]
        for origin, blob in displaced:
            home = self.env_graph.get_node_by_id(
                blob.get_traceable_characteristic(self.ORIGINAL_HOME)
            )
            if origin.id == home.id:
                blob.set_traceable_characteristic(self.TEMPORARILY_DISPLACED, False)
                continue
            if not origin.is_enabled() or not home.is_enabled():
                continue
            origin.remove_blob(blob)
            self.env_graph.log_blob_movement(origin, home, [blob])
            blob.previous_node = origin.id
            blob.frame_origin_node = origin.id
            record = self._movement_record(
                "repatriation", origin, home, blob, cycle_step, simulation_step
            )
            self._clear_completed_commute(blob)
            home.add_blob(blob)
            self.movement_records.append(record)

    def _clear_completed_commute(self, blob) -> None:
        """Clear per-trip identity so completed travelers can merge again."""
        for key, value in self.TRACEABLE_DEFAULTS.items():
            if key != self.LAST_ATTENDANCE_CYCLE:
                blob.set_traceable_characteristic(key, value)

    def _movement_record(
        self,
        event: str,
        origin: EnvNode,
        destination: EnvNode | None,
        blob,
        cycle_step: int,
        simulation_step: int,
        expiry_step: int | None = None,
    ) -> dict[str, Any]:
        requested_id = blob.get_traceable_characteristic(self.REQUESTED_DESTINATION)
        receiving_id = blob.get_traceable_characteristic(self.RECEIVING_DESTINATION)
        home_id = blob.get_traceable_characteristic(self.ORIGINAL_HOME)
        return {
            "event": event,
            "commute_id": blob.get_traceable_characteristic(self.COMMUTE_ID),
            "simulation_step": simulation_step,
            "cycle_step": cycle_step,
            "cycle": simulation_step // self.simulation.time_status.cycle_length,
            "group": blob.get_traceable_characteristic(self.GROUP),
            "origin": origin.get_complete_name(),
            "destination": destination.get_complete_name() if destination else "",
            "requested_destination": self.env_graph.get_node_by_id(
                requested_id
            ).get_complete_name(),
            "receiving_destination": self.env_graph.get_node_by_id(
                receiving_id
            ).get_complete_name(),
            "original_home": self.env_graph.get_node_by_id(home_id).get_complete_name(),
            "expiry_step": (
                blob.get_traceable_characteristic(self.EXPIRY_STEP)
                if expiry_step is None
                else expiry_step
            ),
            "quantity": blob.get_population_size(),
            "blob_count": 1,
            "distance": (
                self._distance_between(origin, destination) if destination else 0.0
            ),
            "rerouted": event in {"temporary_return", "repatriation"},
            "reroute_reason": (
                "nearest_enabled_home" if event == "temporary_return" else ""
            ),
            "reroute_distance": 0.0,
        }

    def _nearest_enabled_home(self, origin: EnvNode) -> EnvNode | None:
        candidates = [
            node
            for node in self._home_nodes
            if node.is_enabled() and node.id != origin.id
        ]
        return min(
            candidates,
            key=lambda node: (
                self._distance_between(origin, node), node.get_complete_name()
            ),
            default=None,
        )

    def _distance_between(self, first: EnvNode, second: EnvNode) -> float:
        if self.distance_type == DistanceType.LONG_LAT:
            return distance2D(first.long_lat, second.long_lat)
        if self.distance_type == DistanceType.METRES_GEOPY:
            return geopy_distance_metre(first.long_lat, second.long_lat)
        return self._geod.inv(
            first.long_lat[0],
            first.long_lat[1],
            second.long_lat[0],
            second.long_lat[1],
        )[2]

    def unload_plugin(self):
        return
