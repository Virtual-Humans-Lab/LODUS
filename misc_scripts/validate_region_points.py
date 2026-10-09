"""Validate the 94 environment coordinates against vigente neighborhood polygons.

This script intentionally uses only the Python standard library, pyproj, and
matplotlib.  It therefore works in the project's current environment without
requiring GeoPandas/Fiona/Shapely.
"""

from __future__ import annotations

import csv
import json
import math
import re
import struct
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pyproj import CRS, Transformer


ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT = ROOT / "data_input" / "Environment-PortoAlegre94RegionsDefault.json"
SHAPE_DIR = ROOT / "data_input" / "spatial" / "bairros_vigentes"
OUTPUT_DIR = ROOT / "docs" / "results" / "spatial_validation"

# The simulation uses historical/common names while the vigente dataset uses
# these current official spellings.
NAME_ALIASES = {
    "passodareia": "passodaareia",
    "saojose": "vilasaojose",
}


def normalized_name(value: str) -> str:
    value = "".join(
        char
        for char in unicodedata.normalize("NFD", value.casefold())
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"[^a-z0-9]", "", value)


def read_dbf(path: Path) -> list[dict[str, str]]:
    with path.open("rb") as handle:
        header = handle.read(32)
        record_count, header_length, record_length = struct.unpack("<IHH", header[4:12])
        descriptor_bytes = handle.read(header_length - 32)

        fields: list[tuple[str, int, int]] = []
        offset = 1  # deletion flag
        for start in range(0, len(descriptor_bytes) - 1, 32):
            descriptor = descriptor_bytes[start : start + 32]
            name = descriptor[:11].split(b"\0", 1)[0].decode("ascii")
            length = descriptor[16]
            fields.append((name, offset, length))
            offset += length

        records = []
        for _ in range(record_count):
            raw = handle.read(record_length)
            if not raw or raw[:1] == b"*":
                continue
            records.append(
                {
                    name: raw[field_offset : field_offset + length]
                    .decode("utf-8", errors="strict")
                    .strip()
                    for name, field_offset, length in fields
                }
            )
    return records


def read_polygon_shapefile(path: Path) -> list[list[list[tuple[float, float]]]]:
    """Return records -> rings -> points for Polygon/PolygonM/PolygonZ shapes."""
    records: list[list[list[tuple[float, float]]]] = []
    with path.open("rb") as handle:
        handle.read(100)
        while True:
            record_header = handle.read(8)
            if not record_header:
                break
            _, content_words = struct.unpack(">2i", record_header)
            content = handle.read(content_words * 2)
            shape_type = struct.unpack_from("<i", content, 0)[0]
            if shape_type == 0:
                records.append([])
                continue
            if shape_type not in (5, 15, 25):
                raise ValueError(f"Unsupported shapefile geometry type: {shape_type}")

            part_count, point_count = struct.unpack_from("<2i", content, 36)
            part_starts = list(struct.unpack_from(f"<{part_count}i", content, 44))
            point_offset = 44 + 4 * part_count
            points = [
                struct.unpack_from("<2d", content, point_offset + 16 * index)
                for index in range(point_count)
            ]
            part_starts.append(point_count)
            records.append(
                [points[part_starts[i] : part_starts[i + 1]] for i in range(part_count)]
            )
    return records


def point_on_segment(point, start, end, tolerance=1e-7) -> bool:
    px, py = point
    ax, ay = start
    bx, by = end
    cross = (px - ax) * (by - ay) - (py - ay) * (bx - ax)
    if abs(cross) > tolerance:
        return False
    return min(ax, bx) - tolerance <= px <= max(ax, bx) + tolerance and min(
        ay, by
    ) - tolerance <= py <= max(ay, by) + tolerance


def point_in_rings(point, rings) -> bool:
    """Even-odd test across all rings; correctly handles holes and multipart records."""
    px, py = point
    inside = False
    for ring in rings:
        if len(ring) < 3:
            continue
        previous = ring[-1]
        for current in ring:
            if point_on_segment(point, previous, current):
                return True
            x1, y1 = previous
            x2, y2 = current
            if (y1 > py) != (y2 > py):
                intersection_x = (x2 - x1) * (py - y1) / (y2 - y1) + x1
                if px < intersection_x:
                    inside = not inside
            previous = current
    return inside


def point_segment_distance(point, start, end) -> float:
    px, py = point
    ax, ay = start
    bx, by = end
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    fraction = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + fraction * dx), py - (ay + fraction * dy))


def distance_to_geometries(point, geometries) -> float:
    return min(
        point_segment_distance(point, ring[index - 1], ring[index])
        for rings in geometries
        for ring in rings
        for index in range(len(ring))
    )


def main() -> None:
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

    source_crs = CRS.from_wkt((SHAPE_DIR / "bairros_vigentes.prj").read_text())
    transformer = Transformer.from_crs("EPSG:4326", source_crs, always_xy=True)

    rows = []
    all_shape_keys = list(geometries_by_name)
    for region in regions:
        longitude, latitude = region["lng_lat"]
        point = transformer.transform(longitude, latitude)
        requested_key = normalized_name(region["name"])
        match_method = "exact"
        if requested_key in geometries_by_name:
            matched_key = requested_key
        elif requested_key in NAME_ALIASES:
            matched_key = NAME_ALIASES[requested_key]
            match_method = "alias"
        else:
            matched_key = max(
                all_shape_keys,
                key=lambda candidate: SequenceMatcher(None, requested_key, candidate).ratio(),
            )
            score = SequenceMatcher(None, requested_key, matched_key).ratio()
            if score < 0.70:
                raise ValueError(f"Could not match neighborhood name: {region['name']!r}")
            match_method = f"fuzzy ({score:.2f})"

        own_geometries = geometries_by_name[matched_key]
        is_inside = any(point_in_rings(point, rings) for rings in own_geometries)
        containing = [
            display_name[key]
            for key, geometries in geometries_by_name.items()
            if any(point_in_rings(point, rings) for rings in geometries)
        ]
        distance = 0.0 if is_inside else distance_to_geometries(point, own_geometries)
        rows.append(
            {
                "region": region["name"],
                "matched_geometry": display_name[matched_key],
                "name_match": match_method,
                "longitude": longitude,
                "latitude": latitude,
                "within_named_geometry": is_inside,
                "containing_geometries": "; ".join(containing),
                "distance_to_named_geometry_m": round(distance, 2),
                "x": point[0],
                "y": point[1],
            }
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_DIR / "region_point_validation.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=[key for key in rows[0] if key not in {"x", "y"}])
        writer.writeheader()
        writer.writerows({key: value for key, value in row.items() if key not in {"x", "y"}} for row in rows)

    fig, ax = plt.subplots(figsize=(12, 12), dpi=180)
    for rings in shapes:
        for ring in rings:
            if not ring:
                continue
            xs, ys = zip(*ring)
            ax.fill(xs, ys, color="#e8edf2", alpha=0.8, zorder=1)
            ax.plot(xs, ys, color="#67727e", linewidth=0.35, zorder=2)

    valid = [row for row in rows if row["within_named_geometry"]]
    invalid = [row for row in rows if not row["within_named_geometry"]]
    ax.scatter(
        [row["x"] for row in valid],
        [row["y"] for row in valid],
        s=22,
        color="#16845b",
        edgecolor="white",
        linewidth=0.5,
        zorder=4,
    )
    ax.scatter(
        [row["x"] for row in invalid],
        [row["y"] for row in invalid],
        s=40,
        marker="X",
        color="#cf3e36",
        edgecolor="white",
        linewidth=0.6,
        zorder=5,
    )
    for row in invalid:
        ax.annotate(
            row["region"],
            (row["x"], row["y"]),
            xytext=(5, 4),
            textcoords="offset points",
            fontsize=6.5,
            color="#84251f",
            zorder=6,
        )

    ax.set_title(
        "Porto Alegre: validation of 94 simulation region points\n"
        f"{len(valid)} inside the corresponding neighborhood geometry; {len(invalid)} outside",
        fontsize=15,
        color="#20252a",
        linespacing=1.45,
        pad=18,
    )
    legend_handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor="#16845b", markeredgecolor="white", markersize=7, label="Inside named neighborhood")
    ]
    if invalid:
        legend_handles.append(
            Line2D([0], [0], marker="X", color="none", markerfacecolor="#cf3e36", markeredgecolor="white", markersize=8, label="Outside named neighborhood")
        )
    ax.legend(
        handles=legend_handles,
        loc="lower left",
        frameon=True,
        framealpha=0.95,
        fontsize=9,
    )
    ax.set_aspect("equal")
    ax.set_axis_off()
    fig.tight_layout()
    image_path = OUTPUT_DIR / "region_points_with_neighborhood_geometries.png"
    fig.savefig(image_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print(f"Environment regions: {len(regions)}")
    print(f"Shapefile records: {len(shapes)}")
    print(f"Unique neighborhood names: {len(geometries_by_name)}")
    print(f"Inside corresponding geometry: {len(valid)}")
    print(f"Outside corresponding geometry: {len(invalid)}")
    print("Non-exact name matches:")
    for row in rows:
        if row["name_match"] != "exact":
            print(
                f"  {row['region']} -> {row['matched_geometry']} "
                f"[{row['name_match']}]"
            )
    print("Outside details:")
    for row in invalid:
        containing = row["containing_geometries"] or "none"
        print(
            f"  {row['region']}: {row['distance_to_named_geometry_m']:.2f} m; "
            f"located in: {containing}"
        )
    print(f"CSV: {csv_path}")
    print(f"Map: {image_path}")


if __name__ == "__main__":
    main()
