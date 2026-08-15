import csv
import json
from pathlib import Path
import tempfile
import unittest

from misc_scripts.run_quantitative_performance import (
    BEGIN_MARKER,
    DEFAULT_WORKERS,
    END_MARKER,
    EXPECTED_CONFIGURATIONS,
    EXPECTED_RUNS,
    REPETITIONS,
    RESULTS_DIR,
    RunnerAlreadyActive,
    TEX_PATH,
    build_catalog,
    compact_completed_run,
    compact_partial_run,
    expand_runs,
    inspect_run,
    parse_args,
    render_generated_tables,
    replace_generated_block,
    runner_lock,
)


class QuantitativePerformanceCatalogTest(unittest.TestCase):
    def test_default_command_uses_four_workers(self):
        self.assertEqual(4, DEFAULT_WORKERS)
        self.assertEqual(4, parse_args([]).workers)
        self.assertEqual(2, parse_args(["--workers", "2"]).workers)

    def test_sector_always_loads_required_blob_logger(self):
        source = (TEX_PATH.parents[2] / "sector_simulation.py").read_text(
            encoding="utf-8"
        )
        load = "lodus_simulation.load_plugin(blob_count_logger)"
        optional_bundle = (
            'if lodus_simulation.experiment_config.get('
            '"default_loggers_enabled", True):'
        )
        self.assertEqual(1, source.count(load))
        self.assertLess(source.index(load), source.index(optional_bundle))

    def test_single_instance_lock_rejects_a_second_orchestrator(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            with runner_lock(output):
                with self.assertRaises(RunnerAlreadyActive):
                    with runner_lock(output):
                        pass

    def test_catalog_has_48_configurations_and_240_runs_without_inpatient(self):
        catalog = build_catalog()
        self.assertEqual(EXPECTED_CONFIGURATIONS, len(catalog))
        self.assertEqual(EXPECTED_RUNS, len(expand_runs(catalog)))
        self.assertEqual(
            {"routine": 6, "adaptation": 10, "disruption": 8, "shelter": 13, "dialysis": 11},
            {
                group: sum(item.table_group == group for item in catalog)
                for group in {item.table_group for item in catalog}
            },
        )
        self.assertEqual(set(range(5)), set(REPETITIONS))
        self.assertFalse(any("inpatient" in repr(item).lower() for item in catalog))
        dialysis = [item for item in catalog if item.table_group == "dialysis"]
        self.assertEqual(
            [f"D{index:02d}" for index in range(1, 12)],
            [item.code for item in dialysis],
        )
        self.assertEqual(
            [f"K{index:02d}" for index in range(1, 12)],
            [item.key.split("_", 1)[0] for item in dialysis],
        )

    def test_resume_requires_all_metrics_validation_and_global_blob_csv(self):
        config = next(
            item
            for item in build_catalog()
            if item.code == "R01"
        )
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            path = output / config.table_group / config.key / "seed_000"
            data = path / "data_frames"
            data.mkdir(parents=True)
            metadata = {
                "status": "complete",
                "experiment": config.experiment,
                "seed": 0,
                "runtime_seconds": 12.5,
                "peak_memory_kib": 2048,
                "max_blob_count": 9,
                "commit_sha": "test-commit",
                "simulation_parameters": {"total_cycles": config.cycles},
            }
            (path / "run_metadata.json").write_text(
                json.dumps(metadata), encoding="utf-8"
            )
            (data / "popular_times_validation.json").write_text(
                '{"passed": true}', encoding="utf-8"
            )
            with (data / "blob_count_global.csv").open(
                "w", encoding="utf-8", newline=""
            ) as stream:
                writer = csv.writer(stream, delimiter=";")
                writer.writerow(["Simulation Frame", "Blob Count"])
                writer.writerow([0, 4])
                writer.writerow([1, 9])

            complete = inspect_run(
                config, 0, output, expected_commit="test-commit"
            )
            self.assertEqual("complete", complete.status, complete.detail)
            self.assertEqual(9, complete.max_blob_count)
            (data / "blob_count_global.csv").unlink()
            pending = inspect_run(
                config, 0, output, expected_commit="test-commit"
            )
            self.assertEqual("pending", pending.status)
            self.assertIn("blob_count_global.csv", pending.detail)

    def test_compaction_retains_only_required_resumable_artifacts(self):
        config = next(item for item in build_catalog() if item.code == "R01")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            path = output / config.table_group / config.key / "seed_000"
            data = path / "data_frames"
            data.mkdir(parents=True)
            (path / "run_metadata.json").write_text(
                json.dumps(
                    {
                        "status": "complete",
                        "experiment": config.experiment,
                        "seed": 0,
                        "runtime_seconds": 12.5,
                        "peak_memory_kib": 2048,
                        "max_blob_count": 9,
                        "commit_sha": "test-commit",
                        "simulation_parameters": {
                            "total_cycles": config.cycles
                        },
                    }
                ),
                encoding="utf-8",
            )
            (data / "popular_times_validation.json").write_text(
                '{"passed": true}', encoding="utf-8"
            )
            (data / "blob_count_global.csv").write_text(
                "Simulation Frame;Blob Count\n0;9\n", encoding="utf-8"
            )
            (data / "popular_times_visits.csv").write_text(
                "large,redundant,output\n", encoding="utf-8"
            )
            (path / "orchestrator.log").write_text(
                "verbose output\n", encoding="utf-8"
            )
            removed, _ = compact_completed_run(
                config, 0, output, "test-commit"
            )
            self.assertEqual(2, removed)
            self.assertFalse((data / "popular_times_visits.csv").exists())
            self.assertFalse((path / "orchestrator.log").exists())
            self.assertEqual(
                "complete",
                inspect_run(config, 0, output, "test-commit").status,
            )

    def test_partial_compaction_keeps_failure_and_log_tail(self):
        with tempfile.TemporaryDirectory() as temporary:
            partial = Path(temporary) / "seed_000.partial-test"
            data = partial / "data_frames"
            data.mkdir(parents=True)
            (data / "large.csv").write_text("raw\n" * 100, encoding="utf-8")
            (partial / "orchestrator.log").write_text(
                "diagnostic tail\n", encoding="utf-8"
            )
            (partial / "orchestrator_failure.json").write_text(
                '{"return_code": 1}', encoding="utf-8"
            )
            compact_partial_run(partial)
            self.assertFalse((data / "large.csv").exists())
            self.assertTrue((partial / "orchestrator.log").is_file())
            self.assertTrue(
                (partial / "orchestrator_failure.json").is_file()
            )
            self.assertTrue((partial / "partial_cleanup.json").is_file())

    def test_generated_block_names_missing_scenario_and_repetitions(self):
        row = {
            "code": "R01",
            "table_group": "routine",
            "scenario": "stage4_13_levy_off_flood_none",
            "description": "Popular Times only",
            "experiment": "popular_times_v2/production/13_levy_off_flood_none",
            "regions": 13,
            "cycles": 56,
            "required_repetitions": 5,
            "completed_repetitions": 0,
            "missing_repetitions": "0,1,2,3,4",
            "mean_max_blob_count": "",
            "mean_runtime_seconds": "",
            "runtime_seconds_per_cycle": "",
            "mean_peak_working_set_mib": "",
            "commit_sha": "",
        }
        generated = render_generated_tables([row])
        self.assertIn("MISSING DATA", generated)
        self.assertIn("13\\_levy\\_off\\_flood\\_none", generated)
        self.assertIn("0,1,2,3,4", generated)

        with tempfile.TemporaryDirectory() as temporary:
            tex = Path(temporary) / "section.tex"
            tex.write_text(
                f"before\n{BEGIN_MARKER}\nold\n{END_MARKER}\nafter\n",
                encoding="utf-8",
            )
            replace_generated_block(tex, generated)
            updated = tex.read_text(encoding="utf-8")
            self.assertIn("MISSING DATA", updated)
            self.assertEqual(1, updated.count(BEGIN_MARKER))
            self.assertEqual(1, updated.count(END_MARKER))

    def test_standalone_fragment_has_balanced_width_limited_tables_and_labels(self):
        content = TEX_PATH.read_text(encoding="utf-8")
        self.assertEqual(1, content.count(BEGIN_MARKER))
        self.assertEqual(1, content.count(END_MARKER))
        self.assertEqual(content.count("\\begin{table}"), content.count("\\end{table}"))
        self.assertEqual(5, content.count("\\begin{tabularx}{\\textwidth}"))
        self.assertIn("\\resizebox{\\textwidth}{!}", content)
        labels = [
            line.strip() for line in content.splitlines()
            if line.strip().startswith("\\label{")
        ]
        self.assertEqual(len(labels), len(set(labels)))
        generated = content.split(BEGIN_MARKER, 1)[1].split(END_MARKER, 1)[0]
        with (RESULTS_DIR / "performance_scenarios.csv").open(
            encoding="utf-8", newline=""
        ) as stream:
            scenarios = list(csv.DictReader(stream))
        incomplete = sum(
            int(row["completed_repetitions"]) < len(REPETITIONS)
            for row in scenarios
        )
        self.assertEqual(incomplete, generated.count("MISSING DATA"))
        self.assertNotIn("10.0.262000", content)
        self.assertIn("10.0.26200", content)


if __name__ == "__main__":
    unittest.main()
