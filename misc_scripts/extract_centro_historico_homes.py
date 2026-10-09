"""Extract and spatially validate Centro Historico home POIs."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from pyproj import CRS, Transformer

from validate_region_points import (
    OUTPUT_DIR,
    SHAPE_DIR,
    normalized_name,
    point_in_rings,
    read_dbf,
    read_polygon_shapefile,
)


ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT = ROOT / "data_input" / "enumeration_area" / "Environment-POA-EnumArea.json"
TARGET_NAME = "Centro Histórico"


def main() -> None:
    with ENVIRONMENT.open(encoding="utf-8") as handle:
        regions = json.load(handle)["regions"]

    target_key = normalized_name(TARGET_NAME)
    region = next(
        item for item in regions if normalized_name(item["name"]) == target_key
    )
    homes = [
        poi for poi in region["points_of_interest"] if poi.get("poi_type") == "home"
    ]

    attributes = read_dbf(SHAPE_DIR / "bairros_vigentes.dbf")
    shapes = read_polygon_shapefile(SHAPE_DIR / "bairros_vigentes.shp")
    geometries_by_name: dict[str, list] = defaultdict(list)
    for name, rings in zip(attributes, shapes):
        geometries_by_name[normalized_name(name["NOME"])].append(rings)
    target_geometries = geometries_by_name[target_key]

    local_crs = CRS.from_wkt((SHAPE_DIR / "bairros_vigentes.prj").read_text())
    to_local = Transformer.from_crs("EPSG:4326", local_crs, always_xy=True)

    output_rows = []
    for poi in homes:
        longitude, latitude = poi["lng_lat"]
        projected_point = to_local.transform(longitude, latitude)
        inside = any(
            point_in_rings(projected_point, rings) for rings in target_geometries
        )
        output_rows.append(
            {
                "enumeration_area": poi["attributes"]["enumeration_area"],
                "unique_name": poi["unique_name"],
                "longitude": longitude,
                "latitude": latitude,
                "within_centro_historico_geometry": inside,
            }
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "centro_historico_home_points.csv"
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)

    inside_count = sum(row["within_centro_historico_geometry"] for row in output_rows)
    distinct_codes = len({row["enumeration_area"] for row in output_rows})
    print(f"Centro Historico home POIs: {len(output_rows)}")
    print(f"Distinct enumeration-area codes: {distinct_codes}")
    print(f"Inside Centro Historico geometry: {inside_count}/{len(output_rows)}")
    print("Outside points:")
    for row in output_rows:
        if not row["within_centro_historico_geometry"]:
            print(
                f"  {row['unique_name']}: {row['longitude']}, {row['latitude']} "
                f"(enumeration area {row['enumeration_area']})"
            )
    print(f"CSV: {output_path}")


if __name__ == "__main__":
    main()
