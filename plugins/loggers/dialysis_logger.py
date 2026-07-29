"""Dialysis-specific event, state, aggregate, and visualization logger."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

import pandas as pd

from core.plugin import LoggerPlugin
from core.population import PopulationTemplate
from core.simulator import LodusSimulation
from plugins.loggers.visualizations.dialysis_visualizations import (
    generate_dialysis_visualizations,
)

if TYPE_CHECKING:
    from plugins.time_actions.dialysis_plugin import DialysisPlugin


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
    LOCATION_COLUMNS = [
        "Node ID",
        "Complete Name",
        "Display Name",
        "Longitude",
        "Latitude",
        "Is Clinic",
    ]

    def __init__(self, export_png: bool = True):
        self.export_png = export_png
        self.events: list[dict] = []
        self.step_rows: list[dict] = []
        self.clinic_rows: list[dict] = []
        self.sim_step = 0
        self.cycle_step = 0

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
        self.dialysis_plugin = cast(
            "DialysisPlugin",
            dialysis_plugins[0],
        )
        self.cycle_length = simulation.time_status.cycle_length
        self.base_path = Path("output_logs") / simulation.experiment_name
        self.data_frames_path = self.base_path / "data_frames"
        self.dialysis_plugin.add_event_listener(
            self.__class__.__name__, self._log_event
        )

    def setup_logger(self):
        self.data_frames_path.mkdir(parents=True, exist_ok=True)

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

    def _locations_dataframe(self) -> pd.DataFrame:
        clinic_ids = set(self.dialysis_plugin.clinic_schedules)
        relevant_ids = clinic_ids | {
            event["origin_id"] for event in self.events
        }
        clinic_name_attribute = getattr(
            self.dialysis_plugin,
            "clinic_name_attribute",
            "clinic_name",
        )
        rows = []
        for node_id in sorted(relevant_ids):
            node = self.env_graph.get_node_by_id(node_id)
            complete_name = node.get_complete_name()
            is_clinic = node_id in clinic_ids
            clinic_name = (
                node.attributes.get(clinic_name_attribute)
                if is_clinic
                else None
            )
            display_name = (
                f"{clinic_name} ({complete_name})"
                if clinic_name and clinic_name != complete_name
                else complete_name
            )
            longitude = node.long_lat[0] if len(node.long_lat) >= 2 else None
            latitude = node.long_lat[1] if len(node.long_lat) >= 2 else None
            rows.append(
                {
                    "Node ID": node.id,
                    "Complete Name": complete_name,
                    "Display Name": display_name,
                    "Longitude": longitude,
                    "Latitude": latitude,
                    "Is Clinic": int(is_clinic),
                }
            )
        return pd.DataFrame(rows, columns=self.LOCATION_COLUMNS)

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
            "dialysis_locations.csv": self._locations_dataframe(),
        }
        for filename, dataframe in outputs.items():
            dataframe.to_csv(
                self.data_frames_path / filename,
                sep=";",
                encoding="utf-8-sig",
                index=False,
            )

        generate_dialysis_visualizations(
            self.base_path,
            export_png=self.export_png,
        )

    def unload_plugin(self):
        if hasattr(self, "dialysis_plugin"):
            self.dialysis_plugin.remove_event_listener(
                self.__class__.__name__
            )
