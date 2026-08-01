import csv
import tempfile
import unittest
from pathlib import Path

from core.environment import EnvNode, EnvRegionTemplate, EnvironmentGraph
from core.population import BlobFactory, CharacteristicsFactory, PopulationTemplate
from core.routine import Action
from core.simulator import LodusSimulation
from plugins.time_actions.popular_times_v2_plugin import PopularTimesV2Plugin
from plugins.time_actions.levy_walk_plugin import LevyWalkPlugin
from util.random_instance import FixedRandom


class PopularTimesV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        FixedRandom()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = Path(self.temp_dir.name)
        self._write_profile("marketplace.csv", [(0, 9, 1), (0, 12, 3)])
        self._write_profile("restaurant.csv", [(0, 12, 1)])
        self._write_profile("pharmacy.csv", [(0, 10, 1)])

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_profile(self, name, rows):
        with (self.data_path / name).open("w", encoding="utf8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ciclo", "hora", "quantidade"])
            writer.writerows(rows)

    def _simulation(self, homes=(100,), config=None):
        characteristics = CharacteristicsFactory()
        characteristics.add_sampled_characteristic("group", ["resident"])
        factory = BlobFactory(characteristics)
        graph = EnvironmentGraph()
        graph.add_region(EnvRegionTemplate("Region", [0.0, 0.0]), factory)
        region = graph.get_region_by_name("Region")

        home_nodes = []
        for index, population in enumerate(homes):
            home = EnvNode("home", f"home_{index}")
            home.set_long_lat_position(float(index), 0.0)
            graph.add_envnode("Region", home)
            home.add_blob(factory.generate_blob_rand(region.id, home.id, population))
            home_nodes.append(home)

        marketplace = EnvNode("marketplace", "marketplace_0")
        marketplace.set_long_lat_position(0.00001, 0.0)
        graph.add_envnode("Region", marketplace)
        pharmacy = EnvNode("pharmacy", "pharmacy_0")
        pharmacy.set_long_lat_position(0.00001, 0.0)
        graph.add_envnode("Region", pharmacy)
        restaurant = EnvNode("restaurant", "restaurant_0")
        restaurant.set_long_lat_position(0.00001, 0.0)
        graph.add_envnode("Region", restaurant)
        graph.set_original_populations()

        simulation = LodusSimulation(graph)
        simulation.set_cycle_length(24)
        simulation.experiment_config = {
            "popular_times_v2_plugin": {
                "data_path": str(self.data_path),
                **(config or {}),
            }
        }
        plugin = PopularTimesV2Plugin()
        simulation.load_plugin(plugin)
        return simulation, plugin, home_nodes, marketplace, pharmacy

    def test_profile_normalization_closed_hours_and_midday_peak(self):
        _, plugin, homes, marketplace, _ = self._simulation()
        template = PopulationTemplate()

        morning = plugin.get_hourly_demand(marketplace, template, 9, 0)
        midday = plugin.get_hourly_demand(marketplace, template, 12, 0)
        closed = plugin.get_hourly_demand(marketplace, template, 8, 0)
        next_week = plugin.get_hourly_demand(marketplace, template, 12, 7 * 24)

        self.assertEqual(morning, 25)
        self.assertEqual(midday, 75)
        self.assertEqual(morning + midday, homes[0].get_population_size())
        self.assertEqual(closed, 0)
        self.assertEqual(next_week, midday)

    def test_node_type_weekly_rate_is_independent_from_profile(self):
        _, plugin, _, _, pharmacy = self._simulation()
        demand = plugin.get_hourly_demand(
            pharmacy, PopulationTemplate(), cycle_step=10, simulation_step=0
        )
        self.assertEqual(demand, 25)

    def test_visit_occupies_poi_for_one_step_then_returns_to_prior_home(self):
        _, plugin, homes, marketplace, _ = self._simulation()
        template = PopulationTemplate()
        initial_total = plugin.env_graph.get_population_size()

        plugin.popular_times_v2_action(
            template,
            {"region": "Region", "node_unique_name": "marketplace_0"},
            cycle_step=12,
            simulation_step=0,
        )
        self.assertEqual(marketplace.get_population_size(), 75)
        self.assertEqual(homes[0].get_population_size(), 25)
        self.assertEqual(plugin.env_graph.get_population_size(), initial_total)

        plugin.update_time_step(cycle_step=13, simulation_step=1)
        self.assertEqual(marketplace.get_population_size(), 0)
        self.assertEqual(homes[0].get_population_size(), 100)
        self.assertEqual(plugin.env_graph.get_population_size(), initial_total)
        self.assertTrue(plugin.visit_records[-1]["event"] == "release")

    def test_distance_times_availability_prefers_nearby_enabled_homes(self):
        _, plugin, homes, marketplace, _ = self._simulation(homes=(30, 100))
        allocations = plugin._source_allocations(
            marketplace, 75, PopulationTemplate()
        )
        by_name = {node.unique_name: quantity for node, quantity in allocations}
        self.assertEqual(by_name["home_0"], 30)
        self.assertEqual(sum(by_name.values()), 75)

        homes[0].disable("flood")
        allocations = plugin._source_allocations(
            marketplace, 75, PopulationTemplate()
        )
        self.assertEqual([(node.unique_name, quantity) for node, quantity in allocations], [("home_1", 75)])

    def test_disabled_destination_suppresses_request(self):
        _, plugin, homes, marketplace, _ = self._simulation()
        marketplace.disable("flood")
        plugin.popular_times_v2_action(
            PopulationTemplate(),
            {"region": "Region", "node": "marketplace_0"},
            cycle_step=12,
            simulation_step=0,
        )
        self.assertEqual(marketplace.get_population_size(), 0)
        self.assertEqual(homes[0].get_population_size(), 100)
        self.assertEqual(plugin.demand_records[-1]["reason"], "disabled_destination")
        self.assertEqual(plugin.demand_records[-1]["unmet"], 75)

    def test_visit_is_suppressed_if_poi_will_flood_before_expiry(self):
        _, plugin, homes, marketplace, _ = self._simulation(
            config={"suppress_if_flooded_before_expiry": True}
        )
        marketplace.attributes["water_level"] = 1.0
        plugin.env_graph.data_action_map["water_level_for_step"] = (
            lambda cycle_step, simulation_step: 2.0
        )
        plugin.popular_times_v2_action(
            PopulationTemplate(),
            {"region": "Region", "node": "marketplace_0"},
            cycle_step=12,
            simulation_step=0,
        )
        self.assertEqual(marketplace.get_population_size(), 0)
        self.assertEqual(homes[0].get_population_size(), 100)
        self.assertEqual(
            plugin.demand_records[-1]["reason"], "disabled_destination"
        )
        self.assertTrue(plugin.demand_records[-1]["anticipated_disable"])

    def test_multiplier_csv_can_replace_initial_population_basis(self):
        with (self.data_path / "multipliers.csv").open(
            "w", encoding="utf8", newline=""
        ) as f:
            writer = csv.writer(f)
            writer.writerows(
                [["local", "multiplicador"], ["Region//home_0", 0.5]]
            )
        _, plugin, _, marketplace, _ = self._simulation(
            config={
                "demand_basis": "multiplier_csv",
                "multiplier_file": "multipliers.csv",
                "multiplier_population_scale": 700,
            }
        )
        schedule = plugin._weekly_schedule(
            plugin.env_graph.get_node_by_complete_name("Region//home_0"),
            "marketplace",
            PopulationTemplate(),
        )
        self.assertEqual(sum(schedule.values()), 350)

    def test_paired_home_return_mode_ignores_the_source_home(self):
        _, plugin, homes, marketplace, _ = self._simulation(
            homes=(100, 100), config={"return_mode": "paired_home"}
        )
        moved = plugin._start_visit(
            homes[1],
            marketplace,
            homes[0],
            10,
            PopulationTemplate(),
            simulation_step=0,
        )
        self.assertEqual(moved, 10)
        plugin.update_time_step(cycle_step=1, simulation_step=1)
        self.assertEqual(homes[0].get_population_size(), 110)
        self.assertEqual(homes[1].get_population_size(), 90)

    def test_disabled_return_home_reroutes_to_nearest_enabled_home(self):
        _, plugin, homes, marketplace, _ = self._simulation(homes=(100, 100))
        plugin._start_visit(
            homes[0],
            marketplace,
            homes[0],
            10,
            PopulationTemplate(),
            simulation_step=0,
        )
        homes[0].disable("flood")
        plugin.update_time_step(cycle_step=1, simulation_step=1)
        self.assertEqual(marketplace.get_population_size(), 0)
        self.assertEqual(homes[0].get_population_size(), 90)
        self.assertEqual(homes[1].get_population_size(), 110)
        self.assertTrue(plugin.visit_records[-1]["rerouted"])


class LevyEnabledStateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        FixedRandom()

    def _plugin(self):
        characteristics = CharacteristicsFactory()
        characteristics.add_sampled_characteristic("group", ["resident"])
        factory = BlobFactory(characteristics)
        graph = EnvironmentGraph()
        graph.add_region(EnvRegionTemplate("Region", [0.0, 0.0]), factory)
        region = graph.get_region_by_name("Region")
        home = graph.add_envnode("Region", EnvNode("home", "home_0"))
        work = graph.add_envnode("Region", EnvNode("work", "work_0"))
        home.set_long_lat_position(0.0, 0.0)
        work.set_long_lat_position(0.01, 0.0)
        home.add_blob(factory.generate_blob_rand(region.id, home.id, 100))
        graph.set_original_populations()
        simulation = LodusSimulation(graph)
        simulation.experiment_config = {
            "levy_walk_plugin": {
                "acting_enabled_only": True,
                "target_enabled_only": True,
                "use_buckets": True,
                "distance_type": 3,
                "distance_bucket_size": 500,
            }
        }
        plugin = LevyWalkPlugin()
        simulation.load_plugin(plugin)
        return plugin, home, work

    def test_disabled_acting_node_produces_no_levy_actions(self):
        plugin, home, _ = self._plugin()
        home.disable("flood")
        actions = plugin.levy_walk(
            PopulationTemplate(),
            {
                "region": "Region",
                "node_id": home.id,
                "acting_node_types": ["home"],
                "target_node_types": ["work"],
            },
            0,
            0,
        )
        self.assertEqual(actions, [])

    def test_disabled_target_leaves_no_valid_levy_destination(self):
        plugin, home, work = self._plugin()
        work.disable("flood")
        actions = plugin.levy_walk(
            PopulationTemplate(),
            {
                "region": "Region",
                "node_id": home.id,
                "acting_node_types": ["home"],
                "target_node_types": ["work"],
            },
            0,
            0,
        )
        self.assertEqual(actions, [])

    def test_plural_target_node_types_key_is_supported(self):
        self.assertEqual(
            LevyWalkPlugin._get_target_node_types({"target_node_types": ["work"]}),
            ["work"],
        )


class SimulatorPhaseOrderingTest(unittest.TestCase):
    def test_regular_actions_are_consumed_before_end_actions_are_generated(self):
        simulation = LodusSimulation(EnvironmentGraph())
        state = {"value": 0, "observed": None}

        def set_value(pop_template, values, cycle_step, simulation_step):
            state["value"] = values["value"]

        simulation.add_action_type_to_function("set_value", set_value, True)
        regular = Action("set_value", PopulationTemplate(), {"value": 1})
        simulation.routine_controller.generate_regular_action_list = lambda _: [regular]

        def generate_end(cycle_step, simulation_step):
            state["observed"] = state["value"]
            return []

        simulation.routine_controller.generate_end_of_step_action_list = generate_end
        simulation.process_regular_and_end_of_step_actions(0, 0)
        self.assertEqual(state["observed"], 1)


if __name__ == "__main__":
    unittest.main()
