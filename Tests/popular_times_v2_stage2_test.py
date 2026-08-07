import hashlib
import json
import unittest
from pathlib import Path

from core.population import PopulationTemplate
from misc_scripts.generate_popular_times_v2_inputs import (
    EXPECTED_UNMATCHED_HOMES,
    POI_TYPES,
    build_outputs,
)
from plugins.routines.off_cycle_routine_plugin import OffCycleRoutinePlugin
from plugins.data.water_level_data_plugin import WaterLevelDataPlugin
from plugins.time_actions.popular_times_v2_plugin import PopularTimesV2Plugin
from util.data_parse import (
    generate_lodus_simulation,
    load_experiment_config,
    parse_global_routines,
)
from util.random_instance import FixedRandom


ROOT = Path(__file__).parents[1]
DATA_ROOT = ROOT / "data_input"


class PopularTimesStage2DataTest(unittest.TestCase):
    def _canonical_region_names(self):
        environment = json.loads(
            (DATA_ROOT / "Environment-PortoAlegre94RegionsDefault.json").read_text(
                encoding="utf8"
            )
        )
        return {region["name"] for region in environment["regions"]}

    def test_generator_is_reproducible_and_matches_audit(self):
        first = build_outputs(DATA_ROOT)
        second = build_outputs(DATA_ROOT)
        first_hash = hashlib.sha256(
            json.dumps(first, ensure_ascii=False, sort_keys=True).encode("utf8")
        ).hexdigest()
        second_hash = hashlib.sha256(
            json.dumps(second, ensure_ascii=False, sort_keys=True).encode("utf8")
        ).hexdigest()
        self.assertEqual(first_hash, second_hash)

        environment, population, audit = first
        validation = audit["validation"]
        self.assertEqual(validation["region_count"], 94)
        self.assertEqual(validation["node_count"], 16266)
        self.assertEqual(validation["population_home_count"], 2711)
        self.assertEqual(validation["total_population"], 1331414)
        self.assertEqual(validation["water_threshold_count"], 16266)
        self.assertTrue(validation["pairing_valid"])
        for node_type in ("home", "work", "school", *POI_TYPES):
            self.assertEqual(validation["node_type_counts"][node_type], 2711)
        self.assertEqual(audit["excluded_population_total"], 1431)
        self.assertEqual(audit["source_population_total"], 1332845)
        self.assertAlmostEqual(audit["excluded_population_percent"], 0.107364)
        self.assertEqual(
            {item["home"] for item in audit["excluded_population"]},
            EXPECTED_UNMATCHED_HOMES,
        )
        self.assertEqual(len(population["initial_population"]), 2711)
        self.assertEqual(len(environment["regions"]), 94)
        self.assertTrue(
            all(
                "water_level" in node.get("attributes", {})
                for region in environment["regions"]
                for node in region["points_of_interest"]
            )
        )
        self.assertEqual(
            audit["water_threshold_source"],
            "Environment-POA-EnumArea-WaterLevels_Filled3.csv",
        )
        self.assertEqual(
            {region["name"] for region in environment["regions"]},
            self._canonical_region_names(),
        )

    def test_source_environments_remain_unmodified(self):
        source_94 = json.loads(
            (DATA_ROOT / "enumeration_area/Environment-POA-EnumArea.json").read_text(
                encoding="utf8"
            )
        )
        types_94 = {
            node["poi_type"]
            for region in source_94["regions"]
            for node in region["points_of_interest"]
        }
        self.assertEqual(types_94, {"home", "work", "school"})

        source_13 = json.loads(
            (DATA_ROOT / "enumeration_area/Environment-13-EnumArea.json").read_text(
                encoding="utf8"
            )
        )
        self.assertEqual(len(source_13["regions"]), 13)
        self.assertEqual(
            sum(len(region["points_of_interest"]) for region in source_13["regions"]),
            3480,
        )
        self.assertEqual(
            {region["name"] for region in source_94["regions"]},
            self._canonical_region_names(),
        )

    def test_census_overlays_use_canonical_region_names(self):
        canonical = self._canonical_region_names()
        overlay_paths = (
            "dialysis_clinics/Environment-Clinics.json",
            "dialysis_clinics/Environment-ETAs.json",
            "inpatient_care/Environment-Hospitals-POA.json",
        )
        for relative_path in overlay_paths:
            overlay = json.loads(
                (DATA_ROOT / relative_path).read_text(encoding="utf8")
            )
            names = {region["name"] for region in overlay["regions"]}
            self.assertLessEqual(names, canonical, relative_path)

    def test_hourly_end_of_step_routine_covers_the_full_day(self):
        routine_data = json.loads(
            (
                DATA_ROOT
                / "popular_times/Routine-PopularTimesV2.json"
            ).read_text(encoding="utf8")
        )
        actions = parse_global_routines(routine_data)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].action_type, "popular_times_v2")
        self.assertEqual(actions[0].cycle_step_definition, list(range(24)))
        self.assertEqual(
            actions[0].values["node_type"],
            ["marketplace", "restaurant", "pharmacy"],
        )


class PopularTimesStage2ConfigurationTest(unittest.TestCase):
    def test_base_and_levy_families_resolve(self):
        base_13 = load_experiment_config("popular_times_v2/Base13")
        levy_13 = load_experiment_config("popular_times_v2/Levy13")
        base_94 = load_experiment_config("popular_times_v2/Base94")
        levy_94 = load_experiment_config("popular_times_v2/Levy94")

        for config in (base_13, levy_13, base_94, levy_94):
            self.assertEqual(config["simulation_parameters"]["total_cycles"], 56)
            self.assertEqual(config["simulation_parameters"]["cycle_length"], 24)
            self.assertIn("popular_times_v2_plugin", config)
            self.assertEqual(
                config["off_cycle_routine_plugin"]["end_of_step_routine_files"],
                ["popular_times/Routine-PopularTimesV2.json"],
            )

        self.assertNotIn("levy_walk_plugin", base_13)
        self.assertNotIn("levy_walk_plugin", base_94)
        for config in (levy_13, levy_94):
            self.assertTrue(config["levy_walk_plugin"]["acting_enabled_only"])
            self.assertTrue(config["levy_walk_plugin"]["target_enabled_only"])
            self.assertIn("routine_file", config["envgraph_inputs_files"])

        self.assertNotIn("water_level_data_plugin", base_94)
        self.assertNotIn("water_level_data_plugin", levy_94)

    def test_flood_target_configs_are_exact(self):
        pois = load_experiment_config("popular_times_v2/FloodPOIs13")
        homes = load_experiment_config("popular_times_v2/FloodHomes13")
        both = load_experiment_config("popular_times_v2/FloodBoth13")
        self.assertEqual(
            set(pois["water_level_data_plugin"]["target_node_types"]),
            {"marketplace", "restaurant", "pharmacy"},
        )
        self.assertEqual(
            homes["water_level_data_plugin"]["target_node_types"], ["home"]
        )
        self.assertEqual(
            set(both["water_level_data_plugin"]["target_node_types"]),
            {"home", "marketplace", "restaurant", "pharmacy"},
        )

    def test_derived_94_environment_loads_with_v2_and_end_routine(self):
        FixedRandom(0)
        simulation = generate_lodus_simulation("popular_times_v2/Base94")
        popular_times = PopularTimesV2Plugin()
        end_routine = OffCycleRoutinePlugin()
        simulation.load_plugin(popular_times)
        simulation.load_plugin(end_routine)

        self.assertEqual(len(simulation.env_graph.region_list), 94)
        self.assertEqual(len(simulation.env_graph.node_list), 16266)
        self.assertEqual(len(end_routine.end_of_step_global_actions), 1)
        marketplace = next(
            node
            for node in simulation.env_graph.node_list
            if node.node_type == "marketplace"
        )
        paired_home = simulation.env_graph.get_node_by_complete_name(
            popular_times.paired_home_name(
                marketplace.containing_region_name, marketplace.unique_name
            )
        )
        schedule = popular_times._weekly_schedule(
            paired_home, "marketplace", PopulationTemplate()
        )
        self.assertEqual(
            sum(schedule.values()),
            paired_home.original_node_population.get_population_size(),
        )

    def test_13_region_flood_config_covers_eight_complete_weeks(self):
        FixedRandom(0)
        simulation = generate_lodus_simulation("popular_times_v2/FloodBoth13")
        water = WaterLevelDataPlugin()
        simulation.load_plugin(water)
        self.assertEqual(simulation.env_graph.get_population_size(), 159886)
        self.assertEqual(
            simulation.env_graph.get_region_by_name("Menino Deus").get_population_size(),
            27961,
        )
        self.assertEqual(simulation.time_status.total_cycles, 56)
        self.assertEqual(simulation.time_status.cycle_length, 24)
        self.assertEqual(
            water.target_node_types,
            {"home", "marketplace", "restaurant", "pharmacy"},
        )
        for cycle in range(56):
            for cycle_step in range(24):
                self.assertIsNotNone(
                    water.get_water_level_for_step(cycle_step, cycle * 24 + cycle_step)
                )


if __name__ == "__main__":
    unittest.main()
