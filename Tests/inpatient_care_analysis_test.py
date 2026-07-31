import pandas as pd
import pytest

from inpatient_care_analysis import (
    aggregate_time_steps,
    long_distribution_summary,
    paired_policy_tables,
    parse_seeds as parse_analysis_seeds,
    weighted_mean,
    weighted_quantile,
)
from inpatient_care_experiments import (
    SPECIALIZED_CSVS,
    _is_complete,
    parse_seeds as parse_batch_seeds,
)


@pytest.mark.parametrize(
    "parser", [parse_analysis_seeds, parse_batch_seeds]
)
def test_seed_parser_supports_ranges_lists_and_deduplication(parser):
    assert parser("3, 0-2,2") == [0, 1, 2, 3]
    with pytest.raises(ValueError, match="range end"):
        parser("4-2")


def test_population_weighted_statistics_treat_cohorts_as_people():
    values = [0, 2, 8]
    populations = [8, 1, 1]
    assert weighted_mean(values, populations) == pytest.approx(1.0)
    assert weighted_quantile(values, populations, 0.5) == 0
    assert weighted_quantile(values, populations, 0.95) == 8


def test_distribution_summary_includes_requested_percentiles():
    frame = pd.DataFrame(
        {
            "scenario": ["A"] * 4,
            "metric_value": [0, 10, 20, 30],
        }
    )
    summary = long_distribution_summary(
        frame, ["scenario"], ["metric_value"]
    ).iloc[0]
    assert summary["repetitions"] == 4
    assert summary["mean"] == 15
    assert summary["median"] == 15
    assert summary["p05"] == pytest.approx(1.5)
    assert summary["p95"] == pytest.approx(28.5)


def test_paired_policy_table_matches_runs_by_seed():
    rows = []
    for seed, overflow, queue in ((0, 100, 80), (1, 100, 70)):
        for scenario, admitted in (
            ("ReferenceDemandOverflow", overflow),
            ("ReferenceDemandQueue", queue),
        ):
            row = {
                "scenario": scenario,
                "seed": seed,
                "admitted": admitted,
            }
            for metric in (
                "admission_coverage",
                "final_queue",
                "peak_queue",
                "queue_patient_steps",
                "mean_admission_delay",
                "maximum_admission_delay",
                "peak_overflow",
                "excess_bed_steps",
                "occupied_bed_steps",
                "inpatients_end",
            ):
                row[metric] = 0
            rows.append(row)
    paired, summary = paired_policy_tables(pd.DataFrame(rows))
    admitted = paired[
        (paired["family"] == "ReferenceDemand")
        & (paired["metric"] == "admitted")
    ]
    assert admitted["queue_minus_overflow"].tolist() == [-20, -30]
    admitted_summary = summary[
        (summary["family"] == "ReferenceDemand")
        & (summary["metric"] == "admitted")
    ].iloc[0]
    assert admitted_summary["mean_difference"] == -25


def test_time_step_aggregation_preserves_seed_uncertainty():
    frame = pd.DataFrame(
        {
            "scenario": ["A", "A"],
            "family": ["A", "A"],
            "policy": ["queue", "queue"],
            "simulation_step": [0, 0],
            "seed": [0, 1],
            "new_demand": [10, 20],
            "admitted": [5, 15],
            "discharged": [0, 0],
            "occupancy": [5, 15],
            "configured_capacity": [10, 10],
            "overflow": [0, 0],
            "waiting": [5, 5],
            "cumulative_demand": [10, 20],
            "cumulative_admitted": [5, 15],
            "cumulative_admission_coverage": [0.5, 0.75],
        }
    )
    row = aggregate_time_steps(frame).iloc[0]
    assert row["repetitions"] == 2
    assert row["occupancy_mean"] == 10
    assert row["occupancy_p05"] == pytest.approx(5.5)
    assert row["occupancy_p95"] == pytest.approx(14.5)


def test_batch_completion_rejects_an_outdated_step_schema(tmp_path):
    data_frames = tmp_path / "data_frames"
    data_frames.mkdir()
    (tmp_path / "run_metadata.json").write_text(
        '{"status": "complete"}', encoding="utf8"
    )
    for filename in SPECIALIZED_CSVS:
        (data_frames / filename).write_text("placeholder\n", encoding="utf8")
    assert not _is_complete(tmp_path)
    (data_frames / "inpatient_step.csv").write_text(
        "Global Population;Population Delta From Initial\n",
        encoding="utf8",
    )
    assert _is_complete(tmp_path)
