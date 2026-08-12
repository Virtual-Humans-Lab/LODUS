"""Generate thesis figures for environmental-disruption mobility results."""

from __future__ import annotations

import math
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from scipy.stats import t

try:
    from misc_scripts.plot_spatial_environments import (
        NEIGHBORHOOD_EDGE,
        SECTOR_EDGE,
        add_parts,
        coordinate_transformer,
        finish_axis,
        read_neighborhoods,
        read_sectors,
    )
except ModuleNotFoundError:
    from plot_spatial_environments import (
        NEIGHBORHOOD_EDGE,
        SECTOR_EDGE,
        add_parts,
        coordinate_transformer,
        finish_axis,
        read_neighborhoods,
        read_sectors,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "thesis" / "flood_chapter" / "Figures"
RESULT_ROOT = ROOT / "output_logs"
CORE_ROOT = RESULT_ROOT / "popular_times_v2_stage4_production"
ADAPTATION_ROOT = RESULT_ROOT / "popular_times_v2_stage5"
COMMUTE_ROOT = RESULT_ROOT / "popular_times_v2_stage6"

TEAL = "#087F8C"
ORANGE = "#D76735"
BLUE = "#3973B7"
INK = "#243238"
MUTED = "#66777B"
GRID = "#D9E0DF"
SECTOR_FILL = "#F4F7F6"

ENVIRONMENT_FILES = {
    13: ROOT / "data_input" / "enumeration_area" / "Environment-13-EnumArea.json",
    94: ROOT
    / "data_input"
    / "enumeration_area"
    / "Environment-POA-EnumArea-PopularTimes.json",
}

ENVIRONMENTS = (13, 94)
ENVIRONMENT_COLORS = {13: TEAL, 94: ORANGE}
ENVIRONMENT_MARKERS = {13: "o", 94: "s"}


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 8.5,
            "axes.titlesize": 9.5,
            "axes.labelsize": 8.5,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": INK,
            "text.color": INK,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def read_results(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", encoding="utf-8-sig")


def mean_interval(values: pd.Series) -> tuple[float, float, float]:
    values = pd.to_numeric(values, errors="raise").astype(float)
    mean = float(values.mean())
    if len(values) <= 1:
        return mean, mean, mean
    critical = float(t.ppf(0.975, len(values) - 1))
    margin = critical * float(values.std(ddof=1)) / math.sqrt(len(values))
    return mean, mean - margin, mean + margin


def save_figure(figure: plt.Figure, stem: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUTPUT_DIR / f"{stem}.pdf", bbox_inches="tight")
    figure.savefig(OUTPUT_DIR / f"{stem}.png", dpi=300, bbox_inches="tight")
    plt.close(figure)


def scenario_statistics(
    data: pd.DataFrame,
    scenarios: list[str],
    metric: str,
) -> list[tuple[float, float, float]]:
    statistics = []
    for scenario in scenarios:
        rows = data.loc[data["scenario"].eq(scenario)]
        if rows.empty:
            raise ValueError(f"No result rows found for {scenario}")
        statistics.append(mean_interval(rows[metric]))
    return statistics


def add_fulfillment_series(
    axis,
    y_positions: np.ndarray,
    statistics: list[tuple[float, float, float]],
    environment: int,
) -> None:
    offset = 0.105 if environment == 13 else -0.105
    means = np.asarray([value[0] * 100 for value in statistics])
    lower = np.asarray([(value[0] - value[1]) * 100 for value in statistics])
    upper = np.asarray([(value[2] - value[0]) * 100 for value in statistics])
    color = ENVIRONMENT_COLORS[environment]
    axis.errorbar(
        means,
        y_positions + offset,
        xerr=np.vstack([lower, upper]),
        fmt=ENVIRONMENT_MARKERS[environment],
        color=color,
        markerfacecolor="white",
        markeredgewidth=1.35,
        markersize=5.5,
        linewidth=1.1,
        capsize=2.6,
        label=f"{environment}-region environment",
        zorder=4,
    )
    for x_value, y_value in zip(means, y_positions + offset):
        axis.annotate(
            f"{x_value:.1f}",
            (x_value, y_value),
            xytext=(-5, 0) if x_value > 99.2 else (5, 0),
            textcoords="offset points",
            ha="right" if x_value > 99.2 else "left",
            va="center",
            fontsize=7.2,
            color=color,
        )


def plot_fulfillment_comparison() -> None:
    core = read_results(CORE_ROOT / "production_runs.csv")
    adaptation = read_results(ADAPTATION_ROOT / "stage5_runs.csv")
    commute = read_results(COMMUTE_ROOT / "stage6_runs.csv")

    activity_labels = [
        "No exposure",
        "Activity destinations",
        "Homes",
        "Homes and destinations",
        "Combined + activity rerouting",
    ]
    commute_labels = [
        "No exposure",
        "Destinations",
        "Homes",
        "All POI types",
        "All POI types + activity rerouting",
    ]
    y_positions = np.arange(4, -1, -1, dtype=float)

    figure, axes = plt.subplots(
        2,
        1,
        figsize=(7.2, 5.7),
        constrained_layout=True,
    )

    for environment in ENVIRONMENTS:
        activity_scenarios = [
            f"{environment}_levy_on_flood_none",
            f"{environment}_levy_on_flood_pois",
            f"{environment}_levy_on_flood_homes",
            f"{environment}_levy_on_flood_both",
        ]
        activity_statistics = scenario_statistics(
            core, activity_scenarios, "fulfillment_rate"
        )
        reroute_scenario = f"{environment}_levy_on_flood_both_reroute"
        activity_statistics.extend(
            scenario_statistics(adaptation, [reroute_scenario], "fulfillment_rate")
        )
        add_fulfillment_series(
            axes[0], y_positions, activity_statistics, environment
        )

        commute_scenarios = [
            f"{environment}_levy_v2_flood_none",
            f"{environment}_levy_v2_flood_destinations",
            f"{environment}_levy_v2_flood_homes",
            f"{environment}_levy_v2_flood_all",
            f"{environment}_levy_v2_flood_all_pt_reroute",
        ]
        commute_statistics = scenario_statistics(
            commute, commute_scenarios, "levy_fulfillment_rate"
        )
        add_fulfillment_series(
            axes[1], y_positions, commute_statistics, environment
        )

    panel_settings = [
        (axes[0], activity_labels, 90.0, "(a) Activity-visit fulfillment"),
        (axes[1], commute_labels, 82.0, "(b) Work and school commute fulfillment"),
    ]
    for axis, labels, minimum, title in panel_settings:
        axis.axvline(100, color=MUTED, linewidth=0.9, linestyle=(0, (3, 2)))
        axis.set_xlim(minimum, 101.0)
        axis.set_ylim(-0.55, 4.55)
        axis.set_yticks(y_positions, labels)
        axis.set_xlabel("Fulfillment (%)")
        axis.set_title(title, loc="left", fontweight="bold")
        axis.grid(axis="x", color=GRID, linewidth=0.7)
        axis.set_axisbelow(True)

    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="outside upper center",
        ncols=2,
        frameon=False,
    )
    save_figure(figure, "environment_disruption_fulfillment_comparison")


def plot_rerouting_burden() -> None:
    data = read_results(ADAPTATION_ROOT / "stage5_runs.csv")
    data = data.loc[data["levy"].astype(str).str.lower().eq("true")].copy()
    metrics = [
        ("mean_reroute_distance_per_traveler", "Mean displacement", "m", 1),
        ("receiving_destinations", "Receiving destinations", "POIs", 0),
        ("peak_receiving_load", "Maximum added load", "travelers", 0),
    ]

    figure, axes = plt.subplots(
        1,
        3,
        figsize=(7.2, 2.45),
        constrained_layout=True,
    )
    y_positions = np.asarray([1.0, 0.0])

    for axis, (metric, title, unit, decimals) in zip(axes, metrics):
        values = []
        for environment in ENVIRONMENTS:
            rows = data.loc[data["environment"].astype(int).eq(environment)]
            values.append(float(pd.to_numeric(rows[metric]).mean()))
        maximum = max(values)
        for y_value, environment, value in zip(
            y_positions, ENVIRONMENTS, values
        ):
            color = ENVIRONMENT_COLORS[environment]
            axis.hlines(y_value, 0, value, color=color, linewidth=3.5, alpha=0.24)
            axis.plot(
                value,
                y_value,
                ENVIRONMENT_MARKERS[environment],
                color=color,
                markerfacecolor="white",
                markeredgewidth=1.5,
                markersize=6.5,
            )
            formatted = f"{value:,.{decimals}f}"
            axis.text(
                value + maximum * 0.035,
                y_value,
                formatted,
                va="center",
                ha="left",
                fontsize=7.8,
                color=color,
                fontweight="semibold",
            )
        axis.set_xlim(0, maximum * 1.30)
        axis.set_ylim(-0.55, 1.55)
        axis.set_yticks(y_positions, ["13 regions", "94 regions"])
        axis.set_title(title, loc="left", fontweight="bold")
        axis.set_xlabel(unit)
        axis.grid(axis="x", color=GRID, linewidth=0.7)
        axis.set_axisbelow(True)
        if axis is not axes[0]:
            axis.tick_params(axis="y", length=0)
            axis.set_yticklabels([])

    save_figure(figure, "environment_disruption_rerouting_burden")


def state_at_water_level(environment: int, water_level: float) -> pd.DataFrame:
    source = json.loads(ENVIRONMENT_FILES[environment].read_text(encoding="utf-8"))
    rows = []
    for region in source["regions"]:
        for node in region["points_of_interest"]:
            node_type = str(node["poi_type"])
            if node_type not in {
                "home",
                "marketplace",
                "restaurant",
                "pharmacy",
                "work",
                "school",
            }:
                continue
            threshold = float(node["attributes"]["water_level"])
            rows.append(
                {
                    "Region": region["name"],
                    "Node Type": node_type,
                    "Longitude": float(node["lng_lat"][0]),
                    "Latitude": float(node["lng_lat"][1]),
                    "Enumeration Area": str(node["attributes"]["enumeration_area"]),
                    "Enabled": int(water_level < threshold),
                }
            )
    return pd.DataFrame(rows)


def draw_exposure_map(
    axis,
    environment: int,
    water_level: float,
    panel: str,
) -> None:
    state = state_at_water_level(environment, water_level)
    homes = state.loc[state["Node Type"].eq("home")]
    sector_ids = set(homes["Enumeration Area"].astype(str))
    region_names = set(homes["Region"].astype(str))
    sector_parts = read_sectors(sector_ids)
    neighborhood_parts = read_neighborhoods(region_names)

    add_parts(
        axis,
        sector_parts,
        facecolor=SECTOR_FILL,
        edgecolor=SECTOR_EDGE,
        linewidth=0.12 if environment == 94 else 0.18,
        zorder=1,
    )
    from matplotlib.collections import LineCollection

    axis.add_collection(
        LineCollection(
            neighborhood_parts,
            colors=NEIGHBORHOOD_EDGE,
            linewidths=0.65,
            zorder=2,
        )
    )

    transformer = coordinate_transformer()
    longitude = pd.to_numeric(state["Longitude"]).to_numpy()
    latitude = pd.to_numeric(state["Latitude"]).to_numpy()
    x_values, y_values = transformer.transform(longitude, latitude)
    state = state.assign(ProjectedX=x_values, ProjectedY=y_values)

    home_nodes = state.loc[state["Node Type"].eq("home")]
    activity = state.loc[
        state["Node Type"].isin(["marketplace", "restaurant", "pharmacy"])
    ]
    commute = state.loc[state["Node Type"].isin(["work", "school"])]
    scale = 1.0 if environment == 94 else 2.2

    for subset, marker in ((home_nodes, "s"), (activity, "o"), (commute, "^")):
        enabled = subset.loc[subset["Enabled"].eq(1)]
        disabled = subset.loc[subset["Enabled"].eq(0)]
        axis.scatter(
            enabled["ProjectedX"],
            enabled["ProjectedY"],
            s=1.8 * scale,
            marker=marker,
            color=TEAL,
            alpha=0.42,
            linewidth=0,
            zorder=4,
        )
        axis.scatter(
            disabled["ProjectedX"],
            disabled["ProjectedY"],
            s=4.0 * scale,
            marker=marker,
            color=ORANGE,
            alpha=0.90,
            linewidth=0,
            zorder=5,
        )

    disabled_homes = int(home_nodes["Enabled"].eq(0).sum())
    disabled_activity = int(activity["Enabled"].eq(0).sum())
    disabled_commute = int(commute["Enabled"].eq(0).sum())
    disabled_total = disabled_homes + disabled_activity + disabled_commute
    axis.set_title(
        f"{panel} {environment}-region environment\n"
        f"{disabled_total:,} of {len(state):,} POIs unavailable\n"
        f"{disabled_homes:,} homes; {disabled_activity:,} activities; "
        f"{disabled_commute:,} work/school",
        loc="left",
        fontweight="bold",
        fontsize=8.8,
        pad=6,
    )
    finish_axis(
        axis,
        state["ProjectedX"].tolist(),
        state["ProjectedY"].tolist(),
        1_000 if environment == 13 else 5_000,
        [*sector_parts, *neighborhood_parts],
    )


def plot_flood_exposure() -> None:
    water_path = (
        CORE_ROOT
        / "13_levy_on_flood_both-seed0"
        / "data_frames"
        / "water_level_step.csv"
    )
    water = read_results(water_path)
    water["Simulation Step"] = water["Simulation Step"].astype(int)
    water["Water Level"] = pd.to_numeric(water["Water Level"])
    peak_row = water.loc[water["Water Level"].idxmax()]
    peak_step = int(peak_row["Simulation Step"])
    peak_level = float(peak_row["Water Level"])

    figure = plt.figure(figsize=(7.2, 6.0), constrained_layout=True)
    grid = figure.add_gridspec(2, 2, height_ratios=[3.2, 1.15])
    map_axes = [figure.add_subplot(grid[0, 0]), figure.add_subplot(grid[0, 1])]
    water_grid = grid[1, :].subgridspec(
        1,
        2,
        width_ratios=[0.08, 0.92],
        wspace=0,
    )
    water_axis = figure.add_subplot(water_grid[0, 1])

    draw_exposure_map(map_axes[0], 13, peak_level, "(a)")
    draw_exposure_map(map_axes[1], 94, peak_level, "(b)")

    days = water["Simulation Step"].to_numpy(dtype=float) / 24.0
    levels = water["Water Level"].to_numpy(dtype=float)
    water_axis.plot(days, levels, color=BLUE, linewidth=1.25)
    water_axis.fill_between(days, levels, levels.min(), color=BLUE, alpha=0.10)
    water_axis.axvline(peak_step / 24.0, color=ORANGE, linestyle=(0, (3, 2)), linewidth=1)
    water_axis.plot(peak_step / 24.0, peak_level, "o", color=ORANGE, markersize=5)
    water_axis.annotate(
        f"Maximum: {peak_level:.2f} m",
        (peak_step / 24.0, peak_level),
        xytext=(8, -3),
        textcoords="offset points",
        va="top",
        fontsize=7.8,
        color=ORANGE,
        fontweight="semibold",
    )
    water_axis.set_title("(c) Water-level time series", loc="left", fontweight="bold")
    water_axis.set_xlabel("Simulation day")
    water_axis.set_ylabel("Water level (m)")
    water_axis.set_xlim(days.min(), days.max())
    water_axis.grid(color=GRID, linewidth=0.7)
    water_axis.set_axisbelow(True)

    legend = [
        Line2D(
            [0],
            [0],
            marker="s",
            color="none",
            markerfacecolor=TEAL,
            markeredgecolor="none",
            markersize=5,
            label="Available home",
        ),
        Line2D(
            [0],
            [0],
            marker="s",
            color="none",
            markerfacecolor=ORANGE,
            markeredgecolor="none",
            markersize=5,
            label="Unavailable home",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=TEAL,
            markeredgecolor="none",
            markersize=5,
            label="Available activity",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=ORANGE,
            markeredgecolor="none",
            markersize=5,
            label="Unavailable activity",
        ),
        Line2D(
            [0],
            [0],
            marker="^",
            color="none",
            markerfacecolor=TEAL,
            markeredgecolor="none",
            markersize=5,
            label="Available work/school",
        ),
        Line2D(
            [0],
            [0],
            marker="^",
            color="none",
            markerfacecolor=ORANGE,
            markeredgecolor="none",
            markersize=5,
            label="Unavailable work/school",
        ),
    ]
    figure.legend(
        handles=legend,
        loc="outside upper center",
        ncols=3,
        frameon=False,
    )
    save_figure(figure, "environment_disruption_flood_exposure")


def plot_poi_unavailability_breakdown() -> None:
    water_path = (
        CORE_ROOT
        / "13_levy_on_flood_both-seed0"
        / "data_frames"
        / "water_level_step.csv"
    )
    water = read_results(water_path)
    peak_level = float(pd.to_numeric(water["Water Level"]).max())
    node_types = ["home", "marketplace", "restaurant", "pharmacy", "work", "school"]
    labels = ["Homes", "Marketplaces", "Restaurants", "Pharmacies", "Work", "Schools"]
    y_positions = np.arange(len(node_types) - 1, -1, -1, dtype=float)

    figure, axis = plt.subplots(figsize=(7.2, 3.35), constrained_layout=True)
    offsets = {13: 0.16, 94: -0.16}
    bar_height = 0.27

    for environment in ENVIRONMENTS:
        state = state_at_water_level(environment, peak_level)
        percentages = []
        counts = []
        totals = []
        for node_type in node_types:
            rows = state.loc[state["Node Type"].eq(node_type)]
            unavailable = int(rows["Enabled"].eq(0).sum())
            total = len(rows)
            percentages.append(100.0 * unavailable / total)
            counts.append(unavailable)
            totals.append(total)

        color = ENVIRONMENT_COLORS[environment]
        positions = y_positions + offsets[environment]
        axis.barh(
            positions,
            percentages,
            height=bar_height,
            color=color,
            alpha=0.78,
            label=f"{environment}-region environment",
            zorder=3,
        )
        for y_value, percentage, count, total in zip(
            positions, percentages, counts, totals
        ):
            axis.text(
                percentage + 0.25,
                y_value,
                f"{count:,}/{total:,}",
                ha="left",
                va="center",
                fontsize=7.4,
                color=color,
                fontweight="semibold",
            )

    axis.set_yticks(y_positions, labels)
    axis.set_xlim(0, 23.0)
    axis.set_xlabel("POIs unavailable at the 5.33 m maximum (%)")
    axis.set_title(
        "Unavailable POIs by type",
        loc="left",
        fontweight="bold",
    )
    axis.grid(axis="x", color=GRID, linewidth=0.7)
    axis.set_axisbelow(True)
    handles, legend_labels = axis.get_legend_handles_labels()
    figure.legend(
        handles,
        legend_labels,
        loc="outside upper center",
        ncols=2,
        frameon=False,
    )
    save_figure(figure, "environment_disruption_poi_breakdown")


def main() -> None:
    configure_style()
    plot_fulfillment_comparison()
    plot_rerouting_burden()
    plot_flood_exposure()
    plot_poi_unavailability_breakdown()


if __name__ == "__main__":
    main()
