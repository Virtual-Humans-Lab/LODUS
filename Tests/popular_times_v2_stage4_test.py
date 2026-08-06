import json
import tempfile
import unittest
from pathlib import Path

from misc_scripts.run_popular_times_v2_production import (
    METRICS,
    RunSpec,
    _read_csv,
    compress_raw_outputs,
    completion_state,
    effect_statistics,
    production_specs,
)
from util.data_parse import load_experiment_config


class PopularTimesStage4MatrixTest(unittest.TestCase):
    def test_matrix_has_eight_deterministic_and_140_stochastic_runs(self):
        specs = production_specs()

        self.assertEqual(148, len(specs))
        self.assertEqual(148, len({spec.run_name for spec in specs}))
        self.assertEqual(8, sum(not spec.levy for spec in specs))
        self.assertEqual(140, sum(spec.levy for spec in specs))
        self.assertEqual(
            set(range(30)),
            {spec.seed for spec in specs if spec.levy and spec.scenario.startswith("13_")},
        )
        self.assertEqual(
            set(range(5)),
            {spec.seed for spec in specs if spec.levy and spec.scenario.startswith("94_")},
        )
        self.assertEqual({0}, {spec.seed for spec in specs if not spec.levy})

    def test_all_production_configs_explicitly_resolve_to_56_cycles(self):
        for scenario in sorted({spec.scenario for spec in production_specs()}):
            with self.subTest(scenario=scenario):
                config = load_experiment_config(
                    f"popular_times_v2/production/{scenario}"
                )
                self.assertEqual(56, config["simulation_parameters"]["total_cycles"])
                self.assertEqual(24, config["simulation_parameters"]["cycle_length"])

    def test_completion_requires_matching_seed_experiment_horizon_and_validation(self):
        spec = RunSpec("94_levy_on_flood_none", 7)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            data = output / spec.run_name / "data_frames"
            data.mkdir(parents=True)
            metadata = {
                "status": "complete",
                "experiment": spec.experiment,
                "seed": 7,
                "simulation_parameters": {"total_cycles": 56},
            }
            (data.parent / "run_metadata.json").write_text(
                json.dumps(metadata), encoding="utf8"
            )
            (data / "popular_times_validation.json").write_text(
                json.dumps({"passed": True}), encoding="utf8"
            )

            self.assertEqual("complete", completion_state(spec, output)[0])
            metadata["simulation_parameters"]["total_cycles"] = 5
            (data.parent / "run_metadata.json").write_text(
                json.dumps(metadata), encoding="utf8"
            )
            self.assertEqual("pending", completion_state(spec, output)[0])

    def test_raw_csv_compression_is_lossless_and_readable_by_analysis(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_path = Path(temporary)
            data = run_path / "data_frames"
            data.mkdir()
            demand = data / "popular_times_demand.csv"
            demand.write_text("requested;fulfilled\n2;1\n", encoding="utf-8-sig")

            compressed = compress_raw_outputs(run_path)

            self.assertFalse(demand.exists())
            self.assertTrue(Path(f"{demand}.gz").exists())
            self.assertIn("data_frames/popular_times_demand.csv.gz", compressed)
            self.assertEqual("2", list(_read_csv(demand))[0]["requested"])


class PopularTimesStage4AnalysisTest(unittest.TestCase):
    @staticmethod
    def _row(scenario, seed, value):
        environment = scenario.split("_", 1)[0]
        levy = "_levy_on_" in scenario
        flood = scenario.rsplit("_", 1)[-1]
        return {
            "scenario": scenario,
            "environment": environment,
            "levy": levy,
            "flood": flood,
            "seed": seed,
            **{metric: float(value) for metric in METRICS},
        }

    def test_effects_use_matched_seeds_and_do_not_invent_deterministic_intervals(self):
        rows = [
            self._row("13_levy_off_flood_none", 0, 10),
            self._row("13_levy_off_flood_pois", 0, 8),
            self._row("13_levy_off_flood_homes", 0, 9),
            self._row("13_levy_off_flood_both", 0, 6),
        ]
        for seed in range(2):
            rows.extend(
                [
                    self._row("13_levy_on_flood_none", seed, 20 + seed),
                    self._row("13_levy_on_flood_pois", seed, 17 + seed),
                    self._row("13_levy_on_flood_homes", seed, 18 + seed),
                    self._row("13_levy_on_flood_both", seed, 14 + seed),
                ]
            )

        effects = effect_statistics(rows)
        indexed = {
            (row["contrast"], row["stratum"], row["metric"]): row
            for row in effects
        }
        deterministic = indexed[
            ("flood_pois_minus_none", "off", "fulfilled")
        ]
        self.assertEqual(-2.0, deterministic["mean"])
        self.assertEqual("", deterministic["ci95_lower"])
        paired = indexed[("flood_pois_minus_none", "on", "fulfilled")]
        self.assertEqual(2, paired["n"])
        self.assertEqual(-3.0, paired["mean"])
        interaction = indexed[("flood_pois_x_homes", "on", "fulfilled")]
        self.assertEqual(-1.0, interaction["mean"])


if __name__ == "__main__":
    unittest.main()
