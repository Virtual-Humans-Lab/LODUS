from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def build_node_dependency_config(
    environment_data: dict[str, Any],
    *,
    region_name_key: str = "name",
    poi_list_key: str = "points_of_interest",
    poi_type_key: str = "poi_type",
    node_name_key: str = "unique_name",
    attributes_key: str = "attributes",
    enum_area_key: str = "enumeration_area",
    water_source_type: str = "water_source",
) -> dict[str, Any]:
    regions = environment_data.get("regions", [])
    if not isinstance(regions, list):
        raise ValueError("environment file must contain a list under 'regions'")

    enum_area_to_water_sources: dict[str, list[str]] = {}
    all_nodes: list[tuple[str, str, str, str | None]] = []

    for region in regions:
        if not isinstance(region, dict):
            raise ValueError("each region must be a mapping")

        region_name = region.get(region_name_key)
        if not isinstance(region_name, str) or not region_name.strip():
            raise ValueError(f"region is missing a valid '{region_name_key}' value")

        pois = region.get(poi_list_key, [])
        if not isinstance(pois, list):
            raise ValueError(f"region '{region_name}' must contain a list under '{poi_list_key}'")

        for poi in pois:
            if not isinstance(poi, dict):
                raise ValueError(f"each point of interest in region '{region_name}' must be a mapping")

            poi_type = poi.get(poi_type_key)
            unique_name = poi.get(node_name_key)
            attributes = poi.get(attributes_key, {})

            if not isinstance(poi_type, str) or not poi_type.strip():
                raise ValueError(f"poi in region '{region_name}' is missing a valid '{poi_type_key}' value")
            if not isinstance(unique_name, str) or not unique_name.strip():
                raise ValueError(f"poi in region '{region_name}' is missing a valid '{node_name_key}' value")
            if not isinstance(attributes, dict):
                raise ValueError(f"poi '{unique_name}' in region '{region_name}' must contain a mapping under '{attributes_key}'")

            enum_area = attributes.get(enum_area_key)
            if enum_area is None:
                raise ValueError(f"poi '{region_name}//{unique_name}' is missing '{enum_area_key}' in attributes")

            complete_name = f"{region_name}//{unique_name}"
            enum_area_str = str(enum_area)
            all_nodes.append((complete_name, poi_type, enum_area_str, unique_name))

            if poi_type == water_source_type:
                enum_area_to_water_sources.setdefault(enum_area_str, []).append(complete_name)

    dependency_rules: dict[str, Any] = {}

    for complete_name, poi_type, enum_area_str, _ in all_nodes:
        if poi_type == water_source_type:
            continue

        water_sources = enum_area_to_water_sources.get(enum_area_str, [])
        if not water_sources:
            raise ValueError(
                f"no '{water_source_type}' node found for enumeration area '{enum_area_str}' "
                f"required by '{complete_name}'"
            )
        if len(water_sources) > 1:
            raise ValueError(
                f"multiple '{water_source_type}' nodes found for enumeration area '{enum_area_str}' "
                f"required by '{complete_name}': {water_sources}"
            )

        dependency_rules[complete_name] = {"all_of": water_sources}

    return {"node_dependencies": dict(sorted(dependency_rules.items()))}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a node dependency JSON file from an environment JSON file."
    )
    parser.add_argument("environment_file", type=Path, help="Path to the environment JSON file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Path to write the dependency JSON file. Defaults to <environment_stem>.node_dependencies.json next to the input file.",
    )
    parser.add_argument("--water-source-type", default="water_source", help="POI type that marks a water source")
    parser.add_argument("--region-name-key", default="name", help="Region field that contains the region name")
    parser.add_argument(
        "--poi-list-key",
        default="points_of_interest",
        help="Region field that contains the POI list",
    )
    parser.add_argument("--poi-type-key", default="poi_type", help="POI field that contains the type")
    parser.add_argument("--node-name-key", default="unique_name", help="POI field that contains the node name")
    parser.add_argument(
        "--attributes-key",
        default="attributes",
        help="POI field that contains the attributes mapping",
    )
    parser.add_argument(
        "--enum-area-key",
        default="enumeration_area",
        help="Attribute key that stores the enumeration area identifier",
    )
    args = parser.parse_args()

    input_path: Path = args.environment_file
    output_path: Path = args.output or input_path.with_name(f"{input_path.stem}.node_dependencies.json")

    with input_path.open("r", encoding="utf-8-sig") as file_handle:
        environment_data = json.load(file_handle)

    dependency_data = build_node_dependency_config(
        environment_data,
        region_name_key=args.region_name_key,
        poi_list_key=args.poi_list_key,
        poi_type_key=args.poi_type_key,
        node_name_key=args.node_name_key,
        attributes_key=args.attributes_key,
        enum_area_key=args.enum_area_key,
        water_source_type=args.water_source_type,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file_handle:
        json.dump(dependency_data, file_handle, indent=2, ensure_ascii=False)
        file_handle.write("\n")

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()

# Example usage:
# python misc_scripts/generate_node_dependency_file.py path/to/environment.json -o path/to/node_dependencies.json --water-source-type water_source --region-name-key name --poi-list-key points_of_interest --poi-type-key poi_type --node-name-key unique_name --attributes-key attributes --enum-area-key enumeration_area
# python.exe .\misc_scripts\generate_node_dependency_file.py .\data_input\enumeration_area\Environment-13-EnumArea.json
# python.exe .\misc_scripts\generate_node_dependency_file.py .\data_input\enumeration_area\Environment-13-EnumArea.json -o .\data_input\enumeration_area\dependency_rules\Env13-Dependency.json