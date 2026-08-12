import unittest
import tempfile
from pathlib import Path

from core.environment import EnvNode, EnvRegionTemplate, EnvironmentGraph
from core.population import BlobFactory, CharacteristicsFactory, PopulationTemplate
from core.simulator import LodusSimulation
from plugins.time_actions.levy_walk_plugin import LevyWalkPlugin
from plugins.time_actions.levy_walk_v2_plugin import LevyWalkV2Plugin
from plugins.loggers.levy_walk_v2_logger import LevyWalkV2Logger
from misc_scripts.run_popular_times_v2_stage6 import (
    RunSpec,
    completion_state,
    stage6_specs,
)
from util.data_parse import load_experiment_config
from util.random_instance import FixedRandom


class LevyWalkV2ConfigurationTest(unittest.TestCase):
    def test_matrix_has_ten_families_and_50_paired_runs(self):
        specs = stage6_specs()
        self.assertEqual(50, len(specs))
        self.assertEqual(50, len({spec.run_name for spec in specs}))
        for scenario in {spec.scenario for spec in specs}:
            expected = set(range(5))
            self.assertEqual(
                expected, {spec.seed for spec in specs if spec.scenario == scenario}
            )

    def test_five_13_region_families_resolve_without_legacy_levy(self):
        targets_by_flood = {
            "none": None,
            "destinations": {
                "marketplace", "restaurant", "pharmacy", "work", "school"
            },
            "homes": {"home"},
            "all": {
                "home", "marketplace", "restaurant", "pharmacy", "work", "school"
            },
            "all_pt_reroute": {
                "home", "marketplace", "restaurant", "pharmacy", "work", "school"
            },
        }
        scenarios = {
            "13_levy_v2_flood_none": None,
            "13_levy_v2_flood_destinations": {
                "marketplace", "restaurant", "pharmacy", "work", "school"
            },
            "13_levy_v2_flood_homes": {"home"},
            "13_levy_v2_flood_all": {
                "home", "marketplace", "restaurant", "pharmacy", "work", "school"
            },
            "13_levy_v2_flood_all_pt_reroute": {
                "home", "marketplace", "restaurant", "pharmacy", "work", "school"
            },
        }
        scenarios.update({
            f"94_levy_v2_flood_{flood}": targets
            for flood, targets in targets_by_flood.items()
        })
        for scenario, targets in scenarios.items():
            with self.subTest(scenario=scenario):
                config = load_experiment_config(
                    f"popular_times_v2/stage6/{scenario}"
                )
                self.assertEqual(56, config["simulation_parameters"]["total_cycles"])
                self.assertIn("levy_walk_v2_plugin", config)
                self.assertNotIn("levy_walk_plugin", config)
                self.assertNotIn("send_population_back_plugin", config)
                actual = config.get("water_level_data_plugin", {}).get(
                    "target_node_types"
                )
                self.assertEqual(targets, None if actual is None else set(actual))

    def test_profiles_and_rates_are_explicit(self):
        config = load_experiment_config("popular_times_v2/LevyV2_13")[
            "levy_walk_v2_plugin"
        ]
        self.assertEqual(50, config["packet_size"])
        self.assertAlmostEqual(
            1.0, config["groups"]["worker"]["cycle_attendance_rate"]
        )
        self.assertAlmostEqual(
            1.0, config["groups"]["student"]["cycle_attendance_rate"]
        )
        student = config["groups"]["student"]["hourly_weights"]
        self.assertAlmostEqual(1.0, sum(student.values()))
        self.assertEqual({"8", "13", "19"}, set(student))

    def test_completion_requires_both_validation_suites(self):
        spec = RunSpec("13_levy_v2_flood_none", 3)
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
                    "levy_walk_v2_plugin": {
                        "groups": {
                            "worker": {"cycle_attendance_rate": 1.0},
                            "student": {"cycle_attendance_rate": 1.0},
                        }
                    },
                    "popular_times_v2_stage6": {
                        "environment": "13", "levy_model": "v2"
                    },
                },
            }
            (data.parent / "run_metadata.json").write_text(
                __import__("json").dumps(metadata), encoding="utf8"
            )
            (data / "popular_times_validation.json").write_text(
                '{"passed": true}', encoding="utf8"
            )
            (data / "levy_v2_validation.json").write_text(
                '{"passed": false}', encoding="utf8"
            )
            self.assertEqual("invalid", completion_state(spec, output)[0])
            (data / "levy_v2_validation.json").write_text(
                '{"passed": true}', encoding="utf8"
            )
            self.assertEqual("complete", completion_state(spec, output)[0])


class LevyWalkV2BehaviorTest(unittest.TestCase):
    def setUp(self):
        FixedRandom(0)

    def _simulation(self, worker=123, student=37, destination_policy="suppress"):
        characteristics = CharacteristicsFactory()
        characteristics.add_sampled_characteristic(
            "occupation", ["worker", "student", "other"]
        )
        factory = BlobFactory(characteristics)
        graph = EnvironmentGraph()
        graph.add_region(EnvRegionTemplate("A", [0.0, 0.0]), factory)
        graph.add_region(EnvRegionTemplate("B", [0.02, 0.0]), factory)
        home = graph.add_envnode("A", EnvNode("home", "home_a"))
        home.set_long_lat_position(0.0, 0.0)
        other_home = graph.add_envnode("B", EnvNode("home", "home_b"))
        other_home.set_long_lat_position(0.02, 0.0)
        work = graph.add_envnode("A", EnvNode("work", "work_a"))
        work.set_long_lat_position(0.005, 0.0)
        alternative = graph.add_envnode("B", EnvNode("work", "work_b"))
        alternative.set_long_lat_position(0.006, 0.0)
        school = graph.add_envnode("A", EnvNode("school", "school_a"))
        school.set_long_lat_position(0.004, 0.0)
        if worker:
            home.add_blob(
                factory.generate_blob_with_profile(
                    0, home.id, worker,
                    {"occupation": {"worker": worker, "student": 0, "other": 0}},
                )
            )
        if student:
            home.add_blob(
                factory.generate_blob_with_profile(
                    1, home.id, student,
                    {"occupation": {"worker": 0, "student": student, "other": 0}},
                )
            )
        other_home.add_blob(
            factory.generate_blob_with_profile(
                2, other_home.id, 10,
                {"occupation": {"worker": 0, "student": 0, "other": 10}},
            )
        )
        graph.set_original_populations()
        simulation = LodusSimulation(graph)
        simulation.set_total_cycles(2)
        simulation.experiment_config = {
            "levy_walk_v2_plugin": {
                "packet_size": 50,
                "disabled_destination_policy": destination_policy,
                "distance_type": 3,
                "groups": {
                    "worker": {
                        "cycle_attendance_rate": 1.0,
                        "hourly_weights": {"0": 1.0},
                    },
                    "student": {
                        "cycle_attendance_rate": 1.0,
                        "hourly_weights": {"0": 1.0},
                    },
                },
            }
        }
        plugin = LevyWalkV2Plugin()
        simulation.load_plugin(plugin)
        return simulation, plugin, home, other_home, work, alternative, school

    def test_exact_allocation_partial_packets_and_group_separation(self):
        _, plugin, home, _, work, _, school = self._simulation()
        plugin._sample_requested_destination = lambda _, kind: (
            work if kind == "work" else school
        )
        plugin.levy_walk_v2_action(PopulationTemplate(), {"group": "worker", "node_id": home.id}, 0, 0)
        plugin.levy_walk_v2_action(PopulationTemplate(), {"group": "student", "node_id": home.id}, 0, 0)
        worker_packets = [r for r in plugin.demand_records if r["group"] == "worker"]
        student_packets = [r for r in plugin.demand_records if r["group"] == "student"]
        self.assertEqual([50, 50, 23], [r["requested"] for r in worker_packets])
        self.assertEqual([37], [r["requested"] for r in student_packets])
        self.assertEqual(123, work.get_population_size())
        self.assertEqual(37, school.get_population_size())
        self.assertEqual(123, plugin.get_cycle_target("worker"))
        self.assertEqual(37, plugin.get_cycle_target("student"))
        self.assertAlmostEqual(
            1.0, sum(plugin.groups["worker"]["hourly_weights"].values())
        )

    def test_each_person_attends_at_most_once_per_cycle_and_returns_on_time(self):
        _, plugin, home, _, work, _, _ = self._simulation(worker=49, student=0)
        plugin._sample_requested_destination = lambda *_: work
        values = {"group": "worker", "node_id": home.id}
        plugin.levy_walk_v2_action(PopulationTemplate(), values, 0, 0)
        plugin.levy_walk_v2_action(PopulationTemplate(), values, 0, 0)
        self.assertEqual(49, sum(r["fulfilled"] for r in plugin.demand_records))
        for step in range(1, 9):
            plugin.update_time_step(step, step)
        self.assertEqual(49, home.get_population_size(PopulationTemplate(sampled_characteristics={"occupation": ["worker"]})))
        returns = [r for r in plugin.movement_records if r["event"] == "return"]
        self.assertEqual(49, sum(r["quantity"] for r in returns))
        self.assertTrue(all(r["simulation_step"] == 8 for r in returns))

    def test_disabled_origin_suppresses_latent_demand(self):
        _, plugin, home, _, work, _, _ = self._simulation(worker=20, student=0)
        plugin._sample_requested_destination = lambda *_: work
        home.disable("flood")
        plugin.levy_walk_v2_action(PopulationTemplate(), {"group": "worker", "node_id": home.id}, 0, 0)
        self.assertEqual("origin_disabled", plugin.demand_records[0]["reason"])
        self.assertEqual(20, plugin.demand_records[0]["unmet"])
        self.assertEqual(0, work.get_population_size())

    def test_destination_suppression_and_cross_region_nearest_rerouting(self):
        _, plugin, home, _, work, alternative, _ = self._simulation(
            worker=20, student=0, destination_policy="nearest_enabled_same_type"
        )
        plugin._sample_requested_destination = lambda *_: work
        work.disable("flood")
        plugin.levy_walk_v2_action(PopulationTemplate(), {"group": "worker", "node_id": home.id}, 0, 0)
        record = plugin.demand_records[0]
        self.assertTrue(record["destination_rerouted"])
        self.assertEqual(work.get_complete_name(), record["requested_destination"])
        self.assertEqual(alternative.get_complete_name(), record["receiving_destination"])
        self.assertEqual(20, alternative.get_population_size())

    def test_temporary_home_and_repatriation_preserve_original_home(self):
        _, plugin, home, other_home, work, _, _ = self._simulation(worker=20, student=0)
        plugin._sample_requested_destination = lambda *_: work
        plugin.levy_walk_v2_action(PopulationTemplate(), {"group": "worker", "node_id": home.id}, 0, 0)
        home.disable("flood")
        plugin.update_time_step(8, 8)
        self.assertEqual(20, other_home.get_population_size(PopulationTemplate(sampled_characteristics={"occupation": ["worker"]})))
        home.enable("flood")
        plugin.update_time_step(9, 9)
        self.assertEqual(20, home.get_population_size(PopulationTemplate(sampled_characteristics={"occupation": ["worker"]})))
        events = [record["event"] for record in plugin.movement_records]
        self.assertIn("temporary_return", events)
        self.assertIn("repatriation", events)

    def test_imminent_flood_and_no_alternative_are_auditable(self):
        simulation, plugin, home, _, work, alternative, _ = self._simulation(
            worker=20, student=0, destination_policy="nearest_enabled_same_type"
        )
        work.attributes["water_level"] = 1.0
        alternative.attributes["water_level"] = 1.0
        simulation.experiment_config["water_level_data_plugin"] = {
            "target_node_types": ["work"]
        }
        simulation.env_graph.data_action_map["water_level_for_step"] = (
            lambda cycle_step, simulation_step: 2.0 if simulation_step >= 4 else 0.0
        )
        plugin._sample_requested_destination = lambda *_: work
        plugin.levy_walk_v2_action(PopulationTemplate(), {"group": "worker", "node_id": home.id}, 0, 0)
        self.assertEqual("no_enabled_alternative", plugin.demand_records[0]["reason"])
        self.assertEqual(20, plugin.demand_records[0]["unmet"])

    def test_blocked_return_stays_put_and_retries_after_reenable(self):
        _, plugin, home, _, work, _, _ = self._simulation(worker=20, student=0)
        plugin._sample_requested_destination = lambda *_: work
        plugin.levy_walk_v2_action(
            PopulationTemplate(), {"group": "worker", "node_id": home.id}, 0, 0
        )
        work.disable("flood")
        plugin.update_time_step(8, 8)
        self.assertEqual(20, work.get_population_size())
        self.assertEqual("return_blocked", plugin.movement_records[-1]["event"])
        work.enable("flood")
        plugin.update_time_step(9, 9)
        self.assertEqual(20, home.get_population_size())
        self.assertEqual("return", plugin.movement_records[-1]["event"])

    def test_enabled_destination_ties_use_complete_node_name(self):
        simulation, plugin, home, _, work, alternative, _ = self._simulation(
            worker=20, student=0, destination_policy="nearest_enabled_same_type"
        )
        region = simulation.env_graph.get_region_by_name("A")
        tie = simulation.env_graph.add_envnode("A", EnvNode("work", "aaa_tie"))
        tie.set_long_lat_position(*alternative.long_lat)
        work.disable("flood")
        plugin._sample_requested_destination = lambda *_: work
        plugin.levy_walk_v2_action(
            PopulationTemplate(), {"group": "worker", "node_id": home.id}, 0, 0
        )
        expected = min(
            [alternative, tie], key=lambda node: node.get_complete_name()
        )
        self.assertEqual(
            expected.get_complete_name(), plugin.demand_records[0]["receiving_destination"]
        )

    def test_logger_writes_a_passing_cycle_lifecycle_audit(self):
        simulation, plugin, home, other_home, work, _, school = self._simulation(
            worker=49, student=0
        )
        simulation.set_total_cycles(1)
        simulation.experiment_name = "stage6-unit"
        simulation.experiment_config["levy_walk_v2_logger"] = {}
        plugin._sample_requested_destination = lambda _, kind: (
            work if kind == "work" else school
        )
        logger = LevyWalkV2Logger()
        simulation.load_plugin(logger)
        with tempfile.TemporaryDirectory() as temporary:
            logger.base_path = Path(temporary)
            logger.data_path = Path(temporary) / "data_frames"
            logger.setup_logger()
            for step in range(24):
                logger.update_time_step(step, step)
                plugin.update_time_step(step, step)
                if step == 0:
                    for group in plugin.groups:
                        for node in (home, other_home):
                            plugin.levy_walk_v2_action(
                                PopulationTemplate(),
                                {"group": group, "node_id": node.id},
                                step,
                                step,
                            )
                logger.log_simulation_step()
            logger.stop_logger()
            validation = __import__("json").loads(
                (logger.data_path / "levy_v2_validation.json").read_text(
                    encoding="utf8"
                )
            )
            self.assertTrue(validation["passed"], validation)
            self.assertTrue(validation["checks"]["no_duplicate_attendance"])

    def test_legacy_packet_flooring_is_unchanged(self):
        simulation, _, home, _, _, _, _ = self._simulation(worker=49, student=0)
        simulation.experiment_config["levy_walk_plugin"] = {
            "population_group_size": 50,
            "movement_probability": 1.0,
            "distance_type": 3,
            "use_buckets": True,
            "distance_bucket_size": 500,
        }
        legacy = LevyWalkPlugin()
        simulation.load_plugin(legacy)
        actions = legacy.levy_walk(
            PopulationTemplate(
                sampled_characteristics={"occupation": ["worker"]}
            ),
            {
                "region": "A",
                "node_id": home.id,
                "acting_node_types": ["home"],
                "target_node_types": ["work"],
            },
            0,
            0,
        )
        self.assertEqual([], actions)


if __name__ == "__main__":
    unittest.main()
