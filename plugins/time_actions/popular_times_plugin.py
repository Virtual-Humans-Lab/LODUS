import csv
from pathlib import Path
from typing import Optional

from core.plugin import ActionPlugin
from core.simulator import LodusSimulation
from data_pop_times_generator import generate_all_popular_times


class PopularTimesPlugin(ActionPlugin):
    """Translate weekly POI demand profiles into gather-population actions."""

    def __init__(self):
        super().__init__()
        self.name = "PopularTimesPlugin"
        self.description = (
            "Loads hourly demand by POI type and delegates movement to "
            "gather_population."
        )
        self.popular_times_data_by_node_type: dict[str, list[tuple[int, int, int]]] = {}
        self.sector_multipliers: dict[str, float] = {}
        self.data_path = Path(__file__).parents[2] / "data_input" / "popular_times"

    def load_plugin(self, simulation: LodusSimulation):
        self.simulation = simulation
        self.env_graph = simulation.env_graph
        self.config = simulation.experiment_config.get("popular_times_plugin", {})
        self.data_path = Path(self.config.get("data_path", self.data_path))

        if self.config.get("generate_on_load", False):
            generate_all_popular_times(
                output_dir=self.data_path,
                sample_size=int(self.config.get("sample_size", 1000)),
                seed=self.config.get("seed", 0),
            )

        simulation.add_action_type_to_function(
            "popular_times", self.popular_times_action, False
        )

    def _load_csv_for_node_type(self, node_type: str) -> None:
        csv_path = self.data_path / f"{node_type}.csv"
        if not csv_path.is_file():
            raise FileNotFoundError(f"Popular-times data not found: {csv_path}")

        with csv_path.open("r", encoding="utf8", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            self.popular_times_data_by_node_type[node_type] = [
                (int(row["ciclo"]), int(row["hora"]), int(row["quantidade"]))
                for row in reader
            ]

    def _load_sector_multipliers(self) -> None:
        filename = self.config.get(
            "sector_multiplier_file", "Setores-13Bairros-Dia.csv"
        )
        csv_path = self.data_path / filename
        if not csv_path.is_file():
            raise FileNotFoundError(f"Sector multiplier data not found: {csv_path}")

        with csv_path.open("r", encoding="utf8", newline="") as csvfile:
            for row in csv.reader(csvfile):
                if len(row) < 2:
                    continue
                try:
                    self.sector_multipliers[row[0].strip().lower()] = float(row[1])
                except ValueError:
                    continue

    def get_quantity_for_hour(
        self,
        sim_step: int,
        node_type: str,
        hour: int,
        region: Optional[str],
        node: Optional[str] = None,
    ) -> int:
        if node_type not in self.popular_times_data_by_node_type:
            return 0

        cycle_length = self.simulation.cycle_lenght
        weekday = (sim_step // cycle_length) % 7
        base_quantity = next(
            (
                quantity
                for cycle, profile_hour, quantity in self.popular_times_data_by_node_type[
                    node_type
                ]
                if cycle == weekday and profile_hour == hour
            ),
            0,
        )

        if not region:
            return base_quantity

        if not self.sector_multipliers:
            self._load_sector_multipliers()

        region_key = region.strip().lower()
        if node:
            node_parts = node.split("_", 1)
            if len(node_parts) == 2:
                region_key = f"{region_key}//home_{node_parts[1]}"

        multiplier = self.sector_multipliers.get(region_key, 1.0)
        scale_divisor = float(self.config.get("scale_divisor", 10))
        if scale_divisor <= 0:
            raise ValueError("popular_times_plugin.scale_divisor must be positive")
        return int(round(base_quantity * multiplier / scale_divisor))

    def popular_times_action(
        self, pop_template, values: dict, cycle_step: int, sim_step: int
    ):
        node_type = values.get("node_type")
        if not node_type:
            raise ValueError("node_type is required by the popular_times action")

        unique_node_name = values.get("node") or values.get("node_unique_name")
        if not unique_node_name:
            raise ValueError("node or node_unique_name is required by popular_times")

        if node_type not in self.popular_times_data_by_node_type:
            self._load_csv_for_node_type(node_type)

        region = values.get("region")
        quantity = self.get_quantity_for_hour(
            sim_step, node_type, cycle_step, region, unique_node_name
        )
        gather_population = self.simulation.routine_controller.action_type_to_function.get(
            "gather_population"
        )
        if gather_population is None:
            raise RuntimeError(
                "PopularTimesPlugin requires GatherPopulationPlugin to be loaded"
            )

        return gather_population(
            pop_template,
            {
                "region": region,
                "node": unique_node_name,
                "quantity": quantity,
                "different_node_name": values.get("different_node_name", False),
            },
            cycle_step,
            sim_step,
        )

    def update_time_step(self, cycle_step: int, simulation_step: int):
        pass

    def unload_plugin(self):
        pass
