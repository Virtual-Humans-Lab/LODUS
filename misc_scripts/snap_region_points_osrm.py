"""Snap the 94 simulation region points to roads with OSRM's nearest service.

For each region, request multiple nearest road candidates and select the closest
candidate that remains inside the corresponding vigente neighborhood geometry.
The raw responses are cached so an interrupted run can safely resume.
"""

from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pyproj import CRS, Transformer

from validate_region_points import (
    ENVIRONMENT,
    NAME_ALIASES,
    OUTPUT_DIR,
    SHAPE_DIR,
    normalized_name,
    point_in_rings,
    read_dbf,
    read_polygon_shapefile,
)


OSRM_BASE_URL = "https://router.project-osrm.org"
CANDIDATE_COUNT = 10
REQUEST_INTERVAL_SECONDS = 1.05
CACHE_PATH = OUTPUT_DIR / "osrm_nearest_cache.json"


def osrm_nearest(longitude: float, latitude: float) -> dict:
    coordinates = f"{longitude:.15g},{latitude:.15g}"
    url = (
        f"{OSRM_BASE_URL}/nearest/v1/driving/{coordinates}"
        f"?number={CANDIDATE_COUNT}"
    )
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "LODUS-region-coordinate-validation/1.0"},
    )
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
            if payload.get("code") != "Ok":
                raise RuntimeError(f"OSRM returned {payload!r}")
            return payload
        except (urllib.error.URLError, TimeoutError, RuntimeError) as error:
            last_error = error
            if attempt == 3:
                break
            time.sleep(2 ** attempt)
    raise RuntimeError(f"OSRM request failed for {coordinates}: {last_error}")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with ENVIRONMENT.open(encoding="utf-8") as handle:
        regions = json.load(handle)["regions"]

    attributes = read_dbf(SHAPE_DIR / "bairros_vigentes.dbf")
    shapes = read_polygon_shapefile(SHAPE_DIR / "bairros_vigentes.shp")
    if len(attributes) != len(shapes):
        raise ValueError(f"DBF/SHP record mismatch: {len(attributes)} vs {len(shapes)}")

    geometries_by_name: dict[str, list] = defaultdict(list)
    display_name: dict[str, str] = {}
    for attributes_row, rings in zip(attributes, shapes):
        key = normalized_name(attributes_row["NOME"])
        geometries_by_name[key].append(rings)
        display_name[key] = attributes_row["NOME"].title()

    local_crs = CRS.from_wkt((SHAPE_DIR / "bairros_vigentes.prj").read_text())
    to_local = Transformer.from_crs("EPSG:4326", local_crs, always_xy=True)

    if CACHE_PATH.exists():
        cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    else:
        cache = {}

    rows = []
    for index, region in enumerate(regions, start=1):
        original_lon, original_lat = region["lng_lat"]
        cache_key = f"{original_lon:.15g},{original_lat:.15g}"
        if cache_key not in cache:
            cache[cache_key] = osrm_nearest(original_lon, original_lat)
            CACHE_PATH.write_text(
                json.dumps(cache, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Queried {index}/{len(regions)}: {region['name']}", flush=True)
            if index < len(regions):
                time.sleep(REQUEST_INTERVAL_SECONDS)
        else:
            print(f"Cached {index}/{len(regions)}: {region['name']}", flush=True)

        requested_key = normalized_name(region["name"])
        matched_key = NAME_ALIASES.get(requested_key, requested_key)
        if matched_key not in geometries_by_name:
            raise ValueError(f"No corresponding geometry for {region['name']!r}")
        own_geometries = geometries_by_name[matched_key]

        original_xy = to_local.transform(original_lon, original_lat)
        if not any(point_in_rings(original_xy, rings) for rings in own_geometries):
            raise ValueError(f"Original point is outside {region['name']!r}")

        selected = None
        selected_rank = None
        for rank, waypoint in enumerate(cache[cache_key]["waypoints"], start=1):
            candidate_lon, candidate_lat = waypoint["location"]
            candidate_xy = to_local.transform(candidate_lon, candidate_lat)
            if any(point_in_rings(candidate_xy, rings) for rings in own_geometries):
                selected = waypoint
                selected_rank = rank
                break
        if selected is None:
            raise RuntimeError(
                f"None of the {CANDIDATE_COUNT} OSRM candidates for "
                f"{region['name']!r} are inside its geometry"
            )

        snapped_lon, snapped_lat = selected["location"]
        snapped_xy = to_local.transform(snapped_lon, snapped_lat)
        rows.append(
            {
                "region": region["name"],
                "matched_geometry": display_name[matched_key],
                "original_longitude": original_lon,
                "original_latitude": original_lat,
                "snapped_longitude": snapped_lon,
                "snapped_latitude": snapped_lat,
                "snap_distance_m": round(float(selected["distance"]), 3),
                "osrm_candidate_rank": selected_rank,
                "osrm_road_name": selected.get("name", ""),
                "original_within_geometry": True,
                "snapped_within_geometry": True,
                "original_x": original_xy[0],
                "original_y": original_xy[1],
                "snapped_x": snapped_xy[0],
                "snapped_y": snapped_xy[1],
            }
        )

    csv_path = OUTPUT_DIR / "region_points_osrm_snapped.csv"
    hidden_fields = {"original_x", "original_y", "snapped_x", "snapped_y"}
    csv_fields = [field for field in rows[0] if field not in hidden_fields]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        writer.writerows(
            {field: value for field, value in row.items() if field not in hidden_fields}
            for row in rows
        )

    fig, ax = plt.subplots(figsize=(12, 12), dpi=180)
    for rings in shapes:
        for ring in rings:
            if not ring:
                continue
            xs, ys = zip(*ring)
            ax.fill(xs, ys, color="#e8edf2", alpha=0.8, zorder=1)
            ax.plot(xs, ys, color="#7b8792", linewidth=0.35, zorder=2)

    for row in rows:
        ax.plot(
            [row["original_x"], row["snapped_x"]],
            [row["original_y"], row["snapped_y"]],
            color="#ef8a36",
            linewidth=0.6,
            alpha=0.8,
            zorder=3,
        )
    ax.scatter(
        [row["original_x"] for row in rows],
        [row["original_y"] for row in rows],
        s=25,
        facecolor="white",
        edgecolor="#16845b",
        linewidth=1.2,
        zorder=4,
    )
    ax.scatter(
        [row["snapped_x"] for row in rows],
        [row["snapped_y"] for row in rows],
        s=28,
        marker="x",
        color="#d95f02",
        linewidth=1.2,
        zorder=5,
    )

    nonfirst = sum(row["osrm_candidate_rank"] > 1 for row in rows)
    ax.set_title(
        "Porto Alegre: original and OSRM-snapped region points\n"
        f"94/94 snapped points inside their neighborhoods; "
        f"{nonfirst} required an in-region candidate beyond rank 1",
        fontsize=15,
        color="#20252a",
        linespacing=1.45,
        pad=18,
    )
    ax.legend(
        handles=[
            Line2D([0], [0], marker="o", color="none", markerfacecolor="white", markeredgecolor="#16845b", markersize=7, label="Original point"),
            Line2D([0], [0], marker="x", color="#d95f02", linestyle="none", markersize=7, label="OSRM-snapped point"),
            Line2D([0], [0], color="#ef8a36", linewidth=1, label="Snap displacement"),
        ],
        loc="lower left",
        frameon=True,
        framealpha=0.95,
        fontsize=9,
    )
    ax.set_aspect("equal")
    ax.set_axis_off()
    fig.tight_layout()
    image_path = OUTPUT_DIR / "region_points_osrm_snapped.png"
    fig.savefig(image_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    distances = [row["snap_distance_m"] for row in rows]
    print(f"Snapped points inside corresponding geometry: {len(rows)}/{len(rows)}")
    print(f"Nearest candidate (rank 1) used: {len(rows) - nonfirst}/{len(rows)}")
    print(f"Candidates beyond rank 1 used: {nonfirst}/{len(rows)}")
    print(f"Snap distance: min={min(distances):.3f} m; mean={sum(distances)/len(distances):.3f} m; max={max(distances):.3f} m")
    print(f"CSV: {csv_path}")
    print(f"Map: {image_path}")


if __name__ == "__main__":
    main()
