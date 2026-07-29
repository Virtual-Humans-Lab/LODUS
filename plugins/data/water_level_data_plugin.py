from __future__ import annotations

from pathlib import Path
from typing import Any
import csv
import json

from core.environment import EnvironmentGraph
from core.plugin import ActionPlugin
from core.simulator import LodusSimulation


class WaterLevelDataPlugin(ActionPlugin):
    """Provides water-level data over the simulation timeline."""

    def __init__(self, graph: EnvironmentGraph | None = None):
        super().__init__()
        self.__header = "Water Level Plugin:"
        self.graph = graph
        self.config: dict[str, Any] = {}
        self.water_level_data: dict[tuple[int, int], float] = {}
        self.ordered_steps: list[tuple[int, int]] = []
        self.current_water_level: float | None = None
        self.cycle_length = 24
        self.cycle_step = 0
        self.sim_step = 0
        self.cycle = 0
        self._is_setup = False
        self.target_node_types: set[str] | None = None
        self.target_regions: set[str] | None = None

    def load_plugin(self, simulation: LodusSimulation):
        self.graph = simulation.env_graph
        self.cycle_length = simulation.time_status.cycle_length
        self._setup(simulation.experiment_config)

    def unload_plugin(self):
        return

    def _setup(self, experiment_config: dict[str, Any]):
        if self.graph is None:
            raise ValueError("WaterLevelPlugin requires an EnvironmentGraph.")
        if self._is_setup:
            return

        self.config = dict(
            experiment_config.get(
                "water_level_data_plugin",
                experiment_config.get("water_level_plugin", {}),
            )
        )
        self._load_configuration_file()

        data_file = self.config.get("data_file")
        if data_file is None:
            legacy_files = self.config.get("water_level_files", [])
            if isinstance(legacy_files, str):
                legacy_files = [legacy_files]
            data_file = (
                legacy_files[0]
                if legacy_files
                else "water_level/flood_time_step.csv"
            )
        self.target_node_types = self._optional_string_set(
            self.config.get("target_node_types")
        )
        self.target_regions = self._optional_string_set(
            self.config.get("target_regions")
        )
        self.water_level_data = self._read_water_level_data(data_file)
        self.ordered_steps = sorted(self.water_level_data)

        if not self.ordered_steps:
            raise ValueError(f"{self.__header} No water-level data available.")

        self.current_water_level = self.water_level_data[self.ordered_steps[0]]
        self.graph.data_action_map["water_level"] = self.get_water_level
        self.graph.data_action_map["current_water_level"] = self.get_water_level
        self.graph.data_action_map["water_level_for_step"] = self.get_water_level_for_step

        print(f"{self.__header} Loaded {len(self.ordered_steps)} water-level steps.")
        self._is_setup = True

    def _load_configuration_file(self):
        if "configuration_file" not in self.config:
            return

        config_path = Path(self.config["configuration_file"])
        if not config_path.is_absolute():
            config_path = Path(__file__).resolve().parents[2] / "data_input" / config_path

        with open(config_path, "r", encoding="utf8") as config_file:
            loaded_config = json.load(config_file)

        for key, value in self.config.items():
            loaded_config[key] = value
        self.config = loaded_config

    def _read_water_level_data(self, data_file: str | Path) -> dict[tuple[int, int], float]:
        data_path = Path(data_file)
        if not data_path.is_absolute():
            data_path = Path(__file__).resolve().parents[2] / "data_input" / data_path

        if not data_path.exists():
            raise FileNotFoundError(f"{self.__header} Water-level file not found: {data_path}")

        water_level_data: dict[tuple[int, int], float] = {}
        last_water_level: float | None = self.config.get("initial_water_level")

        with open(data_path, "r", encoding="utf8", newline="") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=self.config.get("delimiter", ";"))
            required_columns = {"cycle", "cycle_step", "water_level"}
            if reader.fieldnames is None or not required_columns.issubset(reader.fieldnames):
                raise ValueError(
                    f"{self.__header} Expected CSV columns: cycle, cycle_step, water_level"
                )

            for row in reader:
                cycle = int(row["cycle"])
                cycle_step = int(row["cycle_step"])
                raw_water_level = row.get("water_level", "").strip()

                if raw_water_level:
                    last_water_level = float(raw_water_level.replace(",", "."))

                if last_water_level is not None:
                    water_level_data[(cycle, cycle_step)] = last_water_level

        return water_level_data

    def update_time_step(self, cycle_step: int, simulation_step: int):
        self.cycle_step = cycle_step
        self.sim_step = simulation_step
        self.cycle = simulation_step // self._get_cycle_length()
        self.current_water_level = self.get_water_level_for_step(cycle_step, simulation_step)
        self.update_nodes_due_to_water_level()

    def update_nodes_due_to_water_level(self):
        if self.graph is None:
            return

        if self.current_water_level is None:
            return

        for node in self.graph.node_list:
            if (
                self.target_node_types is not None
                and node.node_type not in self.target_node_types
            ):
                continue
            if (
                self.target_regions is not None
                and node.containing_region_name not in self.target_regions
            ):
                continue
            threshold = node.attributes.get("water_level")
            if threshold is None:
                continue
            flooded = self.current_water_level >= float(threshold)
            has_flood_blocker = "flood" in node.disable_reasons
            if flooded == has_flood_blocker:
                continue
            self.graph.set_node_enabled(
                node.get_complete_name(),
                enabled=not flooded,
                cascade_reenable=True,
                cause="flood",
                simulation_step=self.sim_step,
                cycle_step=self.cycle_step,
            )

    # Backwards-compatible alias used by older callers.
    def disable_nodes_due_to_water_level(self):
        self.update_nodes_due_to_water_level()


    def get_water_level(self, *args, **kwargs) -> float | None:
        return self.current_water_level

    def get_water_level_for_step(self, cycle_step: int, simulation_step: int) -> float | None:
        if self.graph is None:
            return None

        cycle = simulation_step // self._get_cycle_length()
        requested_step = (cycle, cycle_step)

        if requested_step in self.water_level_data:
            return self.water_level_data[requested_step]

        previous_level = None
        for step in self.ordered_steps:
            if step > requested_step:
                break
            previous_level = self.water_level_data[step]

        return previous_level

    def _get_cycle_length(self) -> int:
        if self.graph is not None and hasattr(self.graph, "routine_cycle_length"):
            return self.graph.routine_cycle_length
        return self.cycle_length

    @staticmethod
    def _optional_string_set(value) -> set[str] | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            raise ValueError(
                "target_node_types and target_regions must be strings or lists of strings"
            )
        return set(value)
