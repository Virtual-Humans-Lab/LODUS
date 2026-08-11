"""Create thesis figures from the completed routine-mobility simulations."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import t


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGE4_ROOT = PROJECT_ROOT / "output_logs" / "popular_times_v2_stage4_production"
STAGE6_ROOT = PROJECT_ROOT / "output_logs" / "popular_times_v2_stage6"
OUTPUT_ROOT = PROJECT_ROOT / "thesis" / "flood_chapter" / "fig" / "results"
SEEDS = range(5)

BLUE = "#3569A8"
ORANGE = "#D97732"
GREEN = "#348C6C"
GRID = "#D9DEE7"


def interval(values: pd.Series) -> tuple[float, float, float]:
    values = values.astype(float)
    mean = float(values.mean())
    if len(values) < 2:
        return mean, mean, mean
    half_width = float(t.ppf(0.975, len(values) - 1) * values.std(ddof=1) / np.sqrt(len(values)))
    return mean, mean - half_width, mean + half_width


def errorbar(
    axis: plt.Axes,
    position: int,
    values: pd.Series,
    color: str,
    label: str,
) -> None:
    mean, lower, upper = interval(values)
    errors = np.array([[mean - lower], [upper - mean]])
    axis.errorbar(
        position,
        mean,
        yerr=errors,
        fmt="o",
        markersize=9,
        capsize=5,
        linewidth=2,
        color=color,
        markeredgecolor="white",
        markeredgewidth=0.8,
        zorder=3,
    )
    axis.annotate(
        f"{mean:,.2f} m\n{label}",
        (position, mean),
        xytext=(0, 12),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=9,
    )


def composition_figure() -> Path:
    stage4 = pd.read_csv(STAGE4_ROOT / "production_runs.csv", sep=";")
    stage6 = pd.read_csv(STAGE6_ROOT / "stage6_runs.csv", sep=";")
    groups = pd.read_csv(STAGE6_ROOT / "stage6_levy_groups.csv", sep=";")

    pt_only = stage4.loc[
        stage4["scenario"] == "13_levy_off_flood_none",
        "mean_distance_per_traveler",
    ]
    probabilistic = stage4.loc[
        stage4["scenario"] == "13_levy_on_flood_none",
        "mean_distance_per_traveler",
    ]
    attendance = stage6.loc[
        stage6["scenario"] == "13_levy_v2_flood_none",
        "pt_mean_distance_per_traveler",
    ]
    baseline_groups = groups[groups["scenario"] == "13_levy_v2_flood_none"]
    workers = baseline_groups.loc[
        baseline_groups["group"] == "worker", "mean_outbound_distance"
    ]
    students = baseline_groups.loc[
        baseline_groups["group"] == "student", "mean_outbound_distance"
    ]

    figure, axes = plt.subplots(1, 2, figsize=(11.2, 4.8))
    errorbar(axes[0], 0, pt_only, BLUE, "deterministic")
    errorbar(axes[0], 1, probabilistic, ORANGE, "95% CI, n=30")
    errorbar(axes[0], 2, attendance, GREEN, "95% CI, n=5")
    axes[0].set_xticks(
        range(3),
        ["Popular Times\nonly", "With probabilistic\nLévy Walk", "With attendance-\ncontrolled Lévy Walk"],
    )
    axes[0].set_ylabel("Mean activity source distance (m)")
    axes[0].set_title("(a) Activity sourcing by routine composition", loc="left")
    axes[0].set_xlim(-0.35, 2.35)
    axes[0].set_ylim(80, 89)

    errorbar(axes[1], 0, workers, BLUE, "95% CI, n=5")
    errorbar(axes[1], 1, students, ORANGE, "95% CI, n=5")
    axes[1].set_xticks(range(2), ["Workers", "Students"])
    axes[1].set_ylabel("Mean outbound commute distance (m)")
    axes[1].set_title("(b) Attendance commute distance by group", loc="left")
    axes[1].set_xlim(-0.25, 1.25)
    axes[1].set_ylim(1340, 1460)

    for axis in axes:
        axis.grid(axis="y", color=GRID, linewidth=0.8)
        axis.set_axisbelow(True)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)

    figure.suptitle("Routine-mobility distance outcomes (13-region environment)", fontsize=14)
    figure.tight_layout()
    output = OUTPUT_ROOT / "routine_mobility_composition.png"
    figure.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return output


def temporal_figure() -> Path:
    pt_path = (
        STAGE6_ROOT
        / "13_levy_v2_flood_none-seed0"
        / "data_frames"
        / "popular_times_step_type.csv"
    )
    pt = pd.read_csv(pt_path, sep=";")
    pt_profile = (
        pt.groupby(["weekday", "cycle_step", "node_type"], as_index=False)["requested"]
        .mean()
        .groupby(["weekday", "cycle_step"])["requested"]
        .sum()
        .unstack(fill_value=0)
        .reindex(index=range(7), columns=range(24), fill_value=0)
    )

    commute_frames = []
    for seed in SEEDS:
        path = (
            STAGE6_ROOT
            / f"13_levy_v2_flood_none-seed{seed}"
            / "data_frames"
            / "levy_v2_step_group.csv"
        )
        frame = pd.read_csv(path, sep=";")
        frame["seed"] = seed
        commute_frames.append(frame)
    commute = pd.concat(commute_frames, ignore_index=True)
    daily_hourly = (
        commute.groupby(["group", "cycle_step"])["requested"].sum()
        / (len(SEEDS) * 56)
    )

    figure, axes = plt.subplots(
        2,
        1,
        figsize=(11.2, 7.2),
        gridspec_kw={"height_ratios": [1.15, 1]},
    )
    image = axes[0].imshow(pt_profile.to_numpy(), aspect="auto", cmap="YlGnBu")
    axes[0].set_yticks(range(7), ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    axes[0].set_xticks(range(0, 24, 2))
    axes[0].set_xticklabels(range(0, 24, 2))
    axes[0].set_xlabel("Hour")
    axes[0].set_title("(a) Mean Popular Times requests by weekday and hour", loc="left")
    colorbar = figure.colorbar(image, ax=axes[0], pad=0.015)
    colorbar.set_label("Requested activity visits")

    hours = np.arange(24)
    for group, color, label in (
        ("worker", BLUE, "Workers"),
        ("student", ORANGE, "Students"),
    ):
        values = daily_hourly.loc[group].reindex(hours, fill_value=0)
        axes[1].plot(hours, values, marker="o", linewidth=2, markersize=4, color=color, label=label)
    axes[1].set_xticks(range(0, 24, 2))
    axes[1].set_xlabel("Departure hour")
    axes[1].set_ylabel("Mean requests per simulated day")
    axes[1].set_title("(b) Attendance requests by group and departure hour", loc="left")
    axes[1].grid(axis="y", color=GRID, linewidth=0.8)
    axes[1].set_axisbelow(True)
    axes[1].spines["top"].set_visible(False)
    axes[1].spines["right"].set_visible(False)
    axes[1].legend(frameon=False)

    figure.suptitle("Temporal structure of routine-mobility demand (13-region environment)", fontsize=14)
    figure.tight_layout()
    output = OUTPUT_ROOT / "routine_mobility_temporal_demand.png"
    figure.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return output


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for output in (composition_figure(), temporal_figure()):
        print(output.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
