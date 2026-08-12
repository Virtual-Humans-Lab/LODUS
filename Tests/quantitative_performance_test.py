import csv
import json
from pathlib import Path
import tempfile
import unittest

from misc_scripts.run_quantitative_performance import (
    BEGIN_MARKER,
    END_MARKER,
    EXPECTED_CONFIGURATIONS,
    EXPECTED_RUNS,
    REPETITIONS,
    TEX_PATH,
    build_catalog,
    expand_runs,
    inspect_run,
    render_generated_tables,
    replace_generated_block,
)


class QuantitativePerformanceCatalogTest(unittest.TestCase):
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
        self.assertEqual(EXPECTED_CONFIGURATIONS, generated.count("MISSING DATA"))
        self.assertNotIn("10.0.262000", content)
        self.assertIn("10.0.26200", content)


if __name__ == "__main__":
    unittest.main()
