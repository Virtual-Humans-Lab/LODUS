from __future__ import annotations

import argparse
import json
import math
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import shapefile
from pyproj import CRS, Transformer


REQUIRED_STATE_COLUMNS = {
    "Simulation Step",
    "Cycle Step",
    "Cycle",
    "Region",
    "Node",
    "Unique Name",
    "Node Type",
    "Longitude",
    "Latitude",
    "Enumeration Area",
    "Enabled",
}
REQUIRED_WATER_COLUMNS = {
    "Simulation Step",
    "Cycle Step",
    "Cycle",
    "Water Level",
}
CORE_NODE_TYPES = ("home", "pharmacy", "marketplace", "restaurant")
LEVY_NODE_TYPES = ("work", "school")
FLOOD_MODES = ("none", "homes", "pois", "both")


@dataclass(frozen=True)
class RunInfo:
    root: Path
    metadata: dict[str, Any]
    environment: str
    levy: bool
    flood: str
    seed: int

    @property
    def state_path(self) -> Path:
        return self.root / "data_frames" / "envnode_state.csv"

    @property
    def water_path(self) -> Path:
        return self.root / "data_frames" / "water_level_step.csv"

    @property
    def scenario_name(self) -> str:
        return scenario_name(self.environment, self.levy, self.flood)


def scenario_name(environment: str, levy: bool, flood: str) -> str:
    return f"{environment}_levy_{'on' if levy else 'off'}_flood_{flood}"


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    return "".join(char for char in text if unicodedata.category(char) != "Mn").casefold().strip()


def normalize_area(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf8"))


def study_from_metadata(metadata: dict[str, Any]) -> tuple[str, bool, str]:
    config = metadata.get("resolved_config", {})
    study = config.get("popular_times_v2_study", {})
    environment = str(study.get("environment", "unknown"))
    levy = bool(study.get("levy", "levy_walk_plugin" in config))
    flood = str(study.get("flood", "")).casefold()
    if flood not in FLOOD_MODES:
        targets = set(config.get("water_level_data_plugin", {}).get("target_node_types", []))
        poi_targets = {"pharmacy", "marketplace", "restaurant"}
        has_homes = "home" in targets
        has_pois = bool(targets & poi_targets)
        if has_homes and has_pois:
            flood = "both"
        elif has_homes:
            flood = "homes"
        elif has_pois:
            flood = "pois"
        else:
            flood = "none"
    return environment, levy, flood


def discover_scenarios(scenario_root: Path, environment: str = "13") -> dict[str, list[RunInfo]]:
    groups: dict[str, list[RunInfo]] = {}
    for metadata_path in sorted(scenario_root.glob("*/run_metadata.json")):
        metadata = read_json(metadata_path)
        if metadata.get("status") != "complete":
            continue
        run_environment, levy, flood = study_from_metadata(metadata)
        if run_environment != str(environment) or flood not in FLOOD_MODES:
            continue
        seed = int(metadata.get("seed", metadata.get("numpy_seed", 0)))
        info = RunInfo(metadata_path.parent, metadata, run_environment, levy, flood, seed)
        groups.setdefault(info.scenario_name, []).append(info)

    expected = {
        scenario_name(str(environment), levy, flood)
        for levy in (False, True)
        for flood in FLOOD_MODES
    }
    missing = sorted(expected - set(groups))
    unexpected = sorted(set(groups) - expected)
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected: {', '.join(unexpected)}")
        raise ValueError("Scenario discovery did not produce the expected matrix (" + "; ".join(details) + ")")

    for runs in groups.values():
        runs.sort(key=lambda run: (run.seed != 0, run.seed, str(run.root)))
    return dict(sorted(groups.items()))


def choose_canonical_run(runs: Iterable[RunInfo]) -> RunInfo:
    candidates = sorted(runs, key=lambda run: (run.seed != 0, run.seed, str(run.root)))
    if not candidates:
        raise ValueError("Cannot choose a representative run from an empty scenario.")
    return candidates[0]


def visible_node_types(levy: bool, override: Iterable[str] | None = None) -> tuple[str, ...]:
    if override:
        values = []
        for value in override:
            normalized = str(value).strip()
            if normalized and normalized not in {"p8", "p9"} and normalized not in values:
                values.append(normalized)
        if not values:
            raise ValueError("--node-types did not contain any displayable node types.")
        return tuple(values)
    return CORE_NODE_TYPES + (LEVY_NODE_TYPES if levy else ())


def load_state_log(path: Path, node_types: Iterable[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"State log not found: {path}")
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig")
    missing = sorted(REQUIRED_STATE_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(f"State log is missing required columns: {', '.join(missing)}")
    if df.empty:
        raise ValueError(f"State log is empty: {path}")

    for column in ("Simulation Step", "Cycle Step", "Cycle", "Enabled"):
        df[column] = pd.to_numeric(df[column], errors="raise").astype(int)
    for column in ("Longitude", "Latitude"):
        df[column] = pd.to_numeric(df[column], errors="raise")
    if not df["Longitude"].map(math.isfinite).all() or not df["Latitude"].map(math.isfinite).all():
        raise ValueError(f"State log contains non-finite coordinates: {path}")
    df["Node Type"] = df["Node Type"].fillna("Unknown").astype(str).str.strip()
    df["Node"] = df["Node"].astype(str)

    if node_types is not None:
        df = df[df["Node Type"].isin(set(node_types))].copy()
    if df.empty:
        raise ValueError("No state rows remain after applying the node-type filter.")
    return df.sort_values(["Simulation Step", "Node"], kind="stable").reset_index(drop=True)


def load_water_log(path: Path, flood: str, total_steps: int | None = None) -> pd.DataFrame:
    if not path.exists():
        if flood == "none":
            return pd.DataFrame(columns=sorted(REQUIRED_WATER_COLUMNS))
        raise FileNotFoundError(f"Flood scenario is missing its water-level log: {path}")
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig")
    missing = sorted(REQUIRED_WATER_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(f"Water-level log is missing required columns: {', '.join(missing)}")
    if df.empty:
        if flood == "none":
            return df
        raise ValueError(f"Flood scenario has an empty water-level log: {path}")

    for column in ("Simulation Step", "Cycle Step", "Cycle"):
        df[column] = pd.to_numeric(df[column], errors="raise").astype(int)
    df["Water Level"] = pd.to_numeric(df["Water Level"], errors="raise")
    if df["Simulation Step"].duplicated().any():
        raise ValueError(f"Water-level log contains duplicate simulation steps: {path}")
    df = df.sort_values("Simulation Step", kind="stable").reset_index(drop=True)
    if flood != "none" and total_steps is not None:
        actual = df["Simulation Step"].tolist()
        expected = list(range(total_steps))
        if actual != expected:
            raise ValueError(
                f"Water-level log must cover every step 0..{total_steps - 1}: {path}"
            )
    return df


def total_steps_from_metadata(metadata: dict[str, Any], state_df: pd.DataFrame, water_df: pd.DataFrame) -> int:
    parameters = metadata.get("simulation_parameters", {})
    if not parameters:
        parameters = metadata.get("resolved_config", {}).get("simulation_parameters", {})
    total_cycles = parameters.get("total_cycles")
    cycle_length = parameters.get("cycle_length")
    if total_cycles is not None and cycle_length is not None:
        total_steps = int(total_cycles) * int(cycle_length)
        if total_steps > 0:
            return total_steps
    maxima = [int(state_df["Simulation Step"].max())]
    if not water_df.empty:
        maxima.append(int(water_df["Simulation Step"].max()))
    return max(maxima) + 1


def cycle_length_from_metadata(metadata: dict[str, Any]) -> int:
    parameters = metadata.get("simulation_parameters", {})
    if not parameters:
        parameters = metadata.get("resolved_config", {}).get("simulation_parameters", {})
    return int(parameters.get("cycle_length", 24))


def normalized_state_timeline(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["Simulation Step", "Node", "Enabled", "Longitude", "Latitude", "Node Type"]
    result = df[columns].copy()
    result["Longitude"] = result["Longitude"].round(12)
    result["Latitude"] = result["Latitude"].round(12)
    return result.sort_values(["Simulation Step", "Node"], kind="stable").reset_index(drop=True)


def normalized_water_timeline(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Simulation Step", "Water Level"])
    result = df[["Simulation Step", "Water Level"]].copy()
    result["Water Level"] = result["Water Level"].round(12)
    return result.sort_values("Simulation Step", kind="stable").reset_index(drop=True)


def verify_seed_invariance(
    runs: list[RunInfo], node_types: Iterable[str]
) -> tuple[RunInfo, pd.DataFrame, pd.DataFrame, int]:
    canonical = choose_canonical_run(runs)
    canonical_state = load_state_log(canonical.state_path, node_types)
    preliminary_water = load_water_log(canonical.water_path, canonical.flood)
    total_steps = total_steps_from_metadata(canonical.metadata, canonical_state, preliminary_water)
    canonical_water = load_water_log(canonical.water_path, canonical.flood, total_steps)
    expected_state = normalized_state_timeline(canonical_state)
    expected_water = normalized_water_timeline(canonical_water)

    for run in runs:
        if run.root == canonical.root:
            continue
        state = load_state_log(run.state_path, node_types)
        preliminary = load_water_log(run.water_path, run.flood)
        run_steps = total_steps_from_metadata(run.metadata, state, preliminary)
        water = load_water_log(run.water_path, run.flood, run_steps)
        if run_steps != total_steps:
            raise ValueError(
                f"Seed invariance failed for {canonical.scenario_name}: seed {run.seed} has "
                f"{run_steps} steps; representative seed {canonical.seed} has {total_steps}."
            )
        if not normalized_state_timeline(state).equals(expected_state):
            raise ValueError(
                f"Seed invariance failed for {canonical.scenario_name}: node-state timeline "
                f"differs between seed {canonical.seed} and seed {run.seed}."
            )
        if not normalized_water_timeline(water).equals(expected_water):
            raise ValueError(
                f"Seed invariance failed for {canonical.scenario_name}: water-level timeline "
                f"differs between seed {canonical.seed} and seed {run.seed}."
            )
    return canonical, canonical_state, canonical_water, total_steps


def find_shapefile(folder: Path) -> Path:
    matches = sorted(folder.glob("*.shp"))
    if not matches:
        raise FileNotFoundError(f"No .shp file found in {folder}")
    return matches[0]


def shapefile_transformer(shp_path: Path) -> Transformer:
    prj_path = shp_path.with_suffix(".prj")
    if not prj_path.exists():
        raise FileNotFoundError(f"Missing .prj file for {shp_path}")
    source_crs = CRS.from_wkt(prj_path.read_text(encoding="utf-8"))
    return Transformer.from_crs(source_crs, CRS.from_epsg(4326), always_xy=True)


def geometry_lines(shp_path: Path, field_name: str, accepted: set[str]) -> dict[str, list[Any]]:
    reader = shapefile.Reader(str(shp_path))
    transformer = shapefile_transformer(shp_path)
    field_names = [field[0] for field in reader.fields[1:]]
    if field_name not in field_names:
        raise ValueError(f"Shapefile {shp_path} does not contain field {field_name}.")
    field_index = field_names.index(field_name)
    lon_values: list[Any] = []
    lat_values: list[Any] = []

    for shape_record in reader.iterShapeRecords():
        record_value = shape_record.record[field_index]
        lookup = normalize_area(record_value) if field_name == "CD_SETOR" else normalize_text(record_value)
        if lookup not in accepted:
            continue
        points = shape_record.shape.points
        parts = list(shape_record.shape.parts) + [len(points)]
        for index in range(len(parts) - 1):
            ring = points[parts[index] : parts[index + 1]]
            for x, y in ring:
                lon, lat = transformer.transform(x, y)
                lon_values.append(round(lon, 7))
                lat_values.append(round(lat, 7))
            lon_values.append(None)
            lat_values.append(None)
    return {"lon": lon_values, "lat": lat_values}


def build_payload(
    state_df: pd.DataFrame,
    water_df: pd.DataFrame,
    metadata: dict[str, Any],
    scenario: str,
    verified_seeds: int,
    total_steps: int,
    spatial_root: Path,
) -> dict[str, Any]:
    cycle_length = cycle_length_from_metadata(metadata)
    initial_step = int(state_df["Simulation Step"].min())
    initial_rows = state_df[state_df["Simulation Step"] == initial_step]
    if initial_step != 0:
        raise ValueError("State log must contain its initial snapshot at simulation step 0.")
    if initial_rows["Node"].duplicated().any():
        raise ValueError("Initial state snapshot contains duplicate node identifiers.")

    nodes: list[dict[str, Any]] = []
    node_index: dict[str, int] = {}
    for _, row in initial_rows.iterrows():
        key = str(row["Node"])
        node_index[key] = len(nodes)
        nodes.append(
            {
                "id": key,
                "name": str(row["Unique Name"]),
                "type": str(row["Node Type"]),
                "region": str(row["Region"]),
                "area": normalize_area(row["Enumeration Area"]),
                "lon": round(float(row["Longitude"]), 12),
                "lat": round(float(row["Latitude"]), 12),
                "enabled": int(row["Enabled"]),
            }
        )

    events: list[list[int]] = []
    for _, row in state_df[state_df["Simulation Step"] > 0].iterrows():
        key = str(row["Node"])
        if key not in node_index:
            raise ValueError(f"State transition references a node missing from the initial snapshot: {key}")
        events.append([int(row["Simulation Step"]), node_index[key], int(row["Enabled"])])

    regions = {normalize_text(node["region"]) for node in nodes}
    areas = {node["area"] for node in nodes if node["area"]}
    bairros_shp = find_shapefile(spatial_root / "bairros_vigentes")
    setores_shp = find_shapefile(spatial_root / "setores_2022")
    region_geometry = geometry_lines(bairros_shp, "NOME", regions)
    sector_geometry = geometry_lines(setores_shp, "CD_SETOR", areas)
    if not region_geometry["lon"]:
        raise ValueError("No neighborhood geometry matched the visible node regions.")
    if not sector_geometry["lon"]:
        raise ValueError("No census-sector geometry matched the visible enumeration areas.")

    environment, levy, flood = study_from_metadata(metadata)
    water = [
        [int(row["Simulation Step"]), float(row["Water Level"])]
        for _, row in water_df.iterrows()
    ]
    return {
        "scenario": scenario,
        "environment": environment,
        "levy": levy,
        "flood": flood,
        "verifiedSeeds": verified_seeds,
        "cycleLength": cycle_length,
        "totalSteps": total_steps,
        "nodes": nodes,
        "events": events,
        "water": water,
        "regionGeometry": region_geometry,
        "sectorGeometry": sector_geometry,
    }


def render_html(payload: dict[str, Any]) -> str:
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return HTML_TEMPLATE.replace("__PAYLOAD__", payload_json)


def write_visualization(
    run: RunInfo,
    state_df: pd.DataFrame,
    water_df: pd.DataFrame,
    total_steps: int,
    verified_seeds: int,
    spatial_root: Path,
    output_html: Path,
) -> None:
    payload = build_payload(
        state_df,
        water_df,
        run.metadata,
        run.scenario_name,
        verified_seeds,
        total_steps,
        spatial_root,
    )
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(render_html(payload), encoding="utf8")


def generate_scenario_visualizations(
    scenario_root: Path,
    output_dir: Path,
    spatial_root: Path,
    environment: str = "13",
    node_type_override: Iterable[str] | None = None,
) -> list[Path]:
    groups = discover_scenarios(scenario_root, environment)
    outputs = []
    for name, runs in groups.items():
        node_types = visible_node_types(runs[0].levy, node_type_override)
        canonical, state_df, water_df, total_steps = verify_seed_invariance(runs, node_types)
        output_html = output_dir / f"{name}.html"
        write_visualization(
            canonical,
            state_df,
            water_df,
            total_steps,
            len(runs),
            spatial_root,
            output_html,
        )
        outputs.append(output_html)
        print(f"Visualization written: {output_html} ({len(runs)} seed(s) verified)")
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Visualize EnvNode enabled/disabled states and flood water levels over time."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--state-log", type=str, help="Path to envnode_state.csv for one run.")
    source.add_argument(
        "--experiment-name",
        type=str,
        help="Run folder under output_logs for one-run debugging.",
    )
    source.add_argument(
        "--scenario-root",
        type=str,
        help="Production output root to generate one visualization per scenario.",
    )
    parser.add_argument(
        "--water-log",
        type=str,
        default="",
        help="Optional water_level_step.csv override in single-run mode.",
    )
    parser.add_argument(
        "--metadata",
        type=str,
        default="",
        help="Optional run_metadata.json override in single-run mode.",
    )
    parser.add_argument(
        "--node-types",
        nargs="+",
        default=None,
        help="Optional visible node types. p8 and p9 are always excluded.",
    )
    parser.add_argument(
        "--environment",
        type=str,
        default="13",
        help="Environment matrix to select in batch mode (default: 13).",
    )
    parser.add_argument(
        "--spatial-root",
        type=str,
        default="data_input/spatial",
        help="Folder containing bairros_vigentes and setores_2022.",
    )
    parser.add_argument(
        "--output-html",
        type=str,
        default="output_logs/envnode_state_visualization.html",
        help="Output path in single-run mode.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output_logs/popular_times_v2_visualizations",
        help="Output directory in scenario batch mode.",
    )
    return parser.parse_args()


def single_run_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    if args.experiment_name:
        root = Path("output_logs") / args.experiment_name
        state_path = root / "data_frames" / "envnode_state.csv"
    else:
        state_path = Path(args.state_log)
        root = state_path.parent.parent if state_path.parent.name == "data_frames" else state_path.parent
    water_path = Path(args.water_log) if args.water_log else root / "data_frames" / "water_level_step.csv"
    metadata_path = Path(args.metadata) if args.metadata else root / "run_metadata.json"
    return state_path, water_path, metadata_path


def main() -> None:
    args = parse_args()
    spatial_root = Path(args.spatial_root)
    if args.scenario_root:
        generate_scenario_visualizations(
            Path(args.scenario_root),
            Path(args.output_dir),
            spatial_root,
            args.environment,
            args.node_types,
        )
        return

    state_path, water_path, metadata_path = single_run_paths(args)
    if metadata_path.exists():
        metadata = read_json(metadata_path)
    else:
        metadata = {"simulation_parameters": {"cycle_length": 24}}
        print(f"Warning: metadata not found; using core Popular Times node types: {metadata_path}")
    environment, levy, flood = study_from_metadata(metadata)
    node_types = visible_node_types(levy, args.node_types)
    state_df = load_state_log(state_path, node_types)
    preliminary_water = load_water_log(water_path, flood)
    total_steps = total_steps_from_metadata(metadata, state_df, preliminary_water)
    water_df = load_water_log(water_path, flood, total_steps)
    root = metadata_path.parent
    run = RunInfo(root, metadata, environment, levy, flood, int(metadata.get("seed", 0)))
    write_visualization(
        run,
        state_df,
        water_df,
        total_steps,
        1,
        spatial_root,
        Path(args.output_html),
    )
    print(f"Visualization written: {args.output_html}")


HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Popular Times flood visualization</title>
  <script src="https://cdn.plot.ly/plotly-3.0.1.min.js"></script>
  <style>
    :root { --ink:#132a2f; --muted:#62777b; --paper:#f5f4ee; --card:#fff; --line:#d9ded8; --enabled:#159d8c; --disabled:#df624d; --water:#277da1; }
    * { box-sizing:border-box; }
    [hidden] { display:none !important; }
    body { margin:0; color:var(--ink); background:var(--paper); font:14px/1.4 Inter,ui-sans-serif,system-ui,-apple-system,sans-serif; }
    main { width:min(1500px,100%); margin:auto; padding:24px; }
    header { display:flex; justify-content:space-between; gap:24px; align-items:end; margin-bottom:18px; }
    .eyebrow { margin:0 0 4px; color:var(--water); font-size:11px; font-weight:800; letter-spacing:.14em; text-transform:uppercase; }
    h1 { margin:0; font:700 clamp(24px,3vw,40px)/1.05 Georgia,serif; }
    .scenario { color:var(--muted); text-align:right; }
    .scenario strong { color:var(--ink); display:block; }
    .stats { display:grid; grid-template-columns:repeat(5,minmax(115px,1fr)); gap:10px; margin-bottom:12px; }
    .stat { padding:12px 14px; border:1px solid var(--line); border-radius:10px; background:var(--card); }
    .stat span { display:block; color:var(--muted); font-size:11px; letter-spacing:.07em; text-transform:uppercase; }
    .stat strong { display:block; margin-top:3px; font-size:20px; }
    .enabled strong { color:var(--enabled); } .disabled strong { color:var(--disabled); }
    .workspace { display:grid; grid-template-columns:minmax(0,2.2fr) minmax(320px,1fr); gap:12px; }
    .card { overflow:hidden; border:1px solid var(--line); border-radius:12px; background:var(--card); box-shadow:0 8px 28px #173a3f0c; }
    .card-head { display:flex; justify-content:space-between; align-items:center; min-height:44px; padding:8px 12px; border-bottom:1px solid var(--line); }
    .card-head b { font-size:13px; }
    .toggles { display:flex; gap:12px; color:var(--muted); font-size:12px; }
    #map { height:650px; }
    #water-chart { height:650px; }
    #no-water { height:650px; display:grid; place-items:center; color:var(--muted); text-align:center; padding:30px; }
    #no-water b { display:block; color:var(--ink); font-size:18px; }
    .controls { display:grid; grid-template-columns:auto auto auto 1fr; gap:8px; align-items:center; margin-top:12px; padding:12px; border:1px solid var(--line); border-radius:12px; background:var(--card); }
    button { min-width:42px; height:34px; border:1px solid var(--line); border-radius:8px; color:var(--ink); background:#fff; cursor:pointer; font-weight:700; }
    button:hover { border-color:#91a5a5; background:#f7faf8; }
    #play { min-width:78px; }
    input[type=range] { width:100%; accent-color:var(--water); }
    footer { display:flex; justify-content:space-between; color:var(--muted); font-size:11px; margin-top:10px; }
    @media (max-width:900px) { main{padding:12px}.workspace{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}#map,#water-chart,#no-water{height:520px}header{align-items:start;flex-direction:column}.scenario{text-align:left}.controls{grid-template-columns:auto auto auto 1fr} }
  </style>
</head>
<body>
<main>
  <header>
    <div><p class="eyebrow">Porto Alegre · Popular Times V2</p><h1>Flood-state simulation</h1></div>
    <div class="scenario"><strong id="scenario-name"></strong><span id="seed-note"></span></div>
  </header>
  <section class="stats">
    <div class="stat"><span>Simulation step</span><strong id="step-value">0</strong></div>
    <div class="stat"><span>Day / hour</span><strong id="time-value">0 / 00:00</strong></div>
    <div class="stat"><span>Water level</span><strong id="water-value">—</strong></div>
    <div class="stat enabled"><span>Enabled nodes</span><strong id="enabled-value">0</strong></div>
    <div class="stat disabled"><span>Disabled nodes</span><strong id="disabled-value">0</strong></div>
  </section>
  <section class="workspace">
    <article class="card">
      <div class="card-head"><b>Node availability map</b><div class="toggles"><label><input id="regions-toggle" type="checkbox" checked> Neighborhoods</label><label><input id="sectors-toggle" type="checkbox"> Census sectors</label></div></div>
      <div id="map"></div>
    </article>
    <article class="card">
      <div class="card-head"><b>Water level over time</b><span class="eyebrow" style="margin:0">Click chart to seek</span></div>
      <div id="water-chart"></div><div id="no-water" hidden><div><b>Flooding disabled</b>No water-level series is recorded for this control scenario.</div></div>
    </article>
  </section>
  <section class="controls">
    <button id="previous" aria-label="Previous step">←</button><button id="play">Play</button><button id="next" aria-label="Next step">→</button>
    <input id="timeline" type="range" min="0" value="0" aria-label="Simulation step">
  </section>
  <footer><span>Enabled = teal · Disabled = red · click legend items to filter node types</span><span>OpenStreetMap tiles and Plotly require internet access</span></footer>
</main>
<script>
const model=__PAYLOAD__;
const enabledColor="#159d8c",disabledColor="#df624d";
const typeSizes={home:7,work:8,school:9,pharmacy:10,marketplace:11,restaurant:12};
const nodeTypes=[...new Set(model.nodes.map(n=>n.type))];
const initialState=Uint8Array.from(model.nodes.map(n=>n.enabled));
let currentState=initialState.slice(),currentStep=0,timer=null;
const map=document.querySelector("#map"),timeline=document.querySelector("#timeline");
timeline.max=String(model.totalSteps-1);
const prettyFlood={none:"No flooding",homes:"Homes flooded",pois:"Popular Times POIs flooded",both:"Homes and POIs flooded"};
document.querySelector("#scenario-name").textContent=`${prettyFlood[model.flood]||model.flood} · Levy ${model.levy?"on":"off"}`;
document.querySelector("#seed-note").textContent=`${model.verifiedSeeds} seed${model.verifiedSeeds===1?"":"s"} verified · seed-independent view`;

const boundaryTraces=[
 {type:"scattermap",mode:"lines",lon:model.regionGeometry.lon,lat:model.regionGeometry.lat,line:{color:"#51666c",width:1.4},name:"Neighborhood boundaries",hoverinfo:"skip",showlegend:false,visible:true},
 {type:"scattermap",mode:"lines",lon:model.sectorGeometry.lon,lat:model.sectorGeometry.lat,line:{color:"#a98658",width:.7},name:"Census-sector boundaries",hoverinfo:"skip",showlegend:false,visible:false}
];
const dynamicKeys=[];
for(const type of nodeTypes) for(const enabled of [true,false]) dynamicKeys.push({type,enabled});
function groupedTraces(){
 return dynamicKeys.map(key=>{
  const lon=[],lat=[],customdata=[];
  model.nodes.forEach((node,index)=>{if(node.type===key.type&&Boolean(currentState[index])===key.enabled){lon.push(node.lon);lat.push(node.lat);customdata.push([node.id,node.region,node.area,key.enabled?"Enabled":"Disabled"]);}});
  return {type:"scattermap",mode:"markers",lon,lat,customdata,marker:{size:typeSizes[key.type]||9,color:key.enabled?enabledColor:disabledColor,opacity:key.enabled ? .83 : .98},name:`${key.enabled?"Enabled":"Disabled"} | ${key.type}`,legendgroup:key.type,hovertemplate:"<b>%{customdata[0]}</b><br>Region: %{customdata[1]}<br>Enumeration area: %{customdata[2]}<br>Status: %{customdata[3]}<extra></extra>"};
 });
}
const center={lat:model.nodes.reduce((s,n)=>s+n.lat,0)/model.nodes.length,lon:model.nodes.reduce((s,n)=>s+n.lon,0)/model.nodes.length};
const mapLayout={margin:{l:0,r:0,t:0,b:0},map:{style:"open-street-map",center,zoom:12.3},legend:{orientation:"h",y:1,x:0,bgcolor:"rgba(255,255,255,.85)"},uirevision:"keep-map-view"};
Plotly.newPlot(map,[...boundaryTraces,...groupedTraces()],mapLayout,{responsive:true,scrollZoom:true,displaylogo:false});

function rebuildState(step){currentState=initialState.slice();for(const event of model.events){if(event[0]>step)break;currentState[event[1]]=event[2];}}
function updateMap(){
 const traces=groupedTraces(),indices=dynamicKeys.map((_,i)=>i+boundaryTraces.length);
 Plotly.restyle(map,{lon:traces.map(t=>t.lon),lat:traces.map(t=>t.lat),customdata:traces.map(t=>t.customdata)},indices);
}
const waterByStep=new Map(model.water);
const waterChart=document.querySelector("#water-chart"),noWater=document.querySelector("#no-water");
if(model.water.length){
 Plotly.newPlot(waterChart,[
  {x:model.water.map(v=>v[0]),y:model.water.map(v=>v[1]),type:"scattergl",mode:"lines",line:{color:"#277da1",width:2},fill:"tozeroy",fillcolor:"rgba(39,125,161,.12)",name:"Water level",hovertemplate:"Step %{x}<br>%{y:.2f} m<extra></extra>"},
  {x:[0],y:[model.water[0][1]],type:"scatter",mode:"markers",marker:{color:"#df624d",size:10},name:"Current step",hoverinfo:"skip"}
 ],{margin:{l:55,r:18,t:20,b:45},xaxis:{title:"Simulation step",range:[0,model.totalSteps-1]},yaxis:{title:"Water level (m)",rangemode:"tozero"},showlegend:false,hovermode:"x unified",uirevision:"water"},{responsive:true,displaylogo:false});
 waterChart.on("plotly_click",event=>{if(event.points.length)seek(Math.round(event.points[0].x));});
}else{waterChart.hidden=true;noWater.hidden=false;}
function updateChart(level){if(!model.water.length)return;Plotly.restyle(waterChart,{x:[[currentStep]],y:[[level]]},[1]);Plotly.relayout(waterChart,{shapes:[{type:"line",x0:currentStep,x1:currentStep,y0:0,y1:1,yref:"paper",line:{color:"#df624d",width:1,dash:"dot"}}]});}
function seek(rawStep){
 currentStep=Math.max(0,Math.min(model.totalSteps-1,Number(rawStep)||0));rebuildState(currentStep);updateMap();timeline.value=String(currentStep);
 const enabled=currentState.reduce((sum,value)=>sum+value,0),level=waterByStep.get(currentStep);
 document.querySelector("#step-value").textContent=currentStep.toLocaleString();
 document.querySelector("#time-value").textContent=`${Math.floor(currentStep/model.cycleLength)} / ${String(currentStep%model.cycleLength).padStart(2,"0")}:00`;
 document.querySelector("#enabled-value").textContent=enabled.toLocaleString();document.querySelector("#disabled-value").textContent=(model.nodes.length-enabled).toLocaleString();
 document.querySelector("#water-value").textContent=level==null?"Disabled":`${level.toFixed(2)} m`;updateChart(level);
}
function stop(){if(timer){clearInterval(timer);timer=null;}document.querySelector("#play").textContent="Play";}
document.querySelector("#play").onclick=()=>{if(timer){stop();return;}document.querySelector("#play").textContent="Pause";timer=setInterval(()=>{if(currentStep>=model.totalSteps-1){stop();return;}seek(currentStep+1);},250);};
document.querySelector("#previous").onclick=()=>{stop();seek(currentStep-1);};document.querySelector("#next").onclick=()=>{stop();seek(currentStep+1);};timeline.oninput=()=>{stop();seek(timeline.value);};
document.querySelector("#regions-toggle").onchange=event=>Plotly.restyle(map,{visible:event.target.checked},[0]);document.querySelector("#sectors-toggle").onchange=event=>Plotly.restyle(map,{visible:event.target.checked},[1]);
seek(0);
</script>
</body>
</html>'''


if __name__ == "__main__":
    main()
