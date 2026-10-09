"""Compare a geographic sample of stored region routes with a fresh OSRM table."""

from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT = ROOT / "data_input" / "Environment-PortoAlegre94RegionsDefault.json"
STORED_TABLE = ROOT / "data_input" / "spatial" / "region_table_distances.json"
OUTPUT_DIR = ROOT / "docs" / "results" / "spatial_validation"
OUTPUT_CSV = OUTPUT_DIR / "region_table_sample_validation.csv"
RAW_RESPONSE = OUTPUT_DIR / "region_table_sample_osrm_response.json"
OSRM_BASE_URL = "https://router.project-osrm.org"

SAMPLE_REGIONS = [
    "Aberta dos Morros",
    "Centro Histórico",
    "Sarandi",
    "Restinga",
    "Lomba do Pinheiro",
    "Anchieta",
]


def request_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "LODUS-region-table-sample-validation/1.0"},
    )
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.load(response)
            if payload.get("code") != "Ok":
                raise RuntimeError(f"OSRM returned {payload!r}")
            return payload
        except (urllib.error.URLError, TimeoutError, RuntimeError) as error:
            last_error = error
            if attempt < 3:
                time.sleep(2**attempt)
    raise RuntimeError(f"OSRM request failed: {last_error}")


def main() -> None:
    with ENVIRONMENT.open(encoding="utf-8") as handle:
        environment = json.load(handle)["regions"]
    with STORED_TABLE.open(encoding="utf-8") as handle:
        stored = json.load(handle)

    region_by_name = {region["name"]: region for region in environment}
    coordinates = [region_by_name[name]["lng_lat"] for name in SAMPLE_REGIONS]
    coordinate_string = ";".join(f"{lon:.15g},{lat:.15g}" for lon, lat in coordinates)
    url = (
        f"{OSRM_BASE_URL}/table/v1/driving/{coordinate_string}"
        "?annotations=distance,duration"
    )
    fresh = request_json(url)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_RESPONSE.write_text(
        json.dumps(
            {
                "sample_regions": SAMPLE_REGIONS,
                "input_coordinates": coordinates,
                "response": fresh,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    stored_pairs = {
        (origin, entry["go_to"]): entry["transport"][0]
        for origin, entries in stored.items()
        for entry in entries
    }
    rows = []
    for origin_index, origin in enumerate(SAMPLE_REGIONS):
        for destination_index, destination in enumerate(SAMPLE_REGIONS):
            if origin == destination:
                continue
            current_distance = fresh["distances"][origin_index][destination_index]
            current_duration = fresh["durations"][origin_index][destination_index]
            previous = stored_pairs.get((origin, destination))
            if previous is None:
                rows.append(
                    {
                        "origin": origin,
                        "destination": destination,
                        "stored_distance_m": "",
                        "fresh_distance_m": current_distance,
                        "distance_difference_m": "",
                        "distance_difference_percent": "",
                        "stored_duration_s": "",
                        "fresh_duration_s": current_duration,
                        "duration_difference_s": "",
                        "duration_difference_percent": "",
                        "comparison": "missing_from_stored_table",
                    }
                )
                continue

            distance_difference = current_distance - previous["distance"]
            duration_difference = current_duration - previous["duration"]
            rows.append(
                {
                    "origin": origin,
                    "destination": destination,
                    "stored_distance_m": previous["distance"],
                    "fresh_distance_m": current_distance,
                    "distance_difference_m": round(distance_difference, 3),
                    "distance_difference_percent": round(
                        100 * distance_difference / previous["distance"], 4
                    ),
                    "stored_duration_s": previous["duration"],
                    "fresh_duration_s": current_duration,
                    "duration_difference_s": round(duration_difference, 3),
                    "duration_difference_percent": round(
                        100 * duration_difference / previous["duration"], 4
                    ),
                    "comparison": "available",
                }
            )

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    comparable = [row for row in rows if row["comparison"] == "available"]
    missing = [row for row in rows if row["comparison"] != "available"]
    print(f"Fresh directed routes returned: {len(rows)}/{len(rows)}")
    print(f"Comparable stored pairs: {len(comparable)}")
    print(f"Missing stored pairs (Anchieta): {len(missing)}")
    print(
        "Maximum absolute distance difference: "
        f"{max(abs(row['distance_difference_m']) for row in comparable):.3f} m"
    )
    print(
        "Maximum absolute duration difference: "
        f"{max(abs(row['duration_difference_s']) for row in comparable):.3f} s"
    )
    print(
        "Exact stored/fresh matches: "
        f"{sum(row['distance_difference_m'] == 0 and row['duration_difference_s'] == 0 for row in comparable)}"
        f"/{len(comparable)}"
    )
    print(f"CSV: {OUTPUT_CSV}")
    print(f"Raw response: {RAW_RESPONSE}")


if __name__ == "__main__":
    main()
