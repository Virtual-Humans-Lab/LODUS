import csv
import json
import tempfile
import unittest
from pathlib import Path

from core.environment import EnvNode, EnvRegionTemplate, EnvironmentGraph
from core.population import BlobFactory, CharacteristicsFactory, PopulationTemplate
from core.simulator import LodusSimulation
from misc_scripts.run_popular_times_v2_pilot import SCENARIOS
from misc_scripts.generate_popular_times_v2_levy_routine import build_routine
from plugins.loggers.popular_times_v2_logger import PopularTimesV2Logger
from plugins.time_actions.popular_times_v2_plugin import PopularTimesV2Plugin
from util.data_parse import load_experiment_config
from util.random_instance import FixedRandom


class PopularTimesStage3ConfigurationTest(unittest.TestCase):
    def test_primary_matrix_contains_the_ten_approved_scenarios(self):
        self.assertEqual(len(SCENARIOS), 10)
        combinations = set()
        for scenario in SCENARIOS:
            config = load_experiment_config(
                f"popular_times_v2/scenarios/{scenario}"
            )
            study = config["popular_times_v2_study"]
            combinations.add(
                (str(study["environment"]), bool(study["levy"]), study["flood"])
            )
            expected_cycles = 5 if str(study["environment"]) == "94" else 56
            self.assertEqual(
                config["simulation_parameters"]["total_cycles"], expected_cycles
            )
            self.assertEqual(config["simulation_parameters"]["cycle_length"], 24)
            self.assertEqual(config["simulation_parameters"]["random_seed"], 0)
            self.assertIn("popular_times_v2_logger", config)
        expected = {
            ("13", levy, flood)
            for levy in (False, True)
            for flood in ("none", "pois", "homes", "both")
        } | {("94", levy, "none") for levy in (False, True)}
        self.assertEqual(combinations, expected)

    def test_flood_and_levy_flags_resolve_consistently(self):
        for scenario in SCENARIOS:
            config = load_experiment_config(
                f"popular_times_v2/scenarios/{scenario}"
            )
            study = config["popular_times_v2_study"]
            self.assertEqual("levy_walk_plugin" in config, study["levy"])
            self.assertEqual(
                "water_level_data_plugin" in config, study["flood"] != "none"
            )
            if study["levy"]:
                self.assertTrue(
                    config["send_population_back_plugin"][
                        "acting_enabled_only"
                    ]
                )
                self.assertTrue(
                    config["send_population_back_plugin"][
                        "destination_enabled_only"
                    ]
                )

    def test_derived_levy_routine_is_reproducible_and_home_filtered(self):
        root = Path(__file__).parents[1] / "data_input" / "enumeration_area"
        source = json.loads(
            (root / "Routine-POA-EnumArea.json").read_text(encoding="utf8")
        )
        derived = json.loads(
            (
                root / "Routine-POA-EnumArea-PopularTimes.json"
            ).read_text(encoding="utf8")
        )
        self.assertEqual(derived, build_routine(source))
        levy_actions = [
            item["action"]
            for item in derived["global_routine"]
            if item["action"]["type"] == "levy_walk"
        ]
        self.assertEqual(len(levy_actions), 9)
        self.assertTrue(
            all(action["values"]["node_type"] == ["home"] for action in levy_actions)
        )


class PopularTimesStage3LoggerTest(unittest.TestCase):
    def setUp(self):
        FixedRandom(0)
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.profiles = self.root / "profiles"
        self.profiles.mkdir()
        self._profile("marketplace.csv", [(0, 9, 1), (0, 12, 3)])
        self._profile("restaurant.csv", [(0, 12, 1)])
        self._profile("pharmacy.csv", [(0, 10, 1)])

    def tearDown(self):
        self.temp.cleanup()

    def _profile(self, filename, rows):
        with (self.profiles / filename).open(
            "w", encoding="utf8", newline=""
        ) as stream:
            writer = csv.writer(stream)
            writer.writerow(["ciclo", "hora", "quantidade"])
            writer.writerows(rows)

    def _simulation(self):
        characteristics = CharacteristicsFactory()
        characteristics.add_sampled_characteristic("group", ["resident"])
        factory = BlobFactory(characteristics)
        graph = EnvironmentGraph()
        graph.add_region(EnvRegionTemplate("Region", [0.0, 0.0]), factory)
        region = graph.get_region_by_name("Region")
        home = EnvNode("home", "home_0")
        home.set_long_lat_position(0.0, 0.0)
        graph.add_envnode("Region", home)
        home.add_blob(factory.generate_blob_rand(region.id, home.id, 100))
        destinations = []
        for node_type in ("marketplace", "restaurant", "pharmacy"):
            node = EnvNode(node_type, f"{node_type}_0")
            node.set_long_lat_position(0.00001, 0.0)
            graph.add_envnode("Region", node)
            destinations.append(node)
        graph.set_original_populations()

        simulation = LodusSimulation(graph)
        simulation.set_cycle_length(24)
        simulation.set_total_cycles(7)
        simulation.experiment_name = "stage3-unit"
        simulation.experiment_config = {
            "popular_times_v2_plugin": {"data_path": str(self.profiles)},
            "popular_times_v2_logger": {},
        }
        plugin = PopularTimesV2Plugin()
        simulation.load_plugin(plugin)
        logger = PopularTimesV2Logger()
        simulation.load_plugin(logger)
        logger.base_path = self.root
        logger.data_path = self.root / "data_frames"
        logger.setup_logger()
        return simulation, plugin, logger, destinations

    def test_incremental_raw_and_aggregate_outputs_pass_invariants(self):
        simulation, plugin, logger, destinations = self._simulation()
        template = PopulationTemplate()
        for step in range(7 * 24):
            hour = step % 24
            plugin.update_time_step(hour, step)
            logger.update_time_step(hour, step)
            for destination in destinations:
                plugin.popular_times_v2_action(
                    template,
                    {
                        "region": "Region",
                        "node_unique_name": destination.unique_name,
                    },
                    hour,
                    step,
                )
            logger.log_simulation_step()
            self.assertEqual(plugin.demand_records, [])
            self.assertEqual(plugin.visit_records, [])
        logger.stop_logger()

        validation = json.loads(
            (self.root / "data_frames/popular_times_validation.json").read_text(
                encoding="utf8"
            )
        )
        self.assertTrue(validation["passed"], validation)
        self.assertEqual(validation["initial_population"], 100)
        self.assertEqual(validation["final_population"], 100)
        self.assertTrue(
            (self.root / "data_frames/popular_times_demand.csv").is_file()
        )
        self.assertTrue(
            (self.root / "data_frames/popular_times_visits.csv").is_file()
        )
        self.assertTrue(
            (self.root / "data_frames/popular_times_step_type.csv").is_file()
        )
        self.assertTrue(
            (self.root / "data_frames/popular_times_od.csv").is_file()
        )


if __name__ == "__main__":
    unittest.main()
