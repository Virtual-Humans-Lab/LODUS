"""Get bidirectional OSRM distances between Centro Historico homes and its hub."""

from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT = ROOT / "data_input" / "enumeration_area" / "Environment-POA-EnumArea.json"
OUTPUT_DIR = ROOT / "docs" / "results" / "spatial_validation"
OUTPUT_CSV = OUTPUT_DIR / "centro_historico_home_region_osrm_table.csv"
RAW_RESPONSES = OUTPUT_DIR / "centro_historico_osrm_table_responses.json"
OSRM_BASE_URL = "https://router.project-osrm.org"
TARGET_REGION = "Centro Histórico"


def request_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "LODUS-centro-historico-table/1.0"},
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
        regions = json.load(handle)["regions"]

    region = next(item for item in regions if item["name"] == TARGET_REGION)
    homes = [
        poi for poi in region["points_of_interest"] if poi.get("poi_type") == "home"
    ]
    if len(homes) != 95:
        raise ValueError(f"Expected 95 Centro Historico homes, found {len(homes)}")

    # Home indexes are 0..94; the region hub is index 95.
    coordinates = [poi["lng_lat"] for poi in homes] + [region["lng_lat"]]
    coordinate_string = ";".join(f"{lon:.15g},{lat:.15g}" for lon, lat in coordinates)
    home_indexes = ";".join(str(index) for index in range(len(homes)))
    hub_index = len(homes)

    base = f"{OSRM_BASE_URL}/table/v1/driving/{coordinate_string}"
    inbound_url = (
        f"{base}?sources={home_indexes}&destinations={hub_index}"
        "&annotations=distance,duration"
    )
    outbound_url = (
        f"{base}?sources={hub_index}&destinations={home_indexes}"
        "&annotations=distance,duration"
    )

    print("Requesting 95 homes -> region coordinate", flush=True)
    inbound = request_json(inbound_url)
    print("Requesting region coordinate -> 95 homes", flush=True)
    outbound = request_json(outbound_url)

    raw = {
        "profile": "driving",
        "region": TARGET_REGION,
        "region_input_coordinate": region["lng_lat"],
        "home_count": len(homes),
        "inbound": inbound,
        "outbound": outbound,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_RESPONSES.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    rows = []
    for index, home in enumerate(homes):
        home_lon, home_lat = home["lng_lat"]
        rows.append(
            {
                "enumeration_area": home["attributes"]["enumeration_area"],
                "home_unique_name": home["unique_name"],
                "home_longitude": home_lon,
                "home_latitude": home_lat,
                "region": TARGET_REGION,
                "region_longitude": region["lng_lat"][0],
                "region_latitude": region["lng_lat"][1],
                "home_to_region_distance_m": inbound["distances"][index][0],
                "home_to_region_duration_s": inbound["durations"][index][0],
                "region_to_home_distance_m": outbound["distances"][0][index],
                "region_to_home_duration_s": outbound["durations"][0][index],
            }
        )

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    missing_inbound = sum(
        row["home_to_region_distance_m"] is None
        or row["home_to_region_duration_s"] is None
        for row in rows
    )
    missing_outbound = sum(
        row["region_to_home_distance_m"] is None
        or row["region_to_home_duration_s"] is None
        for row in rows
    )
    print(f"Rows written: {len(rows)}")
    print(f"Missing home -> region routes: {missing_inbound}")
    print(f"Missing region -> home routes: {missing_outbound}")
    print(f"CSV: {OUTPUT_CSV}")
    print(f"Raw responses: {RAW_RESPONSES}")


if __name__ == "__main__":
    main()
