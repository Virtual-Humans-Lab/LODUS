"""Download full OSRM route geometries for Centro Historico home/hub pairs."""

from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "results" / "spatial_validation"
TABLE_CSV = OUTPUT_DIR / "centro_historico_home_region_osrm_table.csv"
ROUTES_GEOJSON = OUTPUT_DIR / "centro_historico_routes.geojson"
RAW_RESPONSES = OUTPUT_DIR / "centro_historico_route_responses.json"
OSRM_BASE_URL = "https://router.project-osrm.org"
REQUEST_INTERVAL_SECONDS = 1.05


def request_route(start_lon: float, start_lat: float, end_lon: float, end_lat: float) -> dict:
    coordinates = f"{start_lon:.15g},{start_lat:.15g};{end_lon:.15g},{end_lat:.15g}"
    url = (
        f"{OSRM_BASE_URL}/route/v1/driving/{coordinates}"
        "?alternatives=false&steps=false&overview=full&geometries=geojson"
    )
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "LODUS-centro-historico-routes/1.0"},
    )
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.load(response)
            if payload.get("code") != "Ok" or not payload.get("routes"):
                raise RuntimeError(f"OSRM returned {payload!r}")
            return payload
        except (urllib.error.URLError, TimeoutError, RuntimeError) as error:
            last_error = error
            if attempt < 3:
                time.sleep(2**attempt)
    raise RuntimeError(f"OSRM route request failed: {last_error}")


def save_cache(cache: dict) -> None:
    RAW_RESPONSES.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    if not TABLE_CSV.exists():
        raise FileNotFoundError(
            f"Run get_centro_historico_osrm_table.py first: {TABLE_CSV}"
        )
    with TABLE_CSV.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 95:
        raise ValueError(f"Expected 95 table rows, found {len(rows)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cache = (
        json.loads(RAW_RESPONSES.read_text(encoding="utf-8"))
        if RAW_RESPONSES.exists()
        else {}
    )

    jobs = []
    for row in rows:
        area = row["enumeration_area"]
        jobs.extend(
            [
                (
                    f"{area}_home_to_region",
                    "home_to_region",
                    float(row["home_longitude"]),
                    float(row["home_latitude"]),
                    float(row["region_longitude"]),
                    float(row["region_latitude"]),
                ),
                (
                    f"{area}_region_to_home",
                    "region_to_home",
                    float(row["region_longitude"]),
                    float(row["region_latitude"]),
                    float(row["home_longitude"]),
                    float(row["home_latitude"]),
                ),
            ]
        )

    for index, (route_id, direction, start_lon, start_lat, end_lon, end_lat) in enumerate(
        jobs, start=1
    ):
        if route_id in cache:
            print(f"Cached {index}/{len(jobs)}: {route_id}", flush=True)
            continue
        cache[route_id] = {
            "direction": direction,
            "input_start": [start_lon, start_lat],
            "input_end": [end_lon, end_lat],
            "response": request_route(start_lon, start_lat, end_lon, end_lat),
        }
        save_cache(cache)
        print(f"Queried {index}/{len(jobs)}: {route_id}", flush=True)
        if index < len(jobs):
            time.sleep(REQUEST_INTERVAL_SECONDS)

    features = []
    for row in rows:
        area = row["enumeration_area"]
        inbound_id = f"{area}_home_to_region"
        outbound_id = f"{area}_region_to_home"
        row["home_to_region_route_id"] = inbound_id
        row["region_to_home_route_id"] = outbound_id

        for route_id in (inbound_id, outbound_id):
            cached = cache[route_id]
            route = cached["response"]["routes"][0]
            features.append(
                {
                    "type": "Feature",
                    "id": route_id,
                    "properties": {
                        "route_id": route_id,
                        "enumeration_area": area,
                        "home_unique_name": row["home_unique_name"],
                        "direction": cached["direction"],
                        "distance_m": route["distance"],
                        "duration_s": route["duration"],
                        "weight": route.get("weight"),
                        "weight_name": route.get("weight_name"),
                    },
                    "geometry": route["geometry"],
                }
            )

    fieldnames = list(rows[0])
    with TABLE_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    feature_collection = {
        "type": "FeatureCollection",
        "name": "Centro Historico bidirectional OSRM routes",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }
    ROUTES_GEOJSON.write_text(
        json.dumps(feature_collection, ensure_ascii=False), encoding="utf-8"
    )

    max_distance_delta = 0.0
    max_duration_delta = 0.0
    for row in rows:
        area = row["enumeration_area"]
        inbound = cache[f"{area}_home_to_region"]["response"]["routes"][0]
        outbound = cache[f"{area}_region_to_home"]["response"]["routes"][0]
        max_distance_delta = max(
            max_distance_delta,
            abs(float(row["home_to_region_distance_m"]) - inbound["distance"]),
            abs(float(row["region_to_home_distance_m"]) - outbound["distance"]),
        )
        max_duration_delta = max(
            max_duration_delta,
            abs(float(row["home_to_region_duration_s"]) - inbound["duration"]),
            abs(float(row["region_to_home_duration_s"]) - outbound["duration"]),
        )

    print(f"Route features written: {len(features)}")
    print(f"Maximum Table/Route distance difference: {max_distance_delta:.3f} m")
    print(f"Maximum Table/Route duration difference: {max_duration_delta:.3f} s")
    print(f"Updated CSV: {TABLE_CSV}")
    print(f"GeoJSON: {ROUTES_GEOJSON}")
    print(f"Raw responses: {RAW_RESPONSES}")


if __name__ == "__main__":
    main()
