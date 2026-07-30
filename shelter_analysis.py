"""Aggregate shelter batches and calculate bootstrap confidence intervals."""

from __future__ import annotations

import argparse
from importlib.util import find_spec
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px


METRICS = [
    "Coverage",
    "Unresolved Demand",
    "Peak Waitlist",
    "Waiting Person Steps",
    "Peak Utilization",
    "Mean Distance Km",
    "P95 Distance Km",
    "Equity Gap",
    "Runtime Seconds",
    "Peak Memory KiB",
]


def bootstrap_interval(
    values: np.ndarray,
    samples: int,
    rng: np.random.Generator,
) -> tuple[float, float]:
    if len(values) == 0:
        return np.nan, np.nan
    if len(values) == 1:
        return float(values[0]), float(values[0])
    means = rng.choice(
        values, size=(samples, len(values)), replace=True
    ).mean(axis=1)
    return tuple(np.quantile(means, [0.025, 0.975]))


def summarize(
    frame: pd.DataFrame, bootstrap_samples: int, random_seed: int
) -> pd.DataFrame:
    rng = np.random.default_rng(random_seed)
    rows = []
    complete = frame[frame["Status"].isin(["complete", "resumed"])]
    for scenario, group in complete.groupby("Scenario"):
        for metric in METRICS:
            values = pd.to_numeric(group[metric], errors="coerce").dropna().to_numpy()
            low, high = bootstrap_interval(values, bootstrap_samples, rng)
            rows.append({
                "Scenario": scenario,
                "Metric": metric,
                "Seeds": len(values),
                "Mean": values.mean() if len(values) else np.nan,
                "Standard Deviation": (
                    values.std(ddof=1) if len(values) > 1 else 0
                ),
                "CI 2.5%": low,
                "CI 97.5%": high,
            })
    return pd.DataFrame(rows)


def paired_differences(
    frame: pd.DataFrame,
    reference: str,
    bootstrap_samples: int,
    random_seed: int,
) -> pd.DataFrame:
    complete = frame[frame["Status"].isin(["complete", "resumed"])]
    reference_rows = complete[complete["Scenario"] == reference]
    if reference_rows.empty:
        return pd.DataFrame()
    rng = np.random.default_rng(random_seed)
    rows = []
    for scenario in sorted(set(complete["Scenario"]) - {reference}):
        comparison = complete[complete["Scenario"] == scenario]
        paired = reference_rows.merge(
            comparison, on="Seed", suffixes=("_reference", "_scenario")
        )
        for metric in METRICS:
            differences = (
                pd.to_numeric(
                    paired[f"{metric}_scenario"], errors="coerce"
                )
                - pd.to_numeric(
                    paired[f"{metric}_reference"], errors="coerce"
                )
            ).dropna().to_numpy()
            low, high = bootstrap_interval(
                differences, bootstrap_samples, rng
            )
            rows.append({
                "Reference": reference,
                "Scenario": scenario,
                "Metric": metric,
                "Paired Seeds": len(differences),
                "Mean Difference": (
                    differences.mean() if len(differences) else np.nan
                ),
                "CI 2.5%": low,
                "CI 97.5%": high,
            })
    return pd.DataFrame(rows)


def write_figures(
    frame: pd.DataFrame, output_path: Path, export_png: bool
):
    complete = frame[frame["Status"].isin(["complete", "resumed"])]
    html_path = output_path / "html"
    png_path = output_path / "figures"
    html_path.mkdir(parents=True, exist_ok=True)
    png_available = export_png and find_spec("kaleido") is not None
    for metric in METRICS:
        figure = px.box(
            complete, x="Scenario", y=metric, points="all",
            title=f"{metric} by shelter scenario",
        )
        figure.update_xaxes(tickangle=45)
        figure.write_html(
            html_path / f"{metric.lower().replace(' ', '_')}.html",
            include_plotlyjs=True,
        )
        if png_available:
            png_path.mkdir(parents=True, exist_ok=True)
            try:
                figure.write_image(
                    png_path / f"{metric.lower().replace(' ', '_')}.png"
                )
            except Exception:
                png_available = False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", default="output_logs/shelter_batch_summary.csv"
    )
    parser.add_argument(
        "--output", default="output_logs/shelter_analysis"
    )
    parser.add_argument("--reference", default="v3_reference")
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--no-png", action="store_true")
    args = parser.parse_args()
    frame = pd.read_csv(args.input)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    summary = summarize(frame, args.bootstrap_samples, args.seed)
    summary.to_csv(output / "bootstrap_summary.csv", index=False)
    paired = paired_differences(
        frame, args.reference, args.bootstrap_samples, args.seed
    )
    paired.to_csv(output / "paired_differences.csv", index=False)
    write_figures(frame, output, not args.no_png)


if __name__ == "__main__":
    main()
