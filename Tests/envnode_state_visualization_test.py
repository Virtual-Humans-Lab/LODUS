import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from misc_scripts.visualize_envnode_states import (
    CORE_NODE_TYPES,
    LEVY_NODE_TYPES,
    FLOOD_MODES,
    RunInfo,
    build_payload,
    choose_canonical_run,
    discover_scenarios,
    generate_scenario_visualizations,
    load_state_log,
    load_water_log,
    scenario_name,
    verify_seed_invariance,
    visible_node_types,
)


STATE_HEADER = [
    "Simulation Step",
    "Cycle Step",
    "Cycle",
    "Region",
    "Node",
    "Unique Name",
    "Node Type",
    "Longitude",
    "Latitude",
    "Enumeration Area",
    "Enabled",
]
WATER_HEADER = ["Simulation Step", "Cycle Step", "Cycle", "Water Level"]


class EnvNodeVisualizationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def make_run(
        self,
        environment="13",
        levy=False,
        flood="none",
        seed=0,
        suffix="",
        changed=False,
    ):
        name = scenario_name(environment, levy, flood)
        run_root = self.root / f"{name}-seed{seed}{suffix}"
        data_root = run_root / "data_frames"
        data_root.mkdir(parents=True)
        metadata = {
            "status": "complete",
            "seed": seed,
            "simulation_parameters": {"total_cycles": 1, "cycle_length": 2},
            "resolved_config": {
                "simulation_parameters": {"total_cycles": 1, "cycle_length": 2},
                "popular_times_v2_study": {
                    "environment": environment,
                    "levy": levy,
                    "flood": flood,
                },
            },
        }
        if levy:
            metadata["resolved_config"]["levy_walk_plugin"] = {}
        if flood != "none":
            metadata["resolved_config"]["water_level_data_plugin"] = {
                "target_node_types": ["home"]
            }
        (run_root / "run_metadata.json").write_text(json.dumps(metadata), encoding="utf8")

        node_types = (*CORE_NODE_TYPES, *LEVY_NODE_TYPES, "p8", "p9")
        state_rows = []
        for index, node_type in enumerate(node_types):
            state_rows.append(
                [
                    0,
                    0,
                    0,
                    "Azenha",
                    f"Azenha//{node_type}_0",
                    f"{node_type}_0",
                    node_type,
                    -51.21 + index / 1000,
                    -30.04 + index / 1000,
                    "431490205000592",
                    1,
                ]
            )
        if flood in {"homes", "both"}:
            state_rows.append(
                [
                    1,
                    1,
                    0,
                    "Azenha",
                    "Azenha//home_0",
                    "home_0",
                    "home",
                    -51.21,
                    -30.04,
                    "431490205000592",
                    1 if changed else 0,
                ]
            )
        if flood in {"pois", "both"}:
            state_rows.append(
                [
                    1,
                    1,
                    0,
                    "Azenha",
                    "Azenha//pharmacy_0",
                    "pharmacy_0",
                    "pharmacy",
                    -51.209,
                    -30.039,
                    "431490205000592",
                    0,
                ]
            )
        with (data_root / "envnode_state.csv").open("w", encoding="utf8", newline="") as stream:
            writer = csv.writer(stream, delimiter=";")
            writer.writerow(STATE_HEADER)
            writer.writerows(state_rows)

        with (data_root / "water_level_step.csv").open("w", encoding="utf8", newline="") as stream:
            writer = csv.writer(stream, delimiter=";")
            writer.writerow(WATER_HEADER)
            if flood != "none":
                writer.writerows([[0, 0, 0, 2.0], [1, 1, 0, 4.0]])
        return run_root

    def test_discovers_exact_13_region_matrix(self):
        for levy in (False, True):
            for flood in FLOOD_MODES:
                self.make_run(levy=levy, flood=flood)
        groups = discover_scenarios(self.root)
        self.assertEqual(len(groups), 8)
        self.assertEqual(
            set(groups),
            {
                scenario_name("13", levy, flood)
                for levy in (False, True)
                for flood in FLOOD_MODES
            },
        )

    def test_discovery_reports_missing_scenario(self):
        self.make_run(levy=False, flood="none")
        with self.assertRaisesRegex(ValueError, "missing"):
            discover_scenarios(self.root)

    def test_canonical_run_prefers_seed_zero_then_lowest_seed(self):
        metadata = {"resolved_config": {"popular_times_v2_study": {}}}
        runs = [
            RunInfo(self.root / "three", metadata, "13", True, "both", 3),
            RunInfo(self.root / "zero", metadata, "13", True, "both", 0),
            RunInfo(self.root / "one", metadata, "13", True, "both", 1),
        ]
        self.assertEqual(choose_canonical_run(runs).seed, 0)
        self.assertEqual(choose_canonical_run([runs[0], runs[2]]).seed, 1)

    def test_node_filter_is_dynamic_and_never_includes_p8_or_p9(self):
        self.assertEqual(visible_node_types(False), CORE_NODE_TYPES)
        self.assertEqual(visible_node_types(True), CORE_NODE_TYPES + LEVY_NODE_TYPES)
        self.assertEqual(visible_node_types(True, ["home", "p8", "p9"]), ("home",))

    def test_identical_seeds_are_verified_and_difference_is_rejected(self):
        first_root = self.make_run(levy=True, flood="both", seed=0)
        second_root = self.make_run(levy=True, flood="both", seed=1)
        runs = [RunInfo(first_root, json.loads((first_root / "run_metadata.json").read_text()), "13", True, "both", 0),
                RunInfo(second_root, json.loads((second_root / "run_metadata.json").read_text()), "13", True, "both", 1)]
        canonical, state, water, total_steps = verify_seed_invariance(runs, visible_node_types(True))
        self.assertEqual(canonical.seed, 0)
        self.assertEqual(total_steps, 2)
        self.assertFalse(state.empty)
        self.assertEqual(len(water), 2)

        changed_root = self.make_run(levy=True, flood="both", seed=2, changed=True)
        changed = RunInfo(changed_root, json.loads((changed_root / "run_metadata.json").read_text()), "13", True, "both", 2)
        with self.assertRaisesRegex(ValueError, "node-state timeline"):
            verify_seed_invariance([runs[0], changed], visible_node_types(True))

    @patch("misc_scripts.visualize_envnode_states.geometry_lines")
    @patch("misc_scripts.visualize_envnode_states.find_shapefile")
    def test_payload_uses_sparse_events_and_excludes_unused_types(self, find_shp, geometry):
        find_shp.return_value = self.root / "shape.shp"
        geometry.return_value = {"lon": [-51.21, None], "lat": [-30.04, None]}
        run_root = self.make_run(levy=False, flood="both")
        metadata = json.loads((run_root / "run_metadata.json").read_text())
        state = load_state_log(run_root / "data_frames/envnode_state.csv", visible_node_types(False))
        water = load_water_log(run_root / "data_frames/water_level_step.csv", "both", 2)
        payload = build_payload(state, water, metadata, scenario_name("13", False, "both"), 1, 2, self.root)
        self.assertEqual({node["type"] for node in payload["nodes"]}, set(CORE_NODE_TYPES))
        self.assertNotIn("p8", json.dumps(payload))
        self.assertEqual(payload["events"], [[1, 0, 0], [1, 2, 0]])
        self.assertEqual(payload["totalSteps"], 2)

    def test_flood_requires_complete_water_series(self):
        run_root = self.make_run(flood="homes")
        water_path = run_root / "data_frames/water_level_step.csv"
        water_path.write_text(";".join(WATER_HEADER) + "\n0;0;0;2.0\n", encoding="utf8")
        with self.assertRaisesRegex(ValueError, "cover every step"):
            load_water_log(water_path, "homes", 2)

    @patch("misc_scripts.visualize_envnode_states.geometry_lines")
    @patch("misc_scripts.visualize_envnode_states.find_shapefile")
    def test_batch_writes_one_html_per_scenario(self, find_shp, geometry):
        find_shp.return_value = self.root / "shape.shp"
        geometry.return_value = {"lon": [-51.21, None], "lat": [-30.04, None]}
        for levy in (False, True):
            for flood in FLOOD_MODES:
                self.make_run(levy=levy, flood=flood)
        output = self.root / "visualizations"
        paths = generate_scenario_visualizations(self.root, output, self.root)
        self.assertEqual(len(paths), 8)
        self.assertEqual(len(list(output.glob("*.html"))), 8)
        self.assertTrue((output / "13_levy_on_flood_both.html").exists())
        html = (output / "13_levy_off_flood_none.html").read_text(encoding="utf8")
        self.assertIn("Flooding disabled", html)
        self.assertNotIn('"type":"p8"', html)


if __name__ == "__main__":
    unittest.main()
