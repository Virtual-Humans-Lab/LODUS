"""Generate dialysis visualizations from an experiment output folder."""

from __future__ import annotations

import argparse
from importlib.util import find_spec
from math import log2
from pathlib import Path
from struct import unpack

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pyproj import CRS, Transformer


DATA_FILES = {
    "events": "dialysis_events.csv",
    "steps": "dialysis_step.csv",
    "clinics": "dialysis_clinic_step.csv",
    "cycles": "dialysis_cycle.csv",
    "flows": "dialysis_origin_clinic.csv",
}
LOCATION_FILE = "dialysis_locations.csv"


class DialysisVisualizationGenerator:
    """Reads dialysis result tables and writes their Plotly visualizations."""

    def __init__(self, experiment_path: Path | str, export_png: bool = True):
        self.experiment_path = Path(experiment_path)
        self.data_path = self.experiment_path / "data_frames"
        self.html_path = self.experiment_path / "html_plots" / "dialysis"
        self.figures_path = self.experiment_path / "figures" / "dialysis"
        self.export_png = export_png
        self._png_available = export_png and find_spec("kaleido") is not None

    def _read_data(self) -> dict[str, pd.DataFrame]:
        missing = [
            filename
            for filename in DATA_FILES.values()
            if not (self.data_path / filename).is_file()
        ]
        if missing:
            raise FileNotFoundError(
                "Missing dialysis result files in "
                f"{self.data_path}: {', '.join(missing)}"
            )
        frames = {
            name: pd.read_csv(
                self.data_path / filename,
                sep=";",
                encoding="utf-8-sig",
            )
            for name, filename in DATA_FILES.items()
        }
        location_path = self.data_path / LOCATION_FILE
        frames["locations"] = (
            pd.read_csv(
                location_path,
                sep=";",
                encoding="utf-8-sig",
            )
            if location_path.is_file()
            else pd.DataFrame()
        )
        optional_files = {
            "node_states": "envnode_state.csv",
            "water_levels": "water_level_step.csv",
        }
        for name, filename in optional_files.items():
            path = self.data_path / filename
            frames[name] = (
                pd.read_csv(
                    path,
                    sep=";",
                    encoding="utf-8-sig",
                )
                if path.is_file()
                else pd.DataFrame()
            )
        return frames

    def _write(self, figure, filename: str):
        self.html_path.mkdir(parents=True, exist_ok=True)
        figure.write_html(
            self.html_path / f"{filename}.html",
            include_plotlyjs=True,
        )
        if self._png_available:
            self.figures_path.mkdir(parents=True, exist_ok=True)
            try:
                figure.write_image(self.figures_path / f"{filename}.png")
            except Exception:
                self._png_available = False

    @staticmethod
    def _empty(title: str):
        figure = go.Figure()
        figure.update_layout(title=title)
        figure.add_annotation(
            text="No dialysis data recorded",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
        )
        return figure

    @staticmethod
    def _clinic_labels(locations: pd.DataFrame) -> dict[str, str]:
        required = {"Complete Name", "Display Name", "Is Clinic"}
        if locations.empty or not required.issubset(locations.columns):
            return {}
        clinics = locations[locations["Is Clinic"].astype(bool)]
        return dict(zip(clinics["Complete Name"], clinics["Display Name"]))

    @staticmethod
    def _coordinates(locations: pd.DataFrame) -> dict[str, list[float]]:
        required = {"Complete Name", "Longitude", "Latitude"}
        if locations.empty or not required.issubset(locations.columns):
            return {}
        valid = locations.dropna(subset=["Longitude", "Latitude"])
        return {
            row["Complete Name"]: [row["Longitude"], row["Latitude"]]
            for _, row in valid.iterrows()
            if -180 <= row["Longitude"] <= 180
            and -90 <= row["Latitude"] <= 90
        }

    @staticmethod
    def _neighborhood_layer():
        boundary_path = (
            Path(__file__).resolve().parents[3]
            / "data_input"
            / "spatial"
            / "bairros_vigentes"
            / "bairros_vigentes.shp"
        )
        projection_path = boundary_path.with_suffix(".prj")
        if not boundary_path.exists() or not projection_path.exists():
            return None
        transformer = Transformer.from_crs(
            CRS.from_wkt(projection_path.read_text(encoding="utf-8")),
            "EPSG:4326",
            always_xy=True,
        )
        rings = []
        with boundary_path.open("rb") as shapefile:
            shapefile.seek(100)
            while record_header := shapefile.read(8):
                if len(record_header) < 8:
                    break
                record_length = unpack(">2i", record_header)[1] * 2
                record = shapefile.read(record_length)
                if len(record) < 44:
                    continue
                shape_type = unpack("<i", record[:4])[0]
                if shape_type not in {5, 15, 25}:
                    continue
                part_count, point_count = unpack("<2i", record[36:44])
                parts_end = 44 + 4 * part_count
                parts = list(
                    unpack(f"<{part_count}i", record[44:parts_end])
                )
                points = [
                    unpack(
                        "<2d",
                        record[
                            parts_end + point_index * 16:
                            parts_end + (point_index + 1) * 16
                        ],
                    )
                    for point_index in range(point_count)
                ]
                parts.append(point_count)
                for start, end in zip(parts, parts[1:]):
                    ring = points[start:end]
                    if not ring:
                        continue
                    longitudes, latitudes = transformer.transform(*zip(*ring))
                    rings.append(
                        [
                            [longitude, latitude]
                            for longitude, latitude in zip(
                                longitudes, latitudes
                            )
                        ]
                    )
        if not rings:
            return None
        return {
            "sourcetype": "geojson",
            "source": {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": rings,
                },
            },
            "type": "line",
            "color": "rgba(70, 70, 70, 0.65)",
            "line": {"width": 1},
            "below": "traces",
        }

    def _dashboard(self, steps: pd.DataFrame):
        figure = make_subplots(specs=[[{"secondary_y": True}]])
        series = {
            "Awaiting Next Session": (
                steps["Waiting"] - steps["Unmet Due Demand"]
            ).clip(lower=0),
            "Due Waiting": (
                steps["Unmet Due Demand"] - steps["Overdue"]
            ).clip(lower=0),
            "Overdue": steps["Overdue"],
            "In Treatment": steps["In Treatment"],
            "Admitted": steps["Admitted"],
            "Completed": steps["Completed"],
        }
        for name, values in series.items():
            figure.add_trace(
                go.Scatter(
                    x=steps["Simulation Step"],
                    y=values,
                    mode="lines",
                    name=name,
                ),
                secondary_y=False,
            )
        figure.add_trace(
            go.Scatter(
                x=steps["Simulation Step"],
                y=steps["On Time Rate"],
                mode="lines",
                name="On Time Rate",
            ),
            secondary_y=True,
        )
        figure.update_layout(title="Dialysis Dashboard")
        figure.update_yaxes(title_text="Population", secondary_y=False)
        figure.update_yaxes(title_text="Rate", secondary_y=True)
        self._write(figure, "dashboard")

    def _clinic_plots(
        self,
        clinics: pd.DataFrame,
        clinic_labels: dict[str, str],
    ):
        data = clinics.copy()
        if not data.empty:
            data["Clinic"] = data["Clinic"].map(
                lambda name: clinic_labels.get(name, name)
            )
            utilization = px.line(
                data,
                x="Simulation Step",
                y=[
                    "Occupancy",
                    "Admitted",
                    "Available Capacity",
                    "Utilization",
                ],
                facet_row="Clinic",
                title="Clinic Occupancy, Capacity, and Utilization",
                labels={"variable": "Metric"},
            )
            utilization.update_yaxes(title_text=None)
            domains = [
                axis.domain
                for axis in utilization.select_yaxes()
                if axis.domain is not None
            ]
            for annotation in utilization.layout.annotations:
                if not annotation.text.startswith("Clinic="):
                    continue
                domain = min(
                    domains,
                    key=lambda value: abs(
                        annotation.y - (value[0] + value[1]) / 2
                    ),
                )
                annotation.update(
                    text=annotation.text.removeprefix("Clinic="),
                    x=0,
                    y=domain[1],
                    xanchor="left",
                    yanchor="bottom",
                    textangle=0,
                )
            daily_data = data.groupby(
                ["Cycle", "Clinic"], as_index=False
            )["Completed"].sum()
            daily = px.bar(
                daily_data,
                x="Cycle",
                y="Completed",
                color="Clinic",
                title="Completed Dialysis Treatments by Clinic and Day",
            )
        else:
            utilization = self._empty(
                "Clinic Occupancy, Capacity, and Utilization"
            )
            daily = self._empty(
                "Completed Dialysis Treatments by Clinic and Day"
            )
        self._write(utilization, "clinic_utilization")
        self._write(daily, "daily_completed_by_clinic")

    def _flow_plots(
        self,
        flows: pd.DataFrame,
        clinic_labels: dict[str, str],
    ):
        labeled = flows.copy()
        if not labeled.empty:
            labeled["Clinic"] = labeled["Clinic"].map(
                lambda name: clinic_labels.get(name, name)
            )
        labels = list(
            dict.fromkeys(
                labeled.get("Origin", pd.Series(dtype=str)).tolist()
                + labeled.get("Clinic", pd.Series(dtype=str)).tolist()
            )
        )
        label_index = {label: index for index, label in enumerate(labels)}
        sankey = go.Figure(
            go.Sankey(
                node={"label": labels},
                link={
                    "source": [
                        label_index[value] for value in labeled["Origin"]
                    ],
                    "target": [
                        label_index[value] for value in labeled["Clinic"]
                    ],
                    "value": labeled["Admitted"].tolist(),
                },
            )
        )
        sankey.update_layout(title="Dialysis Origin-to-Clinic Flows")
        self._write(sankey, "origin_clinic_sankey")

        if flows.empty:
            heatmap = self._empty("Dialysis Origin × Clinic Flow")
        else:
            heatmap_flows = flows.copy()
            heatmap_flows["Clinic"] = heatmap_flows["Clinic"].map(
                lambda name: (
                    clinic_labels[name].removesuffix(f" ({name})")
                    + f"<br>({name})"
                    if clinic_labels.get(name, name) != name
                    else name
                )
            )
            heatmap_data = heatmap_flows.pivot(
                index="Origin",
                columns="Clinic",
                values="Admitted",
            ).fillna(0)
            heatmap = px.imshow(
                heatmap_data,
                text_auto=True,
                aspect="auto",
                title="Dialysis Origin × Clinic Flow",
            )
        self._write(heatmap, "origin_clinic_heatmap")

    def _event_plots(
        self,
        events: pd.DataFrame,
        steps: pd.DataFrame,
        clinic_labels: dict[str, str],
    ):
        hourly = px.bar(
            steps.groupby("Cycle Step", as_index=False)["Due Demand"].mean(),
            x="Cycle Step",
            y="Due Demand",
            title="Mean Dialysis Demand by Cycle Step",
        )
        self._write(hourly, "demand_by_cycle_step")
        admissions = events[events["Event"] == "admitted"]
        lateness = px.histogram(
            admissions,
            x="Lateness",
            y="Population",
            histfunc="sum",
            title="Dialysis Waiting Lateness",
        )
        self._write(lateness, "waiting_lateness")
        completed = events[events["Event"] == "completed"].copy()
        if not completed.empty:
            completed["Clinic"] = completed["Clinic"].map(
                lambda name: clinic_labels.get(name, name)
            )
        distance = px.histogram(
            completed,
            x="Distance",
            y="Population",
            color="Clinic",
            histfunc="sum",
            title="Travel Distance by Clinic",
            labels={"Distance": "Distance (km)"},
        )
        self._write(distance, "travel_distance")

    def _resilience_plot(
        self,
        steps: pd.DataFrame,
        node_states: pd.DataFrame,
        water_levels: pd.DataFrame,
    ):
        figure = make_subplots(specs=[[{"secondary_y": True}]])
        state_counts = []
        if not node_states.empty:
            states = {}
            relevant = node_states[
                node_states["Node Type"].isin(
                    ["dialysis_clinic", "water_source"]
                )
            ].sort_values("Simulation Step")
            events_by_step = {
                step: group
                for step, group in relevant.groupby("Simulation Step")
            }
            for simulation_step in steps["Simulation Step"]:
                for _, row in events_by_step.get(
                    simulation_step, pd.DataFrame()
                ).iterrows():
                    states[row["Node"]] = (
                        row["Node Type"],
                        row["Enabled"],
                    )
                state_counts.append(
                    {
                        "Simulation Step": simulation_step,
                        "Active Clinics": sum(
                            enabled
                            for node_type, enabled in states.values()
                            if node_type == "dialysis_clinic"
                        ),
                        "Active ETAs": sum(
                            enabled
                            for node_type, enabled in states.values()
                            if node_type == "water_source"
                        ),
                    }
                )
        counts = pd.DataFrame(state_counts)
        for metric in ("Active Clinics", "Active ETAs"):
            if not counts.empty:
                figure.add_trace(
                    go.Scatter(
                        x=counts["Simulation Step"],
                        y=counts[metric],
                        mode="lines",
                        name=metric,
                    ),
                    secondary_y=False,
                )
        figure.add_trace(
            go.Scatter(
                x=steps["Simulation Step"],
                y=steps["Available Capacity"],
                mode="lines",
                name="Available Capacity",
            ),
            secondary_y=False,
        )
        if not water_levels.empty:
            figure.add_trace(
                go.Scatter(
                    x=water_levels["Simulation Step"],
                    y=water_levels["Water Level"],
                    mode="lines",
                    name="Water Level",
                ),
                secondary_y=True,
            )
        figure.update_layout(
            title="Water Level, Active Infrastructure, and Capacity"
        )
        figure.update_yaxes(
            title_text="Nodes / treatment slots", secondary_y=False
        )
        figure.update_yaxes(
            title_text="Water level", secondary_y=True
        )
        self._write(figure, "resilience_timeline")

    def _geographic_plot(
        self,
        flows: pd.DataFrame,
        clinic_labels: dict[str, str],
        coordinates: dict[str, list[float]],
    ):
        if flows.empty or not any(
            coordinates.get(name, [0, 0]) != [0, 0]
            for name in set(flows["Origin"]) | set(flows["Clinic"])
        ):
            return
        figure = go.Figure()
        clinic_names = list(dict.fromkeys(flows["Clinic"]))
        palette = px.colors.qualitative.Dark24
        colors = {
            clinic: palette[index % len(palette)]
            for index, clinic in enumerate(clinic_names)
        }
        plotted_longitudes = []
        plotted_latitudes = []
        for row in flows.itertuples(index=False):
            origin = coordinates.get(row.Origin)
            clinic = coordinates.get(row.Clinic)
            if origin is None or clinic is None:
                continue
            plotted_longitudes.extend([origin[0], clinic[0]])
            plotted_latitudes.extend([origin[1], clinic[1]])
            clinic_label = clinic_labels.get(row.Clinic, row.Clinic)
            hover_text = (
                f"<b>{row.Origin} → {clinic_label}</b>"
                f"<br>Admitted: {row.Admitted:,}"
                f"<br>Completed: {row.Completed:,}"
                f"<br>Average distance: {row[-1]:,.2f} km"
            )
            figure.add_trace(
                go.Scattermap(
                    lon=[origin[0], clinic[0]],
                    lat=[origin[1], clinic[1]],
                    mode="lines+markers",
                    line={
                        "width": max(1, row.Admitted),
                        "color": colors[row.Clinic],
                    },
                    marker={"color": colors[row.Clinic]},
                    name=f"{row.Origin} → {clinic_label}",
                    text=[hover_text, hover_text],
                    hovertemplate="%{text}<extra></extra>",
                )
            )
            steps = range(1, 32)
            figure.add_trace(
                go.Scattermap(
                    lon=[
                        origin[0] + (clinic[0] - origin[0]) * step / 32
                        for step in steps
                    ],
                    lat=[
                        origin[1] + (clinic[1] - origin[1]) * step / 32
                        for step in steps
                    ],
                    mode="markers",
                    marker={
                        "size": 16,
                        "color": "rgba(0, 0, 0, 0.01)",
                    },
                    text=[hover_text] * 31,
                    hovertemplate="%{text}<extra></extra>",
                    showlegend=False,
                )
            )
        clinic_locations = [
            (name, coordinates.get(name))
            for name in clinic_names
            if coordinates.get(name) is not None
        ]
        if clinic_locations:
            marker_lon = [
                position[0] for _, position in clinic_locations
            ]
            marker_lat = [
                position[1] for _, position in clinic_locations
            ]
            figure.add_trace(
                go.Scattermap(
                    lon=marker_lon,
                    lat=marker_lat,
                    mode="markers",
                    marker={"size": 22, "color": "#222222"},
                    hoverinfo="skip",
                    legendgroup="clinics",
                    showlegend=False,
                )
            )
            figure.add_trace(
                go.Scattermap(
                    lon=marker_lon,
                    lat=marker_lat,
                    mode="markers",
                    marker={
                        "size": 18,
                        "color": [
                            colors[name] for name, _ in clinic_locations
                        ],
                    },
                    text=[
                        "<b>Clinic</b><br>"
                        f"{clinic_labels.get(name, name)}"
                        for name, _ in clinic_locations
                    ],
                    hovertemplate="%{text}<extra></extra>",
                    name="Clinics",
                    legendgroup="clinics",
                )
            )
        map_layout = {"style": "open-street-map"}
        neighborhood_layer = self._neighborhood_layer()
        if neighborhood_layer is not None:
            map_layout["layers"] = [neighborhood_layer]
        if plotted_longitudes:
            longitude_span = max(plotted_longitudes) - min(
                plotted_longitudes
            )
            latitude_span = max(plotted_latitudes) - min(plotted_latitudes)
            longitude_zoom = (
                log2(360 / longitude_span) - 1
                if longitude_span
                else 12
            )
            latitude_zoom = (
                log2(170 / latitude_span) - 1
                if latitude_span
                else 12
            )
            map_layout["center"] = {
                "lon": (
                    min(plotted_longitudes) + max(plotted_longitudes)
                )
                / 2,
                "lat": (min(plotted_latitudes) + max(plotted_latitudes)) / 2,
            }
            map_layout["zoom"] = max(
                1,
                min(12, longitude_zoom, latitude_zoom),
            )
        figure.update_layout(
            title="Dialysis Geographic Flows",
            map=map_layout,
            margin={"l": 0, "r": 0, "b": 0},
        )
        self._write(figure, "geographic_flows")

    def generate(self):
        frames = self._read_data()
        clinic_labels = self._clinic_labels(frames["locations"])
        coordinates = self._coordinates(frames["locations"])
        self._dashboard(frames["steps"])
        self._clinic_plots(frames["clinics"], clinic_labels)
        self._flow_plots(frames["flows"], clinic_labels)
        self._event_plots(
            frames["events"],
            frames["steps"],
            clinic_labels,
        )
        self._resilience_plot(
            frames["steps"],
            frames["node_states"],
            frames["water_levels"],
        )
        self._geographic_plot(
            frames["flows"],
            clinic_labels,
            coordinates,
        )
        return self.html_path


def generate_dialysis_visualizations(
    experiment_path: Path | str,
    export_png: bool = True,
) -> Path:
    """Generate all dialysis plots from an experiment results folder."""
    return DialysisVisualizationGenerator(
        experiment_path,
        export_png=export_png,
    ).generate()


def _resolve_experiment_path(value: str) -> Path:
    supplied = Path(value)
    if supplied.is_dir():
        return supplied
    output_logs_path = Path("output_logs") / supplied
    if output_logs_path.is_dir():
        return output_logs_path
    raise FileNotFoundError(
        f"Experiment folder not found: {supplied} or {output_logs_path}"
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate dialysis visualizations from an output_logs "
            "experiment folder."
        )
    )
    parser.add_argument(
        "experiment",
        help=(
            "Experiment folder path, or its folder name under output_logs."
        ),
    )
    parser.add_argument(
        "--no-png",
        action="store_true",
        help="Generate HTML only, even when Kaleido is installed.",
    )
    args = parser.parse_args()
    output_path = generate_dialysis_visualizations(
        _resolve_experiment_path(args.experiment),
        export_png=not args.no_png,
    )
    print(f"Dialysis visualizations written to {output_path}")


if __name__ == "__main__":
    main()
