"""Plotly outputs for inpatient care simulations."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


class InpatientCareVisualizationGenerator:
    def __init__(self, experiment_path: Path | str, export_png: bool = True):
        self.experiment_path = Path(experiment_path)
        self.data_path = self.experiment_path / "data_frames"
        self.html_path = (
            self.experiment_path / "html_plots" / "inpatient_care"
        )
        self.png_path = (
            self.experiment_path / "png_plots" / "inpatient_care"
        )
        self.export_png = export_png

    def _read(self, name: str) -> pd.DataFrame:
        path = self.data_path / name
        if not path.is_file():
            return pd.DataFrame()
        return pd.read_csv(path, sep=";", encoding="utf-8-sig")

    def _write(self, figure: go.Figure, name: str):
        self.html_path.mkdir(parents=True, exist_ok=True)
        figure.write_html(
            self.html_path / f"{name}.html", include_plotlyjs="cdn"
        )
        if self.export_png:
            self.png_path.mkdir(parents=True, exist_ok=True)
            try:
                figure.write_image(self.png_path / f"{name}.png")
            except (ImportError, ValueError):
                pass

    def _dashboard(self, steps: pd.DataFrame):
        if steps.empty:
            return
        figure = go.Figure()
        for column in ("New Demand", "Admitted", "Discharged", "Waiting"):
            figure.add_trace(
                go.Scatter(
                    x=steps["Simulation Step"],
                    y=steps[column],
                    mode="lines+markers",
                    name=column,
                )
            )
        figure.update_layout(
            title="Inpatient Demand, Admissions, Discharges, and Queue",
            xaxis_title="Simulation Step",
            yaxis_title="Population",
        )
        self._write(figure, "inpatient_dashboard")

        delay = go.Figure()
        delay.add_trace(
            go.Scatter(
                x=steps["Simulation Step"],
                y=steps["Average Admission Delay Steps"],
                mode="lines+markers",
                name="Average Delay",
            )
        )
        delay.add_trace(
            go.Scatter(
                x=steps["Simulation Step"],
                y=steps["Maximum Admission Delay Steps"],
                mode="lines+markers",
                name="Maximum Delay",
            )
        )
        delay.update_layout(
            title="Inpatient Admission Delay",
            xaxis_title="Simulation Step",
            yaxis_title="Steps",
        )
        self._write(delay, "admission_delay")

    def _bed_plots(self, beds: pd.DataFrame):
        if beds.empty:
            return
        for (hospital, specialty, bed_type, payer), frame in beds.groupby(
            ["Hospital", "Specialty", "Bed Type", "Payer"],
            sort=True,
        ):
            if (
                frame["Occupancy"].max() == 0
                and frame["Admitted"].sum() == 0
                and frame["Discharged"].sum() == 0
            ):
                continue
            figure = go.Figure()
            figure.add_trace(
                go.Scatter(
                    x=frame["Simulation Step"],
                    y=frame["Occupancy"],
                    mode="lines+markers",
                    name="Occupancy",
                )
            )
            figure.add_trace(
                go.Scatter(
                    x=frame["Simulation Step"],
                    y=frame["Configured Capacity"],
                    mode="lines",
                    name="Capacity",
                )
            )
            figure.update_layout(
                title=(
                    f"{hospital}: {specialty} / {bed_type} ({payer})"
                ),
                xaxis_title="Simulation Step",
                yaxis_title="Beds",
            )
            safe = "_".join(
                str(value)
                .lower()
                .replace(" ", "_")
                .replace("/", "_")
                for value in (hospital, specialty, bed_type, payer)
            )
            self._write(figure, f"occupancy_{safe}")

    def _region_plot(self, regions: pd.DataFrame):
        if regions.empty:
            return
        figure = px.line(
            regions,
            x="Simulation Step",
            y="Utilization",
            color="Region",
            markers=True,
            title="Inpatient Bed Utilization by Region",
        )
        self._write(figure, "regional_utilization")

    def generate(self) -> Path:
        self._dashboard(self._read("inpatient_step.csv"))
        self._bed_plots(self._read("inpatient_bed_step.csv"))
        self._region_plot(self._read("inpatient_region_step.csv"))
        return self.html_path


def generate_inpatient_care_visualizations(
    experiment_path: Path | str, export_png: bool = True
) -> Path:
    return InpatientCareVisualizationGenerator(
        experiment_path, export_png=export_png
    ).generate()


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate inpatient care visualizations from an experiment run"
        )
    )
    parser.add_argument("experiment")
    parser.add_argument("--no-png", action="store_true")
    args = parser.parse_args()
    supplied = Path(args.experiment)
    path = (
        supplied
        if supplied.is_dir()
        else Path("output_logs") / supplied
    )
    if not path.is_dir():
        raise FileNotFoundError(f"Experiment folder not found: {path}")
    output = generate_inpatient_care_visualizations(
        path, export_png=not args.no_png
    )
    print(f"Inpatient care visualizations written to {output}")


if __name__ == "__main__":
    main()
