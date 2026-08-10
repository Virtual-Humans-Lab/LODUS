from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import t


ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = ROOT / "data_input" / "popular_times"
RESULTS_FILE = (
    ROOT
    / "docs"
    / "results"
    / "popular_times_v2_stage4"
    / "production_poi_type.csv"
)
OUTPUT_DIR = ROOT / "thesis" / "flood_chapter" / "Figures"

ACTIVITY_ORDER = ("marketplace", "restaurant", "pharmacy")
ACTIVITY_LABELS = {
    "marketplace": "Marketplace",
    "restaurant": "Restaurant",
    "pharmacy": "Pharmacy",
}


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "legend.fontsize": 8.5,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def save_figure(fig: plt.Figure, stem: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_DIR / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / f"{stem}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def weekly_profile_matrices() -> dict[str, np.ndarray]:
    matrices: dict[str, np.ndarray] = {}
    for activity in ACTIVITY_ORDER:
        data = pd.read_csv(PROFILE_DIR / f"{activity}.csv", encoding="utf-8-sig")
        matrix = (
            data.pivot_table(
                index="ciclo",
                columns="hora",
                values="quantidade",
                aggfunc="sum",
                fill_value=0,
            )
            .reindex(index=range(7), columns=range(24), fill_value=0)
            .to_numpy(dtype=float)
        )
        matrices[activity] = 100.0 * matrix / matrix.sum()
    return matrices


def plot_weekly_profiles() -> None:
    matrices = weekly_profile_matrices()
    maximum = max(float(matrix.max()) for matrix in matrices.values())
    maximum = math.ceil(maximum * 10.0) / 10.0

    fig, axes = plt.subplots(
        nrows=3,
        ncols=1,
        figsize=(7.2, 7.0),
        sharex=True,
        constrained_layout=True,
    )
    image = None
    for axis, activity in zip(axes, ACTIVITY_ORDER):
        image = axis.imshow(
            matrices[activity],
            aspect="auto",
            interpolation="nearest",
            cmap="YlGnBu",
            vmin=0,
            vmax=maximum,
        )
        axis.set_title(ACTIVITY_LABELS[activity], loc="left", fontweight="bold")
        axis.set_ylabel("Simulation day")
        axis.set_yticks(range(7), [f"Day {day}" for day in range(1, 8)])
        axis.set_xticks(range(0, 24, 2))
        axis.set_xticks(range(24), minor=True)
        axis.tick_params(which="minor", length=0)

    axes[-1].set_xlabel("Hour of day")
    assert image is not None
    colorbar = fig.colorbar(image, ax=axes, pad=0.02, shrink=0.92)
    colorbar.set_label("Share of the activity type's weekly demand (%)")
    save_figure(fig, "popular_times_weekly_profiles")


def mean_and_interval(values: pd.Series) -> tuple[float, float, float]:
    values = values.astype(float)
    mean = float(values.mean())
    if len(values) <= 1:
        return mean, mean, mean
    critical = float(t.ppf(0.975, len(values) - 1))
    margin = critical * float(values.std(ddof=1)) / math.sqrt(len(values))
    return mean, mean - margin, mean + margin


def baseline_distance_statistics() -> dict[tuple[int, str, str], tuple[float, float, float]]:
    data = pd.read_csv(RESULTS_FILE, sep=";", encoding="utf-8-sig")
    data = data.loc[data["flood"].eq("none")].copy()
    data["configuration"] = np.where(
        data["levy"].astype(str).str.lower().eq("true"),
        "Popular Times + Lévy Walk",
        "Popular Times only",
    )

    statistics: dict[tuple[int, str, str], tuple[float, float, float]] = {}
    grouped = data.groupby(["environment", "node_type", "configuration"], sort=False)
    for (environment, node_type, configuration), rows in grouped:
        statistics[(int(environment), str(node_type), str(configuration))] = (
            mean_and_interval(rows["mean_distance_per_traveler"])
        )
    return statistics


def plot_source_distance() -> None:
    statistics = baseline_distance_statistics()
    configurations = ("Popular Times only", "Popular Times + Lévy Walk")
    colors = ("#3B73B9", "#D46A2E")
    markers = ("o", "s")
    offsets = (-0.12, 0.12)
    x_positions = np.arange(len(ACTIVITY_ORDER), dtype=float)

    fig, axes = plt.subplots(
        nrows=1,
        ncols=2,
        figsize=(7.2, 3.45),
        sharey=True,
        constrained_layout=True,
    )

    for axis, environment in zip(axes, (13, 94)):
        plotted_means: dict[str, list[float]] = {}
        for configuration, color, marker, offset in zip(
            configurations, colors, markers, offsets
        ):
            means: list[float] = []
            lower_errors: list[float] = []
            upper_errors: list[float] = []
            for activity in ACTIVITY_ORDER:
                mean, lower, upper = statistics[(environment, activity, configuration)]
                means.append(mean)
                lower_errors.append(mean - lower)
                upper_errors.append(upper - mean)
            plotted_means[configuration] = means
            axis.errorbar(
                x_positions + offset,
                means,
                yerr=np.asarray([lower_errors, upper_errors]),
                fmt=marker,
                markersize=5.5,
                capsize=3,
                linewidth=1.2,
                color=color,
                label=configuration,
                zorder=3,
            )

        only = plotted_means[configurations[0]]
        composed = plotted_means[configurations[1]]
        for index, (start, end) in enumerate(zip(only, composed)):
            axis.plot(
                [x_positions[index] + offsets[0], x_positions[index] + offsets[1]],
                [start, end],
                color="#8A8A8A",
                linewidth=0.9,
                zorder=1,
            )
            axis.text(
                x_positions[index],
                max(start, end) + 0.65,
                f"{end - start:+.2f} m",
                ha="center",
                va="bottom",
                fontsize=7.5,
                color="#555555",
            )

        axis.set_title(f"{environment}-region environment", fontweight="bold")
        axis.set_xticks(
            x_positions,
            [ACTIVITY_LABELS[activity] for activity in ACTIVITY_ORDER],
            rotation=18,
            ha="right",
        )
        axis.set_ylim(75, 98)
        axis.grid(axis="y", color="#D8D8D8", linewidth=0.7, alpha=0.8)
        axis.set_axisbelow(True)

    axes[0].set_ylabel("Mean source distance (m)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="outside lower center",
        ncols=2,
        frameon=False,
    )
    save_figure(fig, "popular_times_source_distance_by_type")


def main() -> None:
    configure_style()
    plot_weekly_profiles()
    plot_source_distance()


if __name__ == "__main__":
    main()
