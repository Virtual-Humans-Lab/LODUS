"""Aggregate dialysis batches into paper-ready tables and plots."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px


DEFAULT_COMPARISONS = {
    "isolated_moinhos": ("K01", "K02"),
    "fast_recovery": ("K02", "K03"),
    "historical_clinic_flood": ("K01", "K04"),
    "synthetic_eta_flood": ("K01", "K05"),
    "combined_disruption": ("K01", "K06"),
    "failure_topology": ("K08", "K09"),
    "complete_combined": ("K10", "K11"),
}
METRICS = [
    "coverage",
    "due_wait_patient_hours",
    "overdue_end",
    "average_admission_distance_km",
    "disabled_clinic_hours",
    "runtime_seconds",
]


def bootstrap_ci(values: np.ndarray, seed: int = 2026) -> tuple[float, float]:
    values = values[np.isfinite(values)]
    if not len(values):
        return np.nan, np.nan
    if len(values) == 1:
        return float(values[0]), float(values[0])
    random = np.random.default_rng(seed)
    samples = random.choice(
        values, size=(5000, len(values)), replace=True
    ).mean(axis=1)
    return tuple(np.quantile(samples, [0.025, 0.975]))


def scenario_summary(runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    complete = runs[runs["status"].isin(["complete", "skipped"])]
    for scenario_id, group in complete.groupby("scenario_id"):
        row = {"scenario_id": scenario_id, "repetitions": len(group)}
        for metric in METRICS:
            values = pd.to_numeric(group[metric], errors="coerce").to_numpy()
            low, high = bootstrap_ci(values)
            row[f"{metric}_mean"] = float(np.nanmean(values))
            row[f"{metric}_std"] = float(np.nanstd(values, ddof=1)) if len(values) > 1 else 0.0
            row[f"{metric}_ci_low"] = low
            row[f"{metric}_ci_high"] = high
        rows.append(row)
    return pd.DataFrame(rows).sort_values("scenario_id")


def paired_comparisons(runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, (control_id, variant_id) in DEFAULT_COMPARISONS.items():
        control = runs[runs["scenario_id"] == control_id].set_index("seed")
        variant = runs[runs["scenario_id"] == variant_id].set_index("seed")
        paired_seeds = control.index.intersection(variant.index)
        for metric in METRICS:
            differences = (
                pd.to_numeric(variant.loc[paired_seeds, metric])
                - pd.to_numeric(control.loc[paired_seeds, metric])
            ).to_numpy(dtype=float)
            low, high = bootstrap_ci(differences)
            rows.append(
                {
                    "comparison": name,
                    "control": control_id,
                    "variant": variant_id,
                    "metric": metric,
                    "paired_repetitions": len(differences),
                    "mean_paired_difference": (
                        float(np.mean(differences))
                        if len(differences)
                        else np.nan
                    ),
                    "ci_low": low,
                    "ci_high": high,
                }
            )
    return pd.DataFrame(rows)


def redistribution_table(results_root: Path, runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for comparison, (control_id, variant_id) in DEFAULT_COMPARISONS.items():
        control_seeds = set(
            runs.loc[runs["scenario_id"] == control_id, "seed"]
        )
        variant_seeds = set(
            runs.loc[runs["scenario_id"] == variant_id, "seed"]
        )
        for seed in sorted(control_seeds & variant_seeds):
            paths = {}
            for label, scenario_id in (
                ("control", control_id),
                ("variant", variant_id),
            ):
                paths[label] = (
                    results_root
                    / scenario_id
                    / f"seed_{int(seed):03d}"
                    / "data_frames"
                    / "dialysis_origin_clinic.csv"
                )
            if not all(path.is_file() for path in paths.values()):
                continue
            control = pd.read_csv(
                paths["control"], sep=";", encoding="utf-8-sig"
            )
            variant = pd.read_csv(
                paths["variant"], sep=";", encoding="utf-8-sig"
            )
            merged = control[["Origin", "Clinic", "Admitted"]].merge(
                variant[["Origin", "Clinic", "Admitted"]],
                on=["Origin", "Clinic"],
                how="outer",
                suffixes=("_control", "_variant"),
            ).fillna(0)
            delta = merged["Admitted_variant"] - merged["Admitted_control"]
            rows.append(
                {
                    "comparison": comparison,
                    "seed": seed,
                    "positive_flow_change": float(delta.clip(lower=0).sum()),
                    "negative_flow_change": float((-delta.clip(upper=0)).sum()),
                    "receiving_flows": int((delta > 0).sum()),
                    "reduced_flows": int((delta < 0).sum()),
                }
            )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-root",
        type=Path,
        default=Path("results/dialysis"),
    )
    args = parser.parse_args()
    summary_path = args.results_root / "summary.csv"
    runs = pd.read_csv(summary_path)
    tables = args.results_root / "analysis"
    tables.mkdir(parents=True, exist_ok=True)
    grouped = scenario_summary(runs)
    paired = paired_comparisons(runs)
    redistribution = redistribution_table(args.results_root, runs)
    grouped.to_csv(tables / "scenario_summary.csv", index=False)
    paired.to_csv(tables / "paired_comparisons.csv", index=False)
    redistribution.to_csv(tables / "redistribution.csv", index=False)

    complete = runs[runs["status"].isin(["complete", "skipped"])]
    for metric, title in (
        ("coverage", "Dialysis Treatment Coverage"),
        ("due_wait_patient_hours", "Cumulative Due-Wait Exposure"),
        ("disabled_clinic_hours", "Disabled Clinic-Hours"),
        ("runtime_seconds", "Simulation Runtime"),
    ):
        figure = px.box(
            complete,
            x="scenario_id",
            y=metric,
            points="all",
            title=title,
        )
        figure.write_html(
            tables / f"{metric}.html", include_plotlyjs=True
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
