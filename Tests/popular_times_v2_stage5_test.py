import csv
import json
import tempfile
import unittest
from pathlib import Path

from core.environment import EnvNode, EnvRegionTemplate, EnvironmentGraph
from core.population import BlobFactory, CharacteristicsFactory, PopulationTemplate
from core.simulator import LodusSimulation
from misc_scripts.run_popular_times_v2_stage5 import (
    RunSpec,
    completion_state,
    stage5_specs,
)
from plugins.loggers.popular_times_v2_logger import PopularTimesV2Logger
from plugins.time_actions.popular_times_v2_plugin import PopularTimesV2Plugin
from util.data_parse import load_experiment_config
from util.random_instance import FixedRandom


class PopularTimesStage5ConfigurationTest(unittest.TestCase):
    def test_matrix_has_one_deterministic_and_30_matched_levy_runs(self):
        specs = stage5_specs()
        self.assertEqual(31, len(specs))
        self.assertEqual(31, len({spec.run_name for spec in specs}))
        self.assertEqual([0], [spec.seed for spec in specs if not spec.levy])
        self.assertEqual(
            set(range(30)), {spec.seed for spec in specs if spec.levy}
        )

    def test_stage5_configs_enable_rerouting_and_resolve_to_56_cycles(self):
        for scenario in {
            "13_levy_off_flood_both_reroute",
            "13_levy_on_flood_both_reroute",
        }:
            with self.subTest(scenario=scenario):
                config = load_experiment_config(
                    f"popular_times_v2/stage5/{scenario}"
                )
                self.assertEqual(56, config["simulation_parameters"]["total_cycles"])
                self.assertEqual(24, config["simulation_parameters"]["cycle_length"])
                self.assertTrue(
                    config["popular_times_v2_plugin"][
                        "reroute_disabled_destinations"
                    ]
                )
                self.assertEqual(
                    "reroute", config["popular_times_v2_stage5"]["adaptation"]
                )

    def test_completion_rejects_runs_without_enabled_rerouting(self):
        spec = RunSpec("13_levy_on_flood_both_reroute", 3)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            data = output / spec.run_name / "data_frames"
            data.mkdir(parents=True)
            metadata = {
                "status": "complete",
                "experiment": spec.experiment,
                "seed": spec.seed,
                "simulation_parameters": {"total_cycles": 56},
                "resolved_config": {
                    "popular_times_v2_plugin": {
                        "reroute_disabled_destinations": False
                    }
                },
            }
            (data.parent / "run_metadata.json").write_text(
                json.dumps(metadata), encoding="utf8"
            )
            (data / "popular_times_validation.json").write_text(
                json.dumps({"passed": True}), encoding="utf8"
            )
            self.assertEqual("pending", completion_state(spec, output)[0])
            metadata["resolved_config"]["popular_times_v2_plugin"][
                "reroute_disabled_destinations"
            ] = True
            (data.parent / "run_metadata.json").write_text(
                json.dumps(metadata), encoding="utf8"
            )
            self.assertEqual("complete", completion_state(spec, output)[0])


class PopularTimesStage5LoggerTest(unittest.TestCase):
    def setUp(self):
        FixedRandom(0)
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.profiles = self.root / "profiles"
        self.profiles.mkdir()
        for node_type, hour in (
            ("marketplace", 12),
            ("restaurant", 13),
            ("pharmacy", 10),
        ):
            with (self.profiles / f"{node_type}.csv").open(
                "w", encoding="utf8", newline=""
            ) as stream:
                writer = csv.writer(stream)
                writer.writerow(["ciclo", "hora", "quantidade"])
                writer.writerow([0, hour, 1])

    def tearDown(self):
        self.temp.cleanup()

    def _simulation(self):
        characteristics = CharacteristicsFactory()
        characteristics.add_sampled_characteristic("group", ["resident"])
        factory = BlobFactory(characteristics)
        graph = EnvironmentGraph()
        graph.add_region(EnvRegionTemplate("Region", [0.0, 0.0]), factory)
        region = graph.get_region_by_name("Region")
        home = graph.add_envnode("Region", EnvNode("home", "home_0"))
        home.set_long_lat_position(0.0, 0.0)
        home.add_blob(factory.generate_blob_rand(region.id, home.id, 100))
        requested = []
        for index, node_type in enumerate(
            ("marketplace", "restaurant", "pharmacy"), start=1
        ):
            original = graph.add_envnode(
                "Region", EnvNode(node_type, f"{node_type}_0")
            )
            original.set_long_lat_position(index * 0.001, 0.0)
            original.disable("flood")
            requested.append(original)
            receiving = graph.add_envnode(
                "Region", EnvNode(node_type, f"{node_type}_alternative")
            )
            receiving.set_long_lat_position(index * 0.0015, 0.0)
        graph.set_original_populations()

        simulation = LodusSimulation(graph)
        simulation.set_cycle_length(24)
        simulation.set_total_cycles(7)
        simulation.experiment_name = "stage5-unit"
        simulation.experiment_config = {
            "popular_times_v2_plugin": {
                "data_path": str(self.profiles),
                "reroute_disabled_destinations": True,
            },
            "popular_times_v2_logger": {},
        }
        plugin = PopularTimesV2Plugin()
        simulation.load_plugin(plugin)
        logger = PopularTimesV2Logger()
        simulation.load_plugin(logger)
        logger.base_path = self.root
        logger.data_path = self.root / "data_frames"
        logger.setup_logger()
        return simulation, plugin, logger, requested

    def test_rerouting_outputs_and_validation_are_auditable(self):
        _, plugin, logger, requested = self._simulation()
        template = PopulationTemplate()
        for step in range(7 * 24):
            hour = step % 24
            plugin.update_time_step(hour, step)
            logger.update_time_step(hour, step)
            for destination in requested:
                plugin.popular_times_v2_action(
                    template,
                    {"region": "Region", "node": destination.unique_name},
                    hour,
                    step,
                )
            logger.log_simulation_step()
        logger.stop_logger()

        data = self.root / "data_frames"
        validation = json.loads(
            (data / "popular_times_validation.json").read_text(encoding="utf8")
        )
        self.assertTrue(validation["passed"], validation)
        self.assertTrue(validation["checks"]["rerouted_destinations_valid"])
        with (data / "popular_times_rerouting.csv").open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            rows = list(csv.DictReader(stream, delimiter=";"))
        self.assertGreater(len(rows), 0)
        self.assertTrue(
            all(
                row["requested_destination"] != row["receiving_destination"]
                and float(row["fulfilled"]) > 0
                and float(row["reroute_distance"]) > 0
                and float(row["receiving_load"]) > 0
                for row in rows
            )
        )
        with (data / "popular_times_rerouting_summary.csv").open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            summaries = list(csv.DictReader(stream, delimiter=";"))
        self.assertEqual(3, len(summaries))
        self.assertTrue(all(float(row["fulfilled"]) > 0 for row in summaries))


if __name__ == "__main__":
    unittest.main()
