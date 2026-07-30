"""Generate Plotly shelter dashboards from an experiment output folder."""

from __future__ import annotations

import argparse
import csv
from importlib.util import find_spec
from pathlib import Path
import unicodedata

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


DATA_FILES = {
    "events": "shelter_events.csv",
    "steps": "shelter_step.csv",
    "nodes": "shelter_node_step.csv",
    "regions": "shelter_region_step.csv",
    "cycles": "shelter_cycle.csv",
    "flows": "shelter_origin_shelter.csv",
    "locations": "shelter_locations.csv",
    "audit": "shelter_input_audit.csv",
    "groups": "shelter_group_step.csv",
}


class ShelterVisualizationGenerator:
    def __init__(self, experiment_path: Path | str, export_png: bool = True):
        self.experiment_path = Path(experiment_path)
        self.data_path = self.experiment_path / "data_frames"
        self.html_path = self.experiment_path / "html_plots" / "shelter"
        self.figure_path = self.experiment_path / "figures" / "shelter"
        self.export_png = export_png
        self.png_available = export_png and find_spec("kaleido") is not None

    def read(self) -> dict[str, pd.DataFrame]:
        missing = [
            filename for filename in DATA_FILES.values()
            if not (self.data_path / filename).is_file()
        ]
        if missing:
            raise FileNotFoundError(
                f"missing shelter result files in {self.data_path}: "
                + ", ".join(missing)
            )
        return {
            name: pd.read_csv(
                self.data_path / filename,
                sep=";",
                encoding="utf-8-sig",
            )
            for name, filename in DATA_FILES.items()
        }

    def write(self, figure, name: str):
        self.html_path.mkdir(parents=True, exist_ok=True)
        config = (
            {"scrollZoom": True, "displayModeBar": True}
            if name in {
                "flood_sector_exposure",
                "flood_neighborhood_exposure_percentage",
                "geographic_flows",
            }
            else None
        )
        figure.write_html(
            self.html_path / f"{name}.html",
            include_plotlyjs=True,
            config=config,
        )
        if self.png_available:
            self.figure_path.mkdir(parents=True, exist_ok=True)
            try:
                figure.write_image(self.figure_path / f"{name}.png")
            except Exception:
                self.png_available = False

    @staticmethod
    def empty(title: str):
        figure = go.Figure()
        figure.update_layout(title=title)
        figure.add_annotation(
            text="No shelter data recorded",
            x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
        )
        return figure

    def generate(self):
        frames = self.read()
        figures = {
            "status_capacity_dashboard": self.status_dashboard(frames),
            "daily_outcomes": self.daily_outcomes(frames),
            "shelter_occupancy_heatmap": self.occupancy_heatmap(frames),
            "constrained_shelters": self.constrained_shelters(frames),
            "origin_shelter_sankey": self.sankey(frames),
            "origin_shelter_heatmap": self.flow_heatmap(frames),
            "geographic_flows": self.geographic_flows(frames),
            "flood_sector_exposure": self.flood_sector_map(frames),
            "flood_neighborhood_exposure_percentage":
                self.flood_neighborhood_percentage_map(frames),
            "travel_distance": self.travel_distance(frames),
            "demographic_equity": self.demographic_equity(frames),
            "data_quality": self.data_quality(frames),
        }
        for name, figure in figures.items():
            self.write(figure, name)
        return figures

    def status_dashboard(self, frames):
        steps = frames["steps"]
        if steps.empty:
            return self.empty("Shelter status and capacity")
        figure = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            subplot_titles=("Population status", "Capacity and waitlist"),
        )
        for column in ["Safe", "In Danger", "Sheltered"]:
            figure.add_trace(
                go.Scatter(
                    x=steps["Simulation Step"], y=steps[column],
                    name=column, mode="lines",
                ),
                row=1, col=1,
            )
        for column in ["Enabled Capacity", "Free Beds", "Waitlist"]:
            figure.add_trace(
                go.Scatter(
                    x=steps["Simulation Step"], y=steps[column],
                    name=column, mode="lines",
                ),
                row=2, col=1,
            )
        figure.update_layout(title="Shelter status and capacity dashboard")
        return figure

    def daily_outcomes(self, frames):
        cycles = frames["cycles"]
        if cycles.empty:
            return self.empty("Daily shelter outcomes")
        columns = ["Arrivals", "Admissions", "Denials", "Reallocations"]
        return px.bar(
            cycles, x="Cycle", y=columns, barmode="group",
            labels={"Cycle": "Cycle (Day)"},
            title="Daily shelter outcomes",
        )

    def occupancy_heatmap(self, frames):
        nodes = frames["nodes"]
        if nodes.empty:
            return self.empty("Shelter occupancy heatmap")
        pivot = nodes.pivot(
            index="Shelter Name", columns="Simulation Step", values="Utilization"
        )
        return px.imshow(
            pivot, aspect="auto", color_continuous_scale="YlOrRd",
            labels={"color": "Utilization"},
            title="Shelter occupancy by simulation step",
        )

    def constrained_shelters(self, frames):
        nodes = frames["nodes"]
        constrained = nodes[(nodes["Queue"] > 0) | (nodes["Free Beds"] == 0)]
        if constrained.empty:
            return self.empty("Constrained shelter capacity and waitlist")
        totals = constrained.groupby(
            ["Simulation Step", "Shelter Name", "Shelter"], as_index=False
        )[["Capacity", "Sheltered", "Queue"]].max()
        totals["Shelter Panel"] = (
            totals["Shelter Name"] + " (" + totals["Shelter"] + ")"
        )
        top = (
            totals.groupby("Shelter Panel")["Queue"].max()
            .nlargest(8).index
        )
        selected = totals[totals["Shelter Panel"].isin(top)]
        figure = px.line(
            selected, x="Simulation Step", y=["Sheltered", "Queue"],
            facet_row="Shelter Panel",
            title="Capacity-constrained shelters: occupancy and queue",
        )
        figure.update_yaxes(title_text=None)

        y_domains = [
            tuple(figure.layout[name].domain)
            for name in figure.layout
            if name.startswith("yaxis")
            and getattr(figure.layout[name], "domain", None) is not None
        ]
        for annotation in figure.layout.annotations:
            if not annotation.text.startswith("Shelter Panel="):
                continue
            annotation.text = annotation.text.removeprefix("Shelter Panel=")
            annotation.x = 0
            annotation.xref = "paper"
            annotation.xanchor = "left"
            annotation.textangle = 0
            matching_domain = next(
                (
                    domain for domain in y_domains
                    if domain[0] <= annotation.y <= domain[1]
                ),
                None,
            )
            if matching_domain is not None:
                annotation.y = matching_domain[1]
                annotation.yanchor = "bottom"

        return figure

    def sankey(self, frames):
        flows = frames["flows"]
        if flows.empty:
            return self.empty("Origin-to-shelter Sankey")
        origins = list(flows["Population Origin Region"].dropna().unique())
        shelters = list(flows["Shelter"].dropna().unique())
        labels = origins + shelters
        lookup = {label: index for index, label in enumerate(labels)}
        height = max(700, 28 * max(len(origins), len(shelters)))
        return go.Figure(
            go.Sankey(
                node={"label": labels},
                link={
                    "source": [lookup[value] for value in flows["Population Origin Region"]],
                    "target": [lookup[value] for value in flows["Shelter"]],
                    "value": flows["Population"],
                },
            ),
            layout={
                "title": "Population origin to shelter flows",
                "height": height,
            },
        )

    def flow_heatmap(self, frames):
        flows = frames["flows"]
        if flows.empty:
            return self.empty("Origin-to-shelter flow heatmap")
        pivot = flows.pivot_table(
            index="Population Origin Region", columns="Shelter",
            values="Population", aggfunc="sum", fill_value=0,
        )
        return px.imshow(
            pivot, aspect="auto", color_continuous_scale="Blues",
            title="Origin-to-shelter population flows",
        )

    def geographic_flows(self, frames):
        flows = frames["flows"]
        locations = frames["locations"]
        if flows.empty or locations.empty:
            return self.empty("Geographic shelter flows")
        shelter_coords = locations[locations["Is Shelter"].astype(bool)].set_index(
            "Complete Name"
        )
        home_coords = locations[~locations["Is Shelter"].astype(bool)].drop_duplicates(
            "Region"
        ).set_index("Region")
        figure = go.Figure()

        import shapefile
        from pyproj import CRS, Transformer
        repo = Path(__file__).resolve().parents[3]
        neighborhood_path = (
            repo / "data_input/spatial/bairros_vigentes/bairros_vigentes.shp"
        )
        projection = neighborhood_path.with_suffix(".prj")
        transformer = Transformer.from_crs(
            CRS.from_wkt(projection.read_text(encoding="utf-8")),
            "EPSG:4326", always_xy=True,
        )
        reader = shapefile.Reader(str(neighborhood_path))
        fields = [field[0] for field in reader.fields[1:]]
        name_index = fields.index("NOME")
        neighborhood_features = []
        neighborhood_ids = []
        neighborhood_names = []
        for index, shape_record in enumerate(reader.iterShapeRecords()):
            neighborhood_id = str(index)
            geometry = shape_record.shape.__geo_interface__
            geometry["coordinates"] = self._transform_coordinates(
                geometry["coordinates"], transformer
            )
            neighborhood_features.append({
                "type": "Feature",
                "id": neighborhood_id,
                "properties": {
                    "name": str(shape_record.record[name_index]),
                },
                "geometry": geometry,
            })
            neighborhood_ids.append(neighborhood_id)
            neighborhood_names.append(str(shape_record.record[name_index]))
        figure.add_trace(go.Choroplethmapbox(
            geojson={
                "type": "FeatureCollection",
                "features": neighborhood_features,
            },
            locations=neighborhood_ids,
            z=[0] * len(neighborhood_ids),
            text=neighborhood_names,
            hovertemplate="%{text}<extra>Neighborhood</extra>",
            colorscale=[
                [0, "rgba(0,0,0,0)"],
                [1, "rgba(0,0,0,0)"],
            ],
            marker_line_color="rgba(60,60,60,0.65)",
            marker_line_width=1,
            showscale=False,
            name="Neighborhood boundaries",
            showlegend=False,
        ))
        midpoint_lons = []
        midpoint_lats = []
        midpoint_hover = []
        for _, flow in flows.nlargest(150, "Population").iterrows():
            origin = flow["Population Origin Region"]
            shelter = flow["Shelter"]
            if origin not in home_coords.index or shelter not in shelter_coords.index:
                continue
            source = home_coords.loc[origin]
            target = shelter_coords.loc[shelter]
            figure.add_trace(go.Scattermapbox(
                lon=[source["Longitude"], target["Longitude"]],
                lat=[source["Latitude"], target["Latitude"]],
                mode="lines",
                line={"width": max(0.6, float(flow["Population"]) ** 0.4 / 2.5),
                      "color": "rgba(30,90,180,0.35)"},
                hovertext=f"{origin} → {shelter}: {flow['Population']}",
                hoverinfo="text", showlegend=False,
            ))
            source_lon = float(source["Longitude"])
            source_lat = float(source["Latitude"])
            target_lon = float(target["Longitude"])
            target_lat = float(target["Latitude"])
            hover_text = (
                f"{origin} → {shelter}<br>Population: {flow['Population']}"
            )
            for index in range(1, 21):
                fraction = index / 21
                midpoint_lons.append(
                    source_lon + (target_lon - source_lon) * fraction
                )
                midpoint_lats.append(
                    source_lat + (target_lat - source_lat) * fraction
                )
                midpoint_hover.append(hover_text)
        figure.add_trace(go.Scattermapbox(
            lon=midpoint_lons,
            lat=midpoint_lats,
            text=midpoint_hover,
            mode="markers",
            marker={"size": 14, "color": "rgba(0,0,0,0.01)"},
            hoverinfo="text",
            showlegend=False,
        ))
        figure.add_trace(go.Scattermapbox(
            lon=shelter_coords["Longitude"], lat=shelter_coords["Latitude"],
            text=shelter_coords["Display Name"],
            customdata=shelter_coords.index,
            hovertemplate=(
                "%{text}<br>Complete name: %{customdata}<extra>Shelter</extra>"
            ),
            mode="markers",
            marker={"size": 5, "color": "crimson"}, name="Shelters",
        ))
        figure.update_layout(
            mapbox={
                "style": "carto-positron",
                "zoom": 9.5,
                "center": {"lat": -30.08, "lon": -51.18},
            },
            margin={"l": 0, "r": 0, "t": 55, "b": 0},
            title="Largest geographic shelter flows",
        )
        return figure

    def flood_sector_map(self, frames):
        audit = frames["audit"]
        coverage = audit[audit["Audit Type"] == "spatial_coverage"]
        if coverage.empty:
            figure = self.empty("Flood-sector exposure")
            figure.layout.annotations[0].text = (
                "This experiment uses region-level rather than census-sector exposure"
            )
            return figure
        try:
            import shapefile
            from pyproj import CRS, Transformer
            repo = Path(__file__).resolve().parents[3]
            csv_path = Path(str(coverage.iloc[0]["Source"]))
            shape_path = repo / (
                "data_input/spatial/setores_preliminares_2022/"
                "porto_alegre_preliminary_mesh_2022.shp"
            )
            projection = shape_path.with_suffix(".prj")
            with csv_path.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
                flooded = {
                    str(row["Setores Censitários Preliminares"]).removesuffix("P"):
                    int(float(row["Total de pessoas"]))
                    for row in rows
                    if str(row["Inundação"]).casefold() == "true"
                }
            transformer = Transformer.from_crs(
                CRS.from_wkt(projection.read_text(encoding="utf-8")),
                "EPSG:4326", always_xy=True,
            )
            reader = shapefile.Reader(str(shape_path))
            fields = [field[0] for field in reader.fields[1:]]
            code_index = fields.index("CD_SETOR")
            features = []
            populations = []
            identifiers = []
            for shape_record in reader.iterShapeRecords():
                sector_id = str(
                    shape_record.record[code_index]
                ).removesuffix("P")
                if sector_id not in flooded:
                    continue
                geometry = shape_record.shape.__geo_interface__
                geometry["coordinates"] = self._transform_coordinates(
                    geometry["coordinates"], transformer
                )
                features.append({
                    "type": "Feature", "id": sector_id,
                    "properties": {"sector": sector_id},
                    "geometry": geometry,
                })
                identifiers.append(sector_id)
                populations.append(flooded[sector_id])
            if not features:
                raise ValueError("no flooded sector geometry matched")
            figure = go.Figure(go.Choroplethmapbox(
                geojson={"type": "FeatureCollection", "features": features},
                locations=identifiers, z=populations,
                colorscale="Reds", marker_opacity=0.65,
                marker_line_width=0,
                colorbar_title="Exposed people",
            ))
            figure.update_layout(
                mapbox_style="carto-positron",
                mapbox_zoom=9.5,
                mapbox_center={"lat": -30.08, "lon": -51.18},
                margin={"l": 0, "r": 0, "t": 55, "b": 0},
                title="Flood-sector exposure (5.30 m)",
            )
            return figure
        except Exception as error:
            figure = self.empty("Flood-sector exposure")
            figure.layout.annotations[0].text = (
                f"Map unavailable: {type(error).__name__}"
            )
            return figure

    def flood_neighborhood_percentage_map(self, frames):
        audit = frames["audit"]
        coverage = audit[audit["Audit Type"] == "spatial_coverage"]
        title = "Flood-exposed population by neighborhood (5.30 m)"
        if coverage.empty:
            figure = self.empty(title)
            figure.layout.annotations[0].text = (
                "This experiment uses region-level rather than census-sector exposure"
            )
            return figure
        try:
            import shapefile
            from pyproj import CRS, Transformer

            repo = Path(__file__).resolve().parents[3]
            csv_path = Path(str(coverage.iloc[0]["Source"]))
            shape_path = repo / (
                "data_input/spatial/bairros_vigentes/bairros_vigentes.shp"
            )
            totals = {}
            exposed = {}
            with csv_path.open(encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream):
                    neighborhood = self._normalize_spatial_name(row["Bairro"])
                    population = int(float(row["Total de pessoas"]))
                    totals[neighborhood] = totals.get(neighborhood, 0) + population
                    if str(row["Inundação"]).casefold() == "true":
                        exposed[neighborhood] = (
                            exposed.get(neighborhood, 0) + population
                        )

            projection = shape_path.with_suffix(".prj")
            transformer = Transformer.from_crs(
                CRS.from_wkt(projection.read_text(encoding="utf-8")),
                "EPSG:4326", always_xy=True,
            )
            reader = shapefile.Reader(str(shape_path))
            fields = [field[0] for field in reader.fields[1:]]
            name_index = fields.index("NOME")
            features = []
            identifiers = []
            percentages = []
            names = []
            for index, shape_record in enumerate(reader.iterShapeRecords()):
                name = str(shape_record.record[name_index])
                normalized = self._normalize_spatial_name(name)
                total = totals.get(normalized, 0)
                geometry = shape_record.shape.__geo_interface__
                geometry["coordinates"] = self._transform_coordinates(
                    geometry["coordinates"], transformer
                )
                identifier = str(index)
                features.append({
                    "type": "Feature",
                    "id": identifier,
                    "properties": {"neighborhood": name},
                    "geometry": geometry,
                })
                identifiers.append(identifier)
                names.append(name)
                percentages.append(
                    100 * exposed.get(normalized, 0) / total if total else 0
                )

            figure = go.Figure(go.Choroplethmapbox(
                geojson={"type": "FeatureCollection", "features": features},
                locations=identifiers,
                z=percentages,
                text=names,
                colorscale="Reds",
                marker_opacity=0.65,
                marker_line_color="rgba(70,70,70,0.65)",
                marker_line_width=1,
                colorbar_title="Exposed population (%)",
                zmin=0,
                zmax=100,
                hovertemplate=(
                    "%{text}<br>Exposed population: %{z:.1f}%<extra></extra>"
                ),
            ))
            figure.update_layout(
                mapbox_style="carto-positron",
                mapbox_zoom=9.5,
                mapbox_center={"lat": -30.08, "lon": -51.18},
                margin={"l": 0, "r": 0, "t": 55, "b": 0},
                title=title,
            )
            return figure
        except Exception as error:
            figure = self.empty(title)
            figure.layout.annotations[0].text = (
                f"Map unavailable: {type(error).__name__}"
            )
            return figure

    @staticmethod
    def _normalize_spatial_name(value):
        decomposed = unicodedata.normalize("NFKD", str(value))
        without_accents = "".join(
            character
            for character in decomposed
            if not unicodedata.combining(character)
        )
        return " ".join(without_accents.casefold().split())

    @classmethod
    def _transform_coordinates(cls, coordinates, transformer):
        if not coordinates:
            return coordinates
        if isinstance(coordinates[0], (int, float)):
            return transformer.transform(coordinates[0], coordinates[1])
        return [
            cls._transform_coordinates(value, transformer)
            for value in coordinates
        ]

    def travel_distance(self, frames):
        flows = frames["flows"]
        if flows.empty:
            return self.empty("Shelter travel distance")
        figure = px.scatter(
            flows, x="Mean Distance Km", y="Population",
            color="Shelter Region", size="Population",
            size_max=35,
            hover_name="Population Origin Region", log_y=True,
            title="Travel distance and population by origin-shelter flow",
        )
        figure.update_traces(marker={"sizemin": 5})
        return figure

    def demographic_equity(self, frames):
        groups = frames["groups"]
        sheltered = groups[groups["Status"] == "sheltered"]
        if sheltered.empty:
            return self.empty("Demographic shelter equity")
        return px.line(
            sheltered, x="Simulation Step", y="Rate Within Group",
            color="Group", facet_row="Dimension",
            title="Sheltered share within age and occupation groups",
        )

    def data_quality(self, frames):
        audit = frames["audit"]
        if audit.empty:
            return self.empty("Shelter input data quality")
        counts = audit.groupby("Audit Type", as_index=False).size()
        return px.bar(
            counts, x="Audit Type", y="size",
            title="Shelter input audit records",
            labels={"size": "Records"},
        )


def generate_shelter_visualizations(
    experiment_path: Path | str, export_png: bool = True
):
    return ShelterVisualizationGenerator(
        experiment_path, export_png
    ).generate()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment_path")
    parser.add_argument("--no-png", action="store_true")
    args = parser.parse_args()
    generate_shelter_visualizations(
        args.experiment_path, export_png=not args.no_png
    )


if __name__ == "__main__":
    main()
