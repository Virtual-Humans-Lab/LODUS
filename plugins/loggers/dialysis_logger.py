"""Dialysis-specific event, state, aggregate, and visualization logger."""

from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core.plugin import LoggerPlugin
from core.population import PopulationTemplate
from core.simulator import LodusSimulation


class DialysisLogger(LoggerPlugin):
    """Records dialysis demand, treatments, clinic utilization, and flows."""

    EVENT_COLUMNS = [
        "Simulation Step",
        "Cycle Step",
        "Cycle",
        "Event",
        "Population",
        "Origin ID",
        "Origin",
        "Origin Region",
        "Clinic ID",
        "Clinic",
        "Clinic Region",
        "Due Day",
        "Treatment Frame",
        "Lateness",
        "On Time",
        "Distance",
    ]
    STEP_COLUMNS = [
        "Simulation Step",
        "Cycle Step",
        "Cycle",
        "Waiting",
        "Due Demand",
        "Unmet Due Demand",
        "Overdue",
        "In Treatment",
        "Admitted",
        "Completed",
        "Available Capacity",
        "Used Capacity",
        "Unused Capacity",
        "Capacity Constrained",
        "On Time Admissions",
        "On Time Rate",
        "Average Admission Lateness",
        "Maximum Admission Lateness",
    ]
    CLINIC_COLUMNS = [
        "Simulation Step",
        "Cycle Step",
        "Cycle",
        "Clinic ID",
        "Clinic",
        "Clinic Region",
        "Enabled",
        "Open",
        "Configured Capacity",
        "Available Capacity",
        "Total Population",
        "Occupancy",
        "Admitted",
        "Completed",
        "Unused Capacity",
        "Utilization",
    ]

    def __init__(self, export_png: bool = True):
        self.export_png = export_png
        self.events: list[dict] = []
        self.step_rows: list[dict] = []
        self.clinic_rows: list[dict] = []
        self.sim_step = 0
        self.cycle_step = 0
        self._png_export_available = False

    def load_plugin(self, simulation: LodusSimulation):
        dialysis_plugins = [
            plugin
            for plugin in simulation.plugin_controller.loaded_action_plugins
            if getattr(plugin, "ACTION_TYPE", None) == "dialysis"
            and callable(getattr(plugin, "add_event_listener", None))
        ]
        if not dialysis_plugins:
            raise ValueError(
                "DialysisLogger requires DialysisPlugin to be loaded first"
            )
        self.simulation = simulation
        self.env_graph = simulation.env_graph
        self.dialysis_plugin = dialysis_plugins[0]
        self.cycle_length = simulation.time_status.cycle_length
        self.base_path = Path("output_logs") / simulation.experiment_name
        self.data_frames_path = self.base_path / "data_frames"
        self.html_plots_path = self.base_path / "html_plots" / "dialysis"
        self.figures_path = self.base_path / "figures" / "dialysis"
        self.dialysis_plugin.add_event_listener(
            self.__class__.__name__, self._log_event
        )

    def setup_logger(self):
        self.data_frames_path.mkdir(parents=True, exist_ok=True)
        self.html_plots_path.mkdir(parents=True, exist_ok=True)
        self._png_export_available = (
            self.export_png and find_spec("kaleido") is not None
        )
        if self._png_export_available:
            self.figures_path.mkdir(parents=True, exist_ok=True)

    def update_time_step(self, cycle_step: int, simulation_step: int):
        self.cycle_step = cycle_step
        self.sim_step = simulation_step

    def _log_event(self, event: dict):
        event["lateness"] = max(0, event["cycle"] - event["due_day"])
        event["on_time"] = int(event["lateness"] == 0)
        self.events.append(event)

    def _events_for_step(self, event_type: str, clinic_id=None) -> list[dict]:
        return [
            event
            for event in self.events
            if event["simulation_step"] == self.sim_step
            and event["event_type"] == event_type
            and (clinic_id is None or event["clinic_id"] == clinic_id)
        ]

    @staticmethod
    def _event_population(events: list[dict]) -> int:
        return sum(event["population"] for event in events)

    def _clinic_capacity(self, clinic_id: int) -> tuple[int, int]:
        clinic = self.env_graph.get_node_by_id(clinic_id)
        configured = sum(
            capacity
            for _, _, capacity in self.dialysis_plugin.clinic_schedules[
                clinic_id
            ]
        )
        if not clinic.is_enabled():
            return configured, 0
        available = sum(
            capacity
            for opening, closing, capacity
            in self.dialysis_plugin.clinic_schedules[clinic_id]
            if self.dialysis_plugin._is_open(
                self.cycle_step, opening, closing
            )
        )
        return configured, available

    def log_simulation_step(self):
        cycle = self.sim_step // self.cycle_length
        current_day = self.sim_step // self.cycle_length
        waiting_template = PopulationTemplate(
            traceable_characteristics={
                self.dialysis_plugin.PATIENT: True,
                self.dialysis_plugin.STATUS: "waiting",
            }
        )
        due_template = PopulationTemplate(
            traceable_characteristics={
                self.dialysis_plugin.PATIENT: True,
                self.dialysis_plugin.STATUS: "waiting",
                self.dialysis_plugin.NEXT_DUE: lambda day: day <= current_day,
            }
        )
        overdue_template = PopulationTemplate(
            traceable_characteristics={
                self.dialysis_plugin.PATIENT: True,
                self.dialysis_plugin.STATUS: "waiting",
                self.dialysis_plugin.NEXT_DUE: lambda day: day < current_day,
            }
        )
        treatment_template = PopulationTemplate(
            traceable_characteristics={
                self.dialysis_plugin.PATIENT: True,
                self.dialysis_plugin.STATUS: "in_treatment",
            }
        )

        admissions = self._events_for_step("admitted")
        completions = self._events_for_step("completed")
        admitted = self._event_population(admissions)
        completed = self._event_population(completions)
        waiting = self.env_graph.get_population_size(waiting_template)
        unmet_due = self.env_graph.get_population_size(due_template)
        overdue = self.env_graph.get_population_size(overdue_template)
        in_treatment = self.env_graph.get_population_size(treatment_template)
        available_capacity = 0

        for clinic_id in self.dialysis_plugin.clinic_schedules:
            clinic = self.env_graph.get_node_by_id(clinic_id)
            clinic_admissions = self._events_for_step("admitted", clinic_id)
            clinic_completions = self._events_for_step("completed", clinic_id)
            clinic_admitted = self._event_population(clinic_admissions)
            clinic_completed = self._event_population(clinic_completions)
            configured, available = self._clinic_capacity(clinic_id)
            available_capacity += available
            occupancy = clinic.get_population_size(treatment_template)
            self.clinic_rows.append(
                {
                    "Simulation Step": self.sim_step,
                    "Cycle Step": self.cycle_step,
                    "Cycle": cycle,
                    "Clinic ID": clinic.id,
                    "Clinic": clinic.get_complete_name(),
                    "Clinic Region": clinic.containing_region_name,
                    "Enabled": int(clinic.is_enabled()),
                    "Open": int(available > 0),
                    "Configured Capacity": configured,
                    "Available Capacity": available,
                    "Total Population": clinic.get_population_size(),
                    "Occupancy": occupancy,
                    "Admitted": clinic_admitted,
                    "Completed": clinic_completed,
                    "Unused Capacity": max(0, available - clinic_admitted),
                    "Utilization": (
                        clinic_admitted / available if available else 0.0
                    ),
                }
            )

        admission_lateness_total = sum(
            event["lateness"] * event["population"] for event in admissions
        )
        on_time_admissions = sum(
            event["population"] * event["on_time"] for event in admissions
        )
        self.step_rows.append(
            {
                "Simulation Step": self.sim_step,
                "Cycle Step": self.cycle_step,
                "Cycle": cycle,
                "Waiting": waiting,
                "Due Demand": admitted + unmet_due,
                "Unmet Due Demand": unmet_due,
                "Overdue": overdue,
                "In Treatment": in_treatment,
                "Admitted": admitted,
                "Completed": completed,
                "Available Capacity": available_capacity,
                "Used Capacity": admitted,
                "Unused Capacity": max(0, available_capacity - admitted),
                "Capacity Constrained": int(unmet_due > 0),
                "On Time Admissions": on_time_admissions,
                "On Time Rate": (
                    on_time_admissions / admitted if admitted else 0.0
                ),
                "Average Admission Lateness": (
                    admission_lateness_total / admitted
                    if admitted
                    else 0.0
                ),
                "Maximum Admission Lateness": (
                    max(
                        (event["lateness"] for event in admissions),
                        default=0,
                    )
                ),
            }
        )

    def _events_dataframe(self) -> pd.DataFrame:
        rows = [
            {
                "Simulation Step": event["simulation_step"],
                "Cycle Step": event["cycle_step"],
                "Cycle": event["cycle"],
                "Event": event["event_type"],
                "Population": event["population"],
                "Origin ID": event["origin_id"],
                "Origin": event["origin"],
                "Origin Region": event["origin_region"],
                "Clinic ID": event["clinic_id"],
                "Clinic": event["clinic"],
                "Clinic Region": event["clinic_region"],
                "Due Day": event["due_day"],
                "Treatment Frame": event["treatment_frame"],
                "Lateness": event["lateness"],
                "On Time": event["on_time"],
                "Distance": event["distance"],
            }
            for event in self.events
        ]
        return pd.DataFrame(rows, columns=self.EVENT_COLUMNS)

    def _cycle_dataframe(
        self, events_df: pd.DataFrame, step_df: pd.DataFrame
    ) -> pd.DataFrame:
        columns = [
            "Cycle",
            "Admissions",
            "Completed",
            "Returns",
            "Unique Origin-Clinic Flows",
            "Due Demand",
            "Unmet Due Demand",
            "Overdue End",
            "Available Capacity",
            "Used Capacity",
            "Unused Capacity",
            "Capacity Constrained Steps",
            "On Time Admissions",
            "On Time Rate",
            "Average Admission Lateness",
            "Maximum Admission Lateness",
            "Average Completed Distance",
            "Incomplete At Cycle End",
        ]
        if step_df.empty:
            return pd.DataFrame(columns=columns)

        rows = []
        for cycle, cycle_steps in step_df.groupby("Cycle", sort=True):
            cycle_events = events_df[events_df["Cycle"] == cycle]
            admitted_events = cycle_events[cycle_events["Event"] == "admitted"]
            completed_events = cycle_events[
                cycle_events["Event"] == "completed"
            ]
            admissions = int(admitted_events["Population"].sum())
            completed = int(completed_events["Population"].sum())
            weighted_lateness = (
                admitted_events["Lateness"] * admitted_events["Population"]
            ).sum()
            weighted_distance = (
                completed_events["Distance"] * completed_events["Population"]
            ).sum()
            rows.append(
                {
                    "Cycle": cycle,
                    "Admissions": admissions,
                    "Completed": completed,
                    "Returns": completed,
                    "Unique Origin-Clinic Flows": len(
                        admitted_events[["Origin", "Clinic"]].drop_duplicates()
                    ),
                    "Due Demand": int(cycle_steps["Due Demand"].sum()),
                    "Unmet Due Demand": int(
                        cycle_steps["Unmet Due Demand"].sum()
                    ),
                    "Overdue End": int(cycle_steps.iloc[-1]["Overdue"]),
                    "Available Capacity": int(
                        cycle_steps["Available Capacity"].sum()
                    ),
                    "Used Capacity": int(cycle_steps["Used Capacity"].sum()),
                    "Unused Capacity": int(
                        cycle_steps["Unused Capacity"].sum()
                    ),
                    "Capacity Constrained Steps": int(
                        cycle_steps["Capacity Constrained"].sum()
                    ),
                    "On Time Admissions": int(
                        admitted_events.loc[
                            admitted_events["On Time"] == 1, "Population"
                        ].sum()
                    ),
                    "On Time Rate": (
                        float(
                            admitted_events.loc[
                                admitted_events["On Time"] == 1, "Population"
                            ].sum()
                        )
                        / admissions
                        if admissions
                        else 0.0
                    ),
                    "Average Admission Lateness": (
                        float(weighted_lateness) / admissions
                        if admissions
                        else 0.0
                    ),
                    "Maximum Admission Lateness": (
                        int(admitted_events["Lateness"].max())
                        if not admitted_events.empty
                        else 0
                    ),
                    "Average Completed Distance": (
                        float(weighted_distance) / completed
                        if completed
                        else 0.0
                    ),
                    "Incomplete At Cycle End": int(
                        cycle_steps.iloc[-1]["In Treatment"]
                    ),
                }
            )
        return pd.DataFrame(rows, columns=columns)

    @staticmethod
    def _origin_clinic_dataframe(events_df: pd.DataFrame) -> pd.DataFrame:
        columns = [
            "Origin",
            "Clinic",
            "Admitted",
            "Completed",
            "Average Distance",
        ]
        if events_df.empty:
            return pd.DataFrame(columns=columns)
        admitted = events_df[events_df["Event"] == "admitted"]
        if admitted.empty:
            return pd.DataFrame(columns=columns)
        rows = []
        for (origin, clinic), group in admitted.groupby(
            ["Origin", "Clinic"], sort=True
        ):
            completed = events_df[
                (events_df["Event"] == "completed")
                & (events_df["Origin"] == origin)
                & (events_df["Clinic"] == clinic)
            ]
            population = int(group["Population"].sum())
            rows.append(
                {
                    "Origin": origin,
                    "Clinic": clinic,
                    "Admitted": population,
                    "Completed": int(completed["Population"].sum()),
                    "Average Distance": (
                        float((group["Distance"] * group["Population"]).sum())
                        / population
                        if population
                        else 0.0
                    ),
                }
            )
        return pd.DataFrame(rows, columns=columns)

    def _write_figure(self, figure, filename: str):
        figure.write_html(
            self.html_plots_path / f"{filename}.html",
            include_plotlyjs=True,
        )
        if self._png_export_available:
            try:
                figure.write_image(self.figures_path / f"{filename}.png")
            except Exception:
                # HTML and CSV output must remain available when image export
                # is installed but not operational in the current environment.
                self._png_export_available = False

    @staticmethod
    def _empty_figure(title: str):
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

    def _generate_plots(
        self,
        events_df: pd.DataFrame,
        step_df: pd.DataFrame,
        clinic_df: pd.DataFrame,
        cycle_df: pd.DataFrame,
        flow_df: pd.DataFrame,
    ):
        dashboard = make_subplots(specs=[[{"secondary_y": True}]])
        for column in ["Waiting", "In Treatment", "Admitted", "Completed"]:
            dashboard.add_trace(
                go.Scatter(
                    x=step_df["Simulation Step"],
                    y=step_df[column],
                    mode="lines",
                    name=column,
                ),
                secondary_y=False,
            )
        dashboard.add_trace(
            go.Scatter(
                x=step_df["Simulation Step"],
                y=step_df["On Time Rate"],
                mode="lines",
                name="On Time Rate",
            ),
            secondary_y=True,
        )
        dashboard.update_layout(title="Dialysis Dashboard")
        dashboard.update_yaxes(title_text="Population", secondary_y=False)
        dashboard.update_yaxes(title_text="Rate", secondary_y=True)
        self._write_figure(dashboard, "dashboard")

        utilization = (
            px.line(
                clinic_df,
                x="Simulation Step",
                y=[
                    "Occupancy",
                    "Admitted",
                    "Available Capacity",
                    "Utilization",
                ],
                facet_row="Clinic",
                title="Clinic Occupancy, Capacity, and Utilization",
            )
            if not clinic_df.empty
            else self._empty_figure(
                "Clinic Occupancy, Capacity, and Utilization"
            )
        )
        self._write_figure(utilization, "clinic_utilization")

        daily = (
            px.bar(
                clinic_df.groupby(["Cycle", "Clinic"], as_index=False)[
                    "Completed"
                ].sum(),
                x="Cycle",
                y="Completed",
                color="Clinic",
                title="Completed Dialysis Treatments by Clinic and Day",
            )
            if not clinic_df.empty
            else self._empty_figure(
                "Completed Dialysis Treatments by Clinic and Day"
            )
        )
        self._write_figure(daily, "daily_completed_by_clinic")

        labels = list(
            dict.fromkeys(
                flow_df.get("Origin", pd.Series(dtype=str)).tolist()
                + flow_df.get("Clinic", pd.Series(dtype=str)).tolist()
            )
        )
        label_index = {label: index for index, label in enumerate(labels)}
        sankey = go.Figure(
            go.Sankey(
                node={"label": labels},
                link={
                    "source": [
                        label_index[value] for value in flow_df["Origin"]
                    ],
                    "target": [
                        label_index[value] for value in flow_df["Clinic"]
                    ],
                    "value": flow_df["Admitted"].tolist(),
                },
            )
        )
        sankey.update_layout(title="Dialysis Origin-to-Clinic Flows")
        self._write_figure(sankey, "origin_clinic_sankey")

        if flow_df.empty:
            heatmap = self._empty_figure(
                "Dialysis Origin × Clinic Flow"
            )
        else:
            heatmap_data = flow_df.pivot(
                index="Origin", columns="Clinic", values="Admitted"
            ).fillna(0)
            heatmap = px.imshow(
                heatmap_data,
                text_auto=True,
                aspect="auto",
                title="Dialysis Origin × Clinic Flow",
            )
        self._write_figure(heatmap, "origin_clinic_heatmap")

        hourly = px.bar(
            step_df.groupby("Cycle Step", as_index=False)["Due Demand"].mean(),
            x="Cycle Step",
            y="Due Demand",
            title="Mean Dialysis Demand by Cycle Step",
        )
        self._write_figure(hourly, "demand_by_cycle_step")

        admissions = events_df[events_df["Event"] == "admitted"]
        lateness = px.histogram(
            admissions,
            x="Lateness",
            y="Population",
            histfunc="sum",
            title="Dialysis Waiting Lateness",
        )
        self._write_figure(lateness, "waiting_lateness")

        completed = events_df[events_df["Event"] == "completed"]
        distance = px.histogram(
            completed,
            x="Distance",
            y="Population",
            color="Clinic",
            histfunc="sum",
            title="Travel Distance by Clinic",
        )
        self._write_figure(distance, "travel_distance")

        coordinates = {}
        for node in self.env_graph.node_list:
            if (
                len(node.long_lat) >= 2
                and -180 <= node.long_lat[0] <= 180
                and -90 <= node.long_lat[1] <= 90
            ):
                coordinates[node.get_complete_name()] = node.long_lat
        if not flow_df.empty and any(
            coordinates.get(name, [0, 0]) != [0, 0]
            for name in set(flow_df["Origin"]) | set(flow_df["Clinic"])
        ):
            geographic = go.Figure()
            for row in flow_df.itertuples(index=False):
                origin_position = coordinates.get(row.Origin)
                clinic_position = coordinates.get(row.Clinic)
                if origin_position is None or clinic_position is None:
                    continue
                geographic.add_trace(
                    go.Scattergeo(
                        lon=[origin_position[0], clinic_position[0]],
                        lat=[origin_position[1], clinic_position[1]],
                        mode="lines+markers",
                        line={"width": max(1, row.Admitted)},
                        name=f"{row.Origin} → {row.Clinic}",
                    )
                )
            geographic.update_layout(title="Dialysis Geographic Flows")
            self._write_figure(geographic, "geographic_flows")

    def stop_logger(self):
        self.setup_logger()
        events_df = self._events_dataframe()
        step_df = pd.DataFrame(self.step_rows, columns=self.STEP_COLUMNS)
        clinic_df = pd.DataFrame(
            self.clinic_rows, columns=self.CLINIC_COLUMNS
        )
        cycle_df = self._cycle_dataframe(events_df, step_df)
        flow_df = self._origin_clinic_dataframe(events_df)

        outputs = {
            "dialysis_events.csv": events_df,
            "dialysis_step.csv": step_df,
            "dialysis_clinic_step.csv": clinic_df,
            "dialysis_cycle.csv": cycle_df,
            "dialysis_origin_clinic.csv": flow_df,
        }
        for filename, dataframe in outputs.items():
            dataframe.to_csv(
                self.data_frames_path / filename,
                sep=";",
                encoding="utf-8-sig",
                index=False,
            )

        self._generate_plots(
            events_df, step_df, clinic_df, cycle_df, flow_df
        )

    def unload_plugin(self):
        if hasattr(self, "dialysis_plugin"):
            self.dialysis_plugin.remove_event_listener(
                self.__class__.__name__
            )
