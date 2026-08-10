"""Create publication figures comparing LodusPop's Porto Alegre environments.

The maps intentionally show only the spatial unit boundaries and home POIs.  This
keeps the comparison legible while making the change in spatial resolution clear.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.lines import Line2D
from pyproj import CRS, Transformer
import shapefile


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "data_input"
NEIGHBORHOOD_SHP = (
    DATA_ROOT / "spatial" / "bairros_vigentes" / "bairros_vigentes.shp"
)
SECTOR_SHP = DATA_ROOT / "spatial" / "setores_2022" / "setores_2022_poa.shp"

ORIGINAL_ENV = DATA_ROOT / "Environment-PortoAlegre94RegionsDefault.json"
REDUCED_ENV = DATA_ROOT / "enumeration_area" / "Environment-13-EnumArea.json"
COMPLETE_ENV = DATA_ROOT / "enumeration_area" / "Environment-POA-EnumArea.json"

DEFAULT_OUTPUT = REPO_ROOT / "thesis" / "flood_chapter" / "Figures"

LAND = "#f4f6f7"
NEIGHBORHOOD_FILL = "#dceaf3"
SECTOR_FILL = "#eef4f7"
NEIGHBORHOOD_EDGE = "#526777"
SECTOR_EDGE = "#9eacb5"
HOME = "#c65336"


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value))
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]", "", value)


# The simulation uses two historical neighborhood labels that differ from the
# current municipal boundary layer.  These are explicit, documented aliases.
NEIGHBORHOOD_ALIASES = {
    normalize("Passo D'Areia"): normalize("Passo da Areia"),
    normalize("São José"): normalize("Vila São José"),
}


def load_environment(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def node_type(node: dict) -> str:
    return str(node.get("poi_type", node.get("name", "")))


def home_nodes(environment: dict) -> list[dict]:
    homes = []
    for region in environment["regions"]:
        for node in region["points_of_interest"]:
            if node_type(node) == "home":
                homes.append(node)
    return homes


def sector_ids(environment: dict) -> set[str]:
    return {
        str(node["attributes"]["enumeration_area"])
        for node in home_nodes(environment)
    }


def shape_parts(shape: shapefile.Shape) -> list[list[tuple[float, float]]]:
    stops = list(shape.parts) + [len(shape.points)]
    return [shape.points[start:end] for start, end in zip(stops, stops[1:])]


def read_neighborhoods(
    wanted_names: set[str],
) -> list[list[tuple[float, float]]]:
    wanted = {
        NEIGHBORHOOD_ALIASES.get(normalize(name), normalize(name))
        for name in wanted_names
    }
    parts = []
    matched = set()
    with shapefile.Reader(str(NEIGHBORHOOD_SHP), encoding="utf-8") as reader:
        for record, shape in zip(reader.iterRecords(), reader.iterShapes()):
            name = normalize(record["NOME"])
            if name in wanted:
                parts.extend(shape_parts(shape))
                matched.add(name)
    missing = wanted - matched
    if missing:
        raise ValueError(f"Neighborhood geometry not found for: {sorted(missing)}")
    return parts


def read_sectors(wanted_ids: set[str]) -> list[list[tuple[float, float]]]:
    parts = []
    matched = set()
    with shapefile.Reader(str(SECTOR_SHP), encoding="utf-8") as reader:
        for record, shape in zip(reader.iterRecords(), reader.iterShapes()):
            sector_id = str(record["CD_SETOR"])
            if sector_id in wanted_ids:
                parts.extend(shape_parts(shape))
                matched.add(sector_id)
    missing = wanted_ids - matched
    if missing:
        raise ValueError(f"Census-sector geometry not found for {len(missing)} IDs")
    return parts


def coordinate_transformer() -> Transformer:
    projection = CRS.from_wkt(
        NEIGHBORHOOD_SHP.with_suffix(".prj").read_text(encoding="utf-8")
    )
    return Transformer.from_crs("EPSG:4326", projection, always_xy=True)


def projected_homes(environment: dict) -> tuple[list[float], list[float]]:
    homes = home_nodes(environment)
    longitude, latitude = zip(*(node["lng_lat"] for node in homes))
    x, y = coordinate_transformer().transform(longitude, latitude)
    return list(x), list(y)


def add_parts(
    axis,
    parts: list[list[tuple[float, float]]],
    *,
    facecolor: str,
    edgecolor: str,
    linewidth: float,
    zorder: int,
) -> None:
    axis.add_collection(
        PolyCollection(
            parts,
            facecolors=facecolor,
            edgecolors=edgecolor,
            linewidths=linewidth,
            zorder=zorder,
        )
    )


def add_scale_bar(axis, length_m: int) -> None:
    xmin, xmax = axis.get_xlim()
    ymin, ymax = axis.get_ylim()
    x0 = xmin + 0.075 * (xmax - xmin)
    y0 = ymin + 0.055 * (ymax - ymin)
    axis.plot([x0, x0 + length_m], [y0, y0], color="#27343d", lw=1.8, zorder=8)
    axis.vlines(
        [x0, x0 + length_m],
        y0 - 90,
        y0 + 90,
        color="#27343d",
        lw=1.0,
        zorder=8,
    )
    label = f"{length_m // 1000} km" if length_m >= 1000 else f"{length_m} m"
    axis.text(
        x0 + length_m / 2,
        y0 + 180,
        label,
        ha="center",
        va="bottom",
        fontsize=7,
        color="#27343d",
    )


def add_north_arrow(axis) -> None:
    axis.annotate(
        "N",
        xy=(0.925, 0.91),
        xytext=(0.925, 0.79),
        xycoords="axes fraction",
        ha="center",
        va="center",
        fontsize=8,
        fontweight="bold",
        arrowprops={"arrowstyle": "-|>", "color": "#27343d", "lw": 1.0},
    )


def finish_axis(
    axis,
    x: list[float],
    y: list[float],
    scale_m: int,
    boundary_parts: list[list[tuple[float, float]]],
) -> None:
    boundary_points = [point for part in boundary_parts for point in part]
    boundary_x, boundary_y = zip(*boundary_points)
    x = [*x, *boundary_x]
    y = [*y, *boundary_y]
    pad_x = (max(x) - min(x)) * 0.055
    pad_y = (max(y) - min(y)) * 0.055
    axis.set_xlim(min(x) - pad_x, max(x) + pad_x)
    axis.set_ylim(min(y) - pad_y, max(y) + pad_y)
    axis.set_aspect("equal", adjustable="box")
    axis.set_facecolor("white")
    axis.set_axis_off()
    add_scale_bar(axis, scale_m)
    add_north_arrow(axis)


def plot_original(axis, environment: dict, panel_label: str = "") -> None:
    names = {region["name"] for region in environment["regions"]}
    neighborhood_parts = read_neighborhoods(names)
    add_parts(
        axis,
        neighborhood_parts,
        facecolor=NEIGHBORHOOD_FILL,
        edgecolor=NEIGHBORHOOD_EDGE,
        linewidth=0.45,
        zorder=1,
    )
    x, y = projected_homes(environment)
    axis.scatter(
        x,
        y,
        s=7,
        facecolor=HOME,
        edgecolor="white",
        linewidth=0.25,
        zorder=4,
    )
    axis.set_title(
        f"{panel_label}Neighborhood-level environment\n94 regions · 94 home POIs",
        fontsize=9,
        fontweight="semibold",
        pad=7,
    )
    finish_axis(axis, x, y, 5_000, neighborhood_parts)


def plot_census(
    axis,
    environment: dict,
    title: str,
    panel_label: str = "",
    scale_m: int = 5_000,
) -> None:
    region_names = {region["name"] for region in environment["regions"]}
    census_parts = read_sectors(sector_ids(environment))
    add_parts(
        axis,
        census_parts,
        facecolor=SECTOR_FILL,
        edgecolor=SECTOR_EDGE,
        linewidth=0.18,
        zorder=1,
    )
    neighborhood_parts = read_neighborhoods(region_names)
    axis.add_collection(
        LineCollection(
            neighborhood_parts,
            colors=NEIGHBORHOOD_EDGE,
            linewidths=0.65,
            zorder=3,
        )
    )
    x, y = projected_homes(environment)
    marker_size = 3.7 if len(x) < 1_000 else 1.15
    axis.scatter(x, y, s=marker_size, color=HOME, linewidth=0, zorder=4)
    axis.set_title(
        f"{panel_label}{title}\n{len(region_names):,} regions · {len(x):,} home POIs",
        fontsize=9,
        fontweight="semibold",
        pad=7,
    )
    finish_axis(axis, x, y, scale_m, [*census_parts, *neighborhood_parts])


def save_figure(figure, output_base: Path) -> None:
    figure.savefig(output_base.with_suffix(".pdf"), bbox_inches="tight")
    figure.savefig(output_base.with_suffix(".png"), dpi=300, bbox_inches="tight")


def create_figures(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    original = load_environment(ORIGINAL_ENV)
    reduced = load_environment(REDUCED_ENV)
    complete = load_environment(COMPLETE_ENV)

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["DejaVu Serif"],
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    panels = [
        ("environment_original_94", lambda ax: plot_original(ax, original)),
        (
            "environment_census_reduced_13",
            lambda ax: plot_census(
                ax, reduced, "Reduced census-sector environment", scale_m=1_000
            ),
        ),
        (
            "environment_census_complete_94",
            lambda ax: plot_census(ax, complete, "Complete census-sector environment"),
        ),
    ]
    for filename, draw in panels:
        figure, axis = plt.subplots(figsize=(4.1, 4.8))
        figure.subplots_adjust(left=0.03, right=0.97, bottom=0.04, top=0.88)
        draw(axis)
        save_figure(figure, output_dir / filename)
        plt.close(figure)

    figure, axes = plt.subplots(1, 3, figsize=(9.6, 4.6))
    figure.subplots_adjust(left=0.01, right=0.99, bottom=0.14, top=0.84, wspace=0.015)
    plot_original(axes[0], original, "(a) ")
    plot_census(
        axes[1],
        reduced,
        "Reduced census-sector environment",
        "(b) ",
        scale_m=1_000,
    )
    plot_census(axes[2], complete, "Complete census-sector environment", "(c) ")
    legend = [
        Line2D([0], [0], color=NEIGHBORHOOD_EDGE, lw=1.0, label="Neighborhood boundary"),
        Line2D([0], [0], color=SECTOR_EDGE, lw=0.6, label="Census-sector boundary"),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=HOME,
            markeredgecolor="none",
            markersize=4,
            label="Modeled home POI",
        ),
    ]
    figure.legend(
        handles=legend,
        loc="outside lower center",
        ncol=3,
        frameon=False,
        fontsize=8,
        handlelength=1.8,
    )
    save_figure(figure, output_dir / "spatial_environment_comparison")
    plt.close(figure)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output directory (default: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args()


if __name__ == "__main__":
    create_figures(parse_args().output_dir.resolve())
