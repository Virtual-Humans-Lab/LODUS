from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "output_logs" / "popular_times_v2_stage6"
OUT = ROOT / "thesis" / "final_draft" / "fig" / "res-normal-life"
SEEDS = range(5)


def weighted_ecdf(frame):
    grouped = frame.groupby("distance", as_index=False)["quantity"].sum().sort_values("distance")
    return grouped["distance"], grouped["quantity"].cumsum() / grouped["quantity"].sum()


def load_data():
    visits, movements, steps = [], [], []
    for seed in SEEDS:
        data = RUNS / f"13_levy_v2_flood_none-seed{seed}" / "data_frames"
        visit = pd.read_csv(data / "popular_times_visits.csv.gz", sep=";")
        visits.append(visit[visit["event"] == "start"])
        movement = pd.read_csv(data / "levy_v2_movements.csv.gz", sep=";", low_memory=False)
        movements.append(movement[movement["event"] == "departure"])
        step = pd.read_csv(data / "levy_v2_step_group.csv", sep=";")
        step["seed"] = seed
        steps.append(step)
    return pd.concat(visits), pd.concat(movements), pd.concat(steps)


def distance_figure(visits, movements):
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 6.5))
    for label, frame, color, linestyle in (
        ("Marketplaces", visits[visits.poi_type == "marketplace"], "#3569A8", "-"),
        ("Restaurants", visits[visits.poi_type == "restaurant"], "#D97732", "--"),
        ("Pharmacies", visits[visits.poi_type == "pharmacy"], "#348C6C", "-."),
    ):
        x, y = weighted_ecdf(frame)
        axes[0].plot(x / 1000, y, label=label, color=color, linestyle=linestyle, linewidth=2.6)
    for label, frame, color, linestyle in (
        ("Work commutes", movements[movements.group == "worker"], "#3569A8", "-"),
        ("School commutes", movements[movements.group == "student"], "#D97732", "--"),
    ):
        x, y = weighted_ecdf(frame)
        axes[1].plot(x / 1000, y, label=label, color=color, linestyle=linestyle, linewidth=2.6)
    for axis, title, limit in zip(
        axes,
        ["(a) Activity distances", "(b) Commute distances"],
        [1.0, 6.9],
    ):
        axis.set_title(title, loc="left", fontweight="bold", fontsize=18)
        axis.set_xlim(0, limit)
        axis.set_ylim(0, 1)
        axis.set_xlabel("Distance (km)", fontsize=15)
        axis.set_ylabel("Cumulative fraction of travelers", fontsize=15)
        axis.grid(color="#D4DCDD", linewidth=.9)
        axis.legend(frameon=False, loc="lower right", fontsize=14)
        axis.tick_params(labelsize=13)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
    fig.tight_layout(w_pad=1.2)
    fig.savefig(OUT / "routine_mobility_distance_ecdf.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def activity_figure():
    data = RUNS / "13_levy_v2_flood_none-seed0" / "data_frames" / "popular_times_step_type.csv"
    frame = pd.read_csv(data, sep=";")
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), constrained_layout=True)
    names = [("marketplace", "Marketplace"), ("restaurant", "Restaurant"), ("pharmacy", "Pharmacy")]
    for axis, (kind, title) in zip(axes, names):
        part = frame[frame.node_type == kind].groupby(["weekday", "cycle_step"])["requested"].sum()
        table = part.unstack(fill_value=0).reindex(index=range(7), columns=range(24), fill_value=0)
        values = table.to_numpy(dtype=float)
        values /= values.sum()
        image = axis.imshow(values, aspect="auto", cmap="YlGnBu")
        axis.set_title(title)
        axis.set_xticks(range(0, 24, 4))
        axis.set_xlabel("Hour")
        axis.set_yticks(range(7), ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
        fig.colorbar(image, ax=axis, fraction=.046, pad=.04, format="%.3f")
    fig.savefig(OUT / "routine_activity_weekday_hour.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def activity_percentage_figure():
    data = RUNS / "13_levy_v2_flood_none-seed0" / "data_frames" / "popular_times_step_type.csv"
    frame = pd.read_csv(data, sep=";")
    names = [("marketplace", "(a) Marketplaces"), ("restaurant", "(b) Restaurants"), ("pharmacy", "(c) Pharmacies")]
    matrices = []
    for kind, _ in names:
        part = frame[frame.node_type == kind].groupby(["weekday", "cycle_step"])["requested"].sum()
        table = part.unstack(fill_value=0).reindex(index=range(7), columns=range(24), fill_value=0)
        values = table.to_numpy(dtype=float)
        matrices.append(100 * values / values.sum())
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.9), sharey=True)
    for axis, (_, title), values in zip(axes, names, matrices):
        image = axis.imshow(values, aspect="auto", cmap="YlGnBu", vmin=0, vmax=4.1)
        axis.set_title(title, loc="left", fontweight="bold", fontsize=17)
        axis.set_xticks(range(0, 24, 4))
        axis.set_xlabel("Hour of day", fontsize=14)
        axis.tick_params(labelsize=12)
    axes[0].set_yticks(range(7), ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    axes[0].set_ylabel("Weekday", fontsize=14)
    for axis in axes:
        for spine in axis.spines.values():
            spine.set_visible(False)
    fig.subplots_adjust(left=.075, right=.91, bottom=.16, top=.88, wspace=.07)
    color_axis = fig.add_axes([.925, .16, .015, .72])
    colorbar = fig.colorbar(image, cax=color_axis, ticks=[0, 1, 2, 3, 4])
    colorbar.set_label("Share of activity-type demand (%)", fontsize=14)
    colorbar.ax.tick_params(labelsize=12)
    fig.savefig(OUT / "routine_activity_weekday_hour_percentage.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def commute_figure(steps):
    demand = steps.groupby(["group", "cycle_step"])["requested"].sum() / (len(SEEDS) * 56)
    occupancy_rows = []
    for (seed, group), part in steps.groupby(["seed", "group"]):
        full_steps = pd.DataFrame(index=range(56 * 24))
        full_steps = full_steps.join(
            part.set_index("simulation_step")[["population_moved", "population_returned"]]
        ).fillna(0)
        full_steps["occupancy"] = (
            full_steps["population_moved"] - full_steps["population_returned"]
        ).cumsum()
        full_steps["cycle_step"] = full_steps.index % 24
        full_steps["seed"] = seed
        full_steps["group"] = group
        occupancy_rows.append(full_steps.reset_index(drop=True))
    occupancy = pd.concat(occupancy_rows).groupby(["group", "cycle_step"])["occupancy"].mean()
    hours = np.arange(24)
    fig, axes = plt.subplots(2, 1, figsize=(11.2, 8.0), sharex=True)
    for group, label, color in (("worker", "Work commutes", "#3569A8"), ("student", "School commutes", "#D97732")):
        requested = demand.loc[group].reindex(hours, fill_value=0)
        occupied = occupancy.loc[group].reindex(hours, fill_value=0)
        axes[0].plot(hours, requested, label=label, color=color, linewidth=2.6)
        axes[1].plot(hours, occupied, label=label, color=color, linewidth=2.6)
    titles = ["(a) Mean daily departure demand", "(b) Mean destination occupancy"]
    ylabels = ["Requested commuting population", "Population at work or school"]
    for axis, title, ylabel in zip(axes, titles, ylabels):
        axis.set_title(title, loc="left", fontweight="bold", fontsize=17)
        axis.set_xticks(range(0, 24, 2))
        axis.set_xlabel("Hour of day", fontsize=14)
        axis.set_ylabel(ylabel)
        axis.grid(color="#D4DCDD", linewidth=.9)
        axis.legend(frameon=False)
        axis.tick_params(labelsize=12)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
    fig.tight_layout(h_pad=.8)
    fig.savefig(OUT / "routine_commute_temporal_behavior.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    visits, movements, steps = load_data()
    distance_figure(visits, movements)
    activity_figure()
    activity_percentage_figure()
    commute_figure(steps)


if __name__ == "__main__":
    main()
