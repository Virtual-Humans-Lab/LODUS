from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any


POI_TYPES = ("marketplace", "restaurant", "pharmacy")
LEGACY_OFFSET_REGION_NAMES = {
    "Cel. Aparício Borges": "Coronel Aparício Borges",
    "Jardim Itú": "Jardim Itu",
    "Menino Deus": "Menino-Deus",
    "Mont'Serrat": "Mont’Serrat",
    "Passo D'Areia": "Passo da Areia",
    "São José": "Vila São José",
}
WATER_REGION_ALIASES = {
    legacy_name: canonical_name
    for canonical_name, legacy_name in LEGACY_OFFSET_REGION_NAMES.items()
}
EXPECTED_UNMATCHED_HOMES = {
    "Chapéu do Sol//home_9",
    "Hípica//home_40",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf8"))


def load_water_thresholds(path: Path) -> dict[str, float]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream, delimiter=";")
        if rows.fieldnames != ["node_name", "lat", "long", "wather_lvl"]:
            raise ValueError(f"Unexpected water-threshold columns in {path}")
        thresholds = {}
        for row in rows:
            region_name, node_name = row["node_name"].split("//", 1)
            # This CSV was exported with UTF-8 names interpreted as Mac Roman.
            # Recover those names while accepting already-corrected rows too.
            try:
                region_name = region_name.encode("mac_roman").decode("utf8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
            region_name = WATER_REGION_ALIASES.get(region_name, region_name)
            full_name = f"{region_name}//{node_name}"
            if full_name in thresholds:
                raise ValueError(f"Duplicate water threshold for {full_name}")
            thresholds[full_name] = float(row["wather_lvl"].strip())
    if len(thresholds) != 16266:
        raise ValueError(
            f"Expected 16266 water thresholds in {path}, found {len(thresholds)}"
        )
    return thresholds


def _paired_nodes(environment: dict[str, Any], node_type: str):
    for region in environment["regions"]:
        nodes = {node["unique_name"]: node for node in region["points_of_interest"]}
        for home_name, home in nodes.items():
            if home.get("poi_type") != "home":
                continue
            suffix = home_name.rsplit("_", 1)[-1]
            paired = nodes.get(f"{node_type}_{suffix}")
            if paired is None:
                raise ValueError(
                    f"Missing {node_type} paired with {region['name']}//{home_name}"
                )
            yield home, paired


def collect_empirical_offsets(
    reference_environment: dict[str, Any],
) -> dict[str, list[tuple[float, float]]]:
    offsets: dict[str, list[tuple[float, float]]] = {}
    for node_type in POI_TYPES:
        offsets[node_type] = [
            (
                paired["lng_lat"][0] - home["lng_lat"][0],
                paired["lng_lat"][1] - home["lng_lat"][1],
            )
            for home, paired in _paired_nodes(reference_environment, node_type)
        ]
        if not offsets[node_type]:
            raise ValueError(f"No empirical offsets available for {node_type}")
    return offsets


def _deterministic_offset(
    offsets: list[tuple[float, float]], node_key: str, node_type: str
) -> tuple[float, float]:
    digest = hashlib.sha256(f"{node_key}|{node_type}".encode("utf8")).digest()
    index = int.from_bytes(digest[:8], "big") % len(offsets)
    return offsets[index]


def build_complete_environment(
    source_environment: dict[str, Any],
    empirical_offsets: dict[str, list[tuple[float, float]]],
    water_thresholds: dict[str, float],
) -> dict[str, Any]:
    result = deepcopy(source_environment)
    for region in result["regions"]:
        offset_region_name = LEGACY_OFFSET_REGION_NAMES.get(
            region["name"], region["name"]
        )
        original_nodes = list(region["points_of_interest"])
        existing_names = {node["unique_name"] for node in original_nodes}
        generated_nodes = []
        for home in original_nodes:
            if home.get("poi_type") != "home":
                continue
            suffix = home["unique_name"].rsplit("_", 1)[-1]
            enumeration_area = home.get("attributes", {}).get("enumeration_area")
            for node_type in POI_TYPES:
                unique_name = f"{node_type}_{suffix}"
                if unique_name in existing_names:
                    raise ValueError(
                        f"Generated node already exists: {region['name']}//{unique_name}"
                    )
                dx, dy = _deterministic_offset(
                    empirical_offsets[node_type],
                    f"{offset_region_name}//{home['unique_name']}",
                    node_type,
                )
                attributes = {}
                if enumeration_area is not None:
                    attributes["enumeration_area"] = enumeration_area
                generated_nodes.append(
                    {
                        "poi_type": node_type,
                        "unique_name": unique_name,
                        "lng_lat": [
                            home["lng_lat"][0] + dx,
                            home["lng_lat"][1] + dy,
                        ],
                        "attributes": attributes,
                    }
                )
                existing_names.add(unique_name)
        region["points_of_interest"].extend(generated_nodes)

    generated_names = {
        f"{region['name']}//{node['unique_name']}"
        for region in result["regions"]
        for node in region["points_of_interest"]
    }
    if generated_names != set(water_thresholds):
        missing = sorted(generated_names - set(water_thresholds))
        extra = sorted(set(water_thresholds) - generated_names)
        raise ValueError(
            "Water thresholds do not match the generated environment: "
            f"missing={missing[:5]}, extra={extra[:5]}"
        )
    for region in result["regions"]:
        for node in region["points_of_interest"]:
            node.setdefault("attributes", {})["water_level"] = water_thresholds[
                f"{region['name']}//{node['unique_name']}"
            ]
    return result


def clean_population(
    source_population: dict[str, Any], source_environment: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    environment_homes = {
        f"{region['name']}//{node['unique_name']}"
        for region in source_environment["regions"]
        for node in region["points_of_interest"]
        if node.get("poi_type") == "home"
    }
    initial_population = source_population["initial_population"]
    unmatched = set(initial_population) - environment_homes
    if unmatched != EXPECTED_UNMATCHED_HOMES:
        raise ValueError(
            "Unexpected population/environment mismatch. "
            f"Expected {sorted(EXPECTED_UNMATCHED_HOMES)}, found {sorted(unmatched)}"
        )

    result = deepcopy(source_population)
    exclusions = []
    for key in sorted(unmatched):
        entry = result["initial_population"].pop(key)
        exclusions.append(
            {
                "home": key,
                "population": sum(item["total_population"] for item in entry),
                "reason": "Population entry has no matching environment home node",
            }
        )
    return result, exclusions


def validate_outputs(
    environment: dict[str, Any], population: dict[str, Any]
) -> dict[str, Any]:
    regions = environment["regions"]
    nodes = [node for region in regions for node in region["points_of_interest"]]
    type_counts = Counter(node["poi_type"] for node in nodes)
    homes = {
        f"{region['name']}//{node['unique_name']}"
        for region in regions
        for node in region["points_of_interest"]
        if node["poi_type"] == "home"
    }
    population_homes = set(population["initial_population"])
    complete_names = [
        f"{region['name']}//{node['unique_name']}"
        for region in regions
        for node in region["points_of_interest"]
    ]
    if len(complete_names) != len(set(complete_names)):
        raise ValueError("Generated environment contains duplicate node names")
    for node in nodes:
        coordinates = node.get("lng_lat")
        if (
            not isinstance(coordinates, list)
            or len(coordinates) != 2
            or not all(isinstance(value, (int, float)) for value in coordinates)
        ):
            raise ValueError(f"Invalid generated coordinates for {node['unique_name']}")
    if population_homes != homes:
        raise ValueError(
            "Generated population keys do not match generated environment homes"
        )
    for node_type in POI_TYPES:
        if type_counts[node_type] != type_counts["home"]:
            raise ValueError(f"Incomplete generated POI coverage for {node_type}")

    for region in regions:
        by_name = {node["unique_name"]: node for node in region["points_of_interest"]}
        for node in by_name.values():
            if node["poi_type"] != "home":
                continue
            suffix = node["unique_name"].rsplit("_", 1)[-1]
            for node_type in POI_TYPES:
                if f"{node_type}_{suffix}" not in by_name:
                    raise ValueError(
                        f"Missing generated pair in {region['name']} for home_{suffix}"
                    )

    total_population = sum(
        item["total_population"]
        for entries in population["initial_population"].values()
        for item in entries
    )
    water_threshold_count = sum(
        "water_level" in node.get("attributes", {}) for node in nodes
    )
    if water_threshold_count != len(nodes):
        raise ValueError(
            "Every node in the 94-region output must have a water threshold"
        )
    return {
        "region_count": len(regions),
        "node_count": len(nodes),
        "node_type_counts": dict(sorted(type_counts.items())),
        "population_home_count": len(population_homes),
        "total_population": total_population,
        "pairing_valid": True,
        "water_threshold_count": water_threshold_count,
    }


def build_outputs(data_root: Path):
    enumeration_root = data_root / "enumeration_area"
    reference_environment = _load_json(
        enumeration_root / "Environment-13-EnumArea.json"
    )
    source_environment = _load_json(
        enumeration_root / "Environment-POA-EnumArea.json"
    )
    source_population = _load_json(
        enumeration_root / "Population-POA-EnumArea.json"
    )
    water_threshold_path = (
        enumeration_root / "Environment-POA-EnumArea-WaterLevels_Filled3.csv"
    )
    water_thresholds = load_water_thresholds(water_threshold_path)
    offsets = collect_empirical_offsets(reference_environment)
    environment = build_complete_environment(
        source_environment, offsets, water_thresholds
    )
    population, exclusions = clean_population(source_population, source_environment)
    validation = validate_outputs(environment, population)
    source_population_total = sum(
        item["total_population"]
        for entries in source_population["initial_population"].values()
        for item in entries
    )
    excluded_population_total = sum(item["population"] for item in exclusions)
    audit = {
        "source_environment": "Environment-POA-EnumArea.json",
        "source_population": "Population-POA-EnumArea.json",
        "derived_environment": "Environment-POA-EnumArea-PopularTimes.json",
        "derived_population": "Population-POA-EnumArea-PopularTimes.json",
        "poi_offset_source": "Environment-13-EnumArea.json",
        "poi_offset_method": "SHA-256 deterministic selection from empirical type-specific offset vectors",
        "water_threshold_source": water_threshold_path.name,
        "offset_seed_region_aliases": LEGACY_OFFSET_REGION_NAMES,
        "offset_sample_counts": {
            node_type: len(values) for node_type, values in offsets.items()
        },
        "excluded_population": exclusions,
        "source_population_total": source_population_total,
        "excluded_population_total": excluded_population_total,
        "excluded_population_percent": round(
            100 * excluded_population_total / source_population_total, 6
        ),
        "validation": validation,
    }
    return environment, population, audit


def write_outputs(data_root: Path) -> None:
    environment, population, audit = build_outputs(data_root)
    output_root = data_root / "enumeration_area"
    outputs = {
        output_root / "Environment-POA-EnumArea-PopularTimes.json": environment,
        output_root / "Population-POA-EnumArea-PopularTimes.json": population,
        output_root / "PopularTimes-94-Audit.json": audit,
    }
    for path, data in outputs.items():
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate validated 94-region Popular Times V2 inputs."
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(__file__).parents[1] / "data_input",
    )
    args = parser.parse_args()
    write_outputs(args.data_root)


if __name__ == "__main__":
    main()
