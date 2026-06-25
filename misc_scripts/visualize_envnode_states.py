import argparse
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
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


def find_shapefile(folder: Path) -> Path:
    matches = list(folder.glob("*.shp"))
    if not matches:
        raise FileNotFoundError(f"No .shp file found in {folder}")
    return matches[0]


def shapefile_transformer(shp_path: Path) -> Transformer:
    prj_path = shp_path.with_suffix(".prj")
    if not prj_path.exists():
        raise FileNotFoundError(f"Missing .prj file for {shp_path}")

    source_crs = CRS.from_wkt(prj_path.read_text(encoding="utf-8"))
    target_crs = CRS.from_epsg(4326)
    return Transformer.from_crs(source_crs, target_crs, always_xy=True)


def shapefile_outline_trace(shp_path: Path, name: str, color: str, visible: bool) -> Any:
    reader = shapefile.Reader(str(shp_path))
    transformer = shapefile_transformer(shp_path)
    lon_values = []
    lat_values = []

    for shape in reader.shapes():
        if shape is None:
            continue
        points = shape.points
        parts = list(shape.parts) + [len(points)]
        for i in range(len(parts) - 1):
            ring = points[parts[i] : parts[i + 1]]
            if not ring:
                continue
            for point in ring:
                lon, lat = transformer.transform(point[0], point[1])
                lon_values.append(lon)
                lat_values.append(lat)
            lon_values.append(None)
            lat_values.append(None)

    return go.Scattermap(
        lon=lon_values,
        lat=lat_values,
        mode="lines",
        name=name,
        line=dict(color=color, width=1),
        hoverinfo="skip",
        visible=visible,
    )


def node_trace(df: pd.DataFrame, enabled: bool, name: str, color: str) -> Any:
    state_value = 1 if enabled else 0
    state_df = df[df["Enabled"] == state_value]
    if state_df.empty:
        return go.Scattermap(
            lon=[],
            lat=[],
            mode="markers",
            marker=dict(size=7, color=color),
            name=name,
            hovertemplate="No nodes<extra></extra>",
        )

    hover_text = (
        "Region: "
        + state_df["Region"].astype(str)
        + "<br>Node: "
        + state_df["Node"].astype(str)
        + "<br>Type: "
        + state_df["Node Type"].astype(str)
        + "<br>Enumeration Area: "
        + state_df["Enumeration Area"].astype(str)
    )

    return go.Scattermap(
        lon=state_df["Longitude"],
        lat=state_df["Latitude"],
        mode="markers",
        marker=dict(size=15, color=color),
        name=name,
        text=hover_text,
        hovertemplate="%{text}<extra></extra>",
    )


def validate_state_log(df: pd.DataFrame) -> None:
    missing_columns = sorted(REQUIRED_STATE_COLUMNS - set(df.columns))
    if missing_columns:
        raise ValueError(f"State log is missing required columns: {', '.join(missing_columns)}")


def infer_cycle_length(state_df: pd.DataFrame) -> int | None:
    cycle_rows = state_df[state_df["Cycle"] > 0]
    if cycle_rows.empty:
        return None

    offsets = cycle_rows["Simulation Step"] - cycle_rows["Cycle Step"]
    if not (offsets % cycle_rows["Cycle"] == 0).all():
        raise ValueError("Cannot infer cycle length from inconsistent cycle metadata.")

    candidates = (offsets // cycle_rows["Cycle"]).astype(int)
    first_candidate = int(candidates.iloc[0])
    if not (candidates == first_candidate).all():
        raise ValueError("Cannot infer cycle length from inconsistent cycle metadata.")

    return first_candidate


def node_key_from_row(row: pd.Series) -> str:
    node_name = row.get("Node")
    if pd.notna(node_name) and str(node_name):
        return str(node_name)

    unique_name = row.get("Unique Name")
    if pd.notna(unique_name) and str(unique_name):
        return str(unique_name)
    return str(row["Node"])


def sort_snapshot(snapshot_df: pd.DataFrame) -> pd.DataFrame:
    if snapshot_df.empty:
        return snapshot_df

    sort_column = "Node" if "Node" in snapshot_df.columns else "Unique Name"
    return snapshot_df.sort_values(sort_column, kind="stable").reset_index(drop=True)


def step_title(step: int, step_rows: pd.DataFrame, cycle_length: int | None) -> str:
    if cycle_length is not None:
        return (
            f"EnvNode State Map | Step {step} "
            f"| Cycle {step // cycle_length} | Cycle Step {step % cycle_length}"
        )

    if not step_rows.empty:
        row = step_rows.iloc[0]
        return (
            f"EnvNode State Map | Step {step} "
            f"| Cycle {int(row['Cycle'])} | Cycle Step {int(row['Cycle Step'])}"
        )

    return f"EnvNode State Map | Step {step}"


def load_state_log(state_log_path: Path) -> pd.DataFrame:
    df = pd.read_csv(state_log_path, sep=";")
    validate_state_log(df)
    df["Enabled"] = df["Enabled"].astype(int)
    df["Simulation Step"] = df["Simulation Step"].astype(int)
    df["Cycle"] = df["Cycle"].astype(int)
    df["Cycle Step"] = df["Cycle Step"].astype(int)
    return df


def build_figure(state_df: pd.DataFrame, bairros_shp: Path, setores_shp: Path) -> go.Figure:
    if state_df.empty:
        raise ValueError("State log is empty.")

    sort_columns = ["Simulation Step"]
    if "Node" in state_df.columns:
        sort_columns.append("Node")
    elif "Unique Name" in state_df.columns:
        sort_columns.append("Unique Name")
    state_df = state_df.sort_values(sort_columns, kind="stable").reset_index(drop=True)
    cycle_length = infer_cycle_length(state_df)
    min_step = int(state_df["Simulation Step"].min())
    max_step = int(state_df["Simulation Step"].max())

    step_groups: dict[Any, pd.DataFrame] = {}
    for step, group in state_df.groupby("Simulation Step", sort=True):
        step_groups[step] = group.reset_index(drop=True)

    empty_step_rows = state_df.iloc[0:0]
    steps = range(min_step, max_step + 1)
    current_state: dict[str, dict[str, Any]] = {}
    region_trace = shapefile_outline_trace(
        bairros_shp,
        name="Region geometry (bairros_vigentes)",
        color="#6c757d",
        visible=True,
    )
    sector_trace = shapefile_outline_trace(
        setores_shp,
        name="Sector geometry (setores_2022)",
        color="#8b5e34",
        visible=False,
    )
    frames = []
    slider_steps = []
    initial_snapshot_df: pd.DataFrame | None = None
    initial_step_rows = empty_step_rows

    for step in steps:
        step_rows = step_groups.get(step, empty_step_rows)
        if not step_rows.empty:
            for _, row in step_rows.iterrows():
                row_data: dict[str, Any] = {str(key): value for key, value in row.to_dict().items()}
                current_state[node_key_from_row(row)] = row_data

        snapshot_df = sort_snapshot(pd.DataFrame(current_state.values()))
        if initial_snapshot_df is None:
            initial_snapshot_df = snapshot_df.copy()
            initial_step_rows = step_rows.copy()

        frame_enabled = node_trace(snapshot_df, enabled=True, name="Enabled nodes", color="#2a9d8f")
        frame_disabled = node_trace(snapshot_df, enabled=False, name="Disabled nodes", color="#e76f51")
        frames.append(
            go.Frame(
                name=str(step),
                data=[frame_enabled, frame_disabled],
                traces=[2, 3],
                layout=go.Layout(title=step_title(step, step_rows, cycle_length)),
            )
        )
        slider_steps.append(
            {
                "label": str(step),
                "method": "animate",
                "args": [
                    [str(step)],
                    {
                        "mode": "immediate",
                        "frame": {"duration": 0, "redraw": True},
                        "transition": {"duration": 0},
                    },
                ],
            }
        )

    if initial_snapshot_df is None:
        raise ValueError("Unable to reconstruct an initial state snapshot from the log.")

    enabled_trace = node_trace(initial_snapshot_df, enabled=True, name="Enabled nodes", color="#2a9d8f")
    disabled_trace = node_trace(initial_snapshot_df, enabled=False, name="Disabled nodes", color="#e76f51")
    fig = go.Figure(data=[region_trace, sector_trace, enabled_trace, disabled_trace], frames=frames)

    fig.update_layout(
        title=step_title(min_step, initial_step_rows, cycle_length),
        title_x=0.5,
        margin=dict(l=0, r=0, t=120, b=30),
        legend=dict(orientation="h", yanchor="top", y=1.02, xanchor="left", x=0),
        map=dict(
            style="open-street-map",
            center=dict(lat=-30.04, lon=-51.22),
            zoom=12,
        ),
        uirevision="keep-map-state",
        updatemenus=[
            {
                "type": "buttons",
                "x": 0,
                "y": 1.08,
                "direction": "right",
                "showactive": False,
                "buttons": [
                    {
                        "label": "Play",
                        "method": "animate",
                        "args": [
                            None,
                            {
                                "frame": {"duration": 300, "redraw": True},
                                "transition": {"duration": 0},
                                "fromcurrent": True,
                            },
                        ],
                    },
                    {
                        "label": "Pause",
                        "method": "animate",
                        "args": [[None], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}}],
                    },
                ],
            },
            {
                "type": "buttons",
                "x": 0.23,
                "y": 1.08,
                "direction": "right",
                "showactive": True,
                "buttons": [
                    {
                        "label": "Region level",
                        "method": "update",
                        "args": [{"visible": [True, False, True, True]}],
                    },
                    {
                        "label": "Sector level",
                        "method": "update",
                        "args": [{"visible": [False, True, True, True]}],
                    },
                ],
            },
            {
                "type": "buttons",
                "x": 0.58,
                "y": 1.08,
                "direction": "right",
                "showactive": True,
                "buttons": [
                    {
                        "label": "Map on",
                        "method": "relayout",
                        "args": [{"map.style": "open-street-map"}],
                    },
                    {
                        "label": "Map off",
                        "method": "relayout",
                        "args": [{"map.style": "white-bg"}],
                    },
                ],
            },
        ],
        sliders=[
            {
                "currentvalue": {"prefix": "Simulation Step: "},
                "x": 0,
                "y": 0,
                "len": 1.0,
                "steps": slider_steps,
            }
        ],
    )

    return fig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Visualize EnvNode enabled/disabled states over time with a geometry toggle "
            "for bairros_vigentes (region) and setores_2022 (sector)."
        )
    )
    parser.add_argument(
        "--state-log",
        type=str,
        default="",
        help="Path to envnode_state.csv. If empty, --experiment-name is used.",
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        default="",
        help="Experiment output folder name under output_logs used to locate envnode_state.csv.",
    )
    parser.add_argument(
        "--spatial-root",
        type=str,
        default="data_input/spatial",
        help="Path to the folder containing bairros_vigentes and setores_2022.",
    )
    parser.add_argument(
        "--output-html",
        type=str,
        default="output_logs/envnode_state_visualization.html",
        help="Path of the generated interactive HTML file.",
    )
    return parser.parse_args()


def resolve_state_log_path(args: argparse.Namespace) -> Path:
    if args.state_log:
        return Path(args.state_log)
    if args.experiment_name:
        return Path("output_logs") / args.experiment_name / "data_frames" / "envnode_state.csv"
    raise ValueError("Either --state-log or --experiment-name must be provided.")


def main():
    args = parse_args()
    state_log_path = resolve_state_log_path(args)
    if not state_log_path.exists():
        raise FileNotFoundError(f"State log not found: {state_log_path}")

    spatial_root = Path(args.spatial_root)
    bairros_shp = find_shapefile(spatial_root / "bairros_vigentes")
    setores_shp = find_shapefile(spatial_root / "setores_2022")

    state_df = load_state_log(state_log_path)
    fig = build_figure(state_df, bairros_shp, setores_shp)

    output_html = Path(args.output_html)
    output_html.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_html), include_plotlyjs="cdn", config={"scrollZoom": True})
    print(f"Visualization written to: {output_html}")


if __name__ == "__main__":
    main()
