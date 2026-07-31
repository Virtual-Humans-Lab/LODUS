"""Inpatient-care event, occupancy, queue, and regional logger."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

import pandas as pd

from core.plugin import LoggerPlugin
from core.simulator import LodusSimulation
from plugins.loggers.visualizations.inpatient_care_visualizations import (
    generate_inpatient_care_visualizations,
)

if TYPE_CHECKING:
    from plugins.time_actions.inpatient_care_plugin import InpatientCarePlugin


class InpatientCareLogger(LoggerPlugin):
    EVENT_COLUMNS = [
        "Simulation Step",
        "Cycle Step",
        "Cycle",
        "Event",
        "Population",
        "Demand ID",
        "CID",
        "Origin ID",
        "Origin",
        "Origin Region",
        "Hospital ID",
        "Hospital",
        "Hospital Region",
        "Preferred Hospital",
        "Specialty",
        "Bed Type",
        "Payer",
        "Request Step",
        "Admission Step",
        "Discharge Step",
        "Length Of Stay",
        "Admission Delay Steps",
        "Distance Km",
    ]
    STEP_COLUMNS = [
        "Simulation Step",
        "Cycle Step",
        "Cycle",
        "Global Population",
        "Population Delta From Initial",
        "New Demand",
        "Admitted",
        "Discharged",
        "Rerouted",
        "Waiting",
        "Occupancy",
        "Configured Capacity",
        "Overflow",
        "Capacity Constrained",
        "Average Admission Delay Steps",
        "Maximum Admission Delay Steps",
    ]
    BED_COLUMNS = [
        "Simulation Step",
        "Cycle Step",
        "Cycle",
        "Hospital ID",
        "Hospital",
        "Region",
        "Specialty",
        "Bed Type",
        "Payer",
        "Configured Capacity",
        "Occupancy",
        "Available Capacity",
        "Overflow",
        "Utilization",
        "Admitted",
        "Discharged",
        "Synthetic Capacity",
    ]
    REGION_COLUMNS = [
        "Simulation Step",
        "Cycle Step",
        "Cycle",
        "Region",
        "Configured Capacity",
        "Occupancy",
        "Available Capacity",
        "Overflow",
        "Utilization",
        "Waiting Origin Demand",
    ]
    LOCATION_COLUMNS = [
        "Hospital ID",
        "Hospital",
        "Complete Name",
        "Region",
        "Longitude",
        "Latitude",
    ]

    def __init__(
        self,
        export_png: bool = True,
        generate_plots: bool = True,
    ):
        self.export_png = export_png
        self.generate_plots = generate_plots
        self.events: list[dict] = []
        self.step_rows: list[dict] = []
        self.bed_rows: list[dict] = []
        self.region_rows: list[dict] = []
        self.sim_step = 0
        self.cycle_step = 0

    def load_plugin(self, simulation: LodusSimulation):
        plugins = [
            plugin
            for plugin in simulation.plugin_controller.loaded_action_plugins
            if getattr(plugin, "ACTION_TYPE", None) == "inpatient_care"
            and callable(getattr(plugin, "add_event_listener", None))
        ]
        if not plugins:
            raise ValueError(
                "InpatientCareLogger requires InpatientCarePlugin to be "
                "loaded first"
            )
        self.simulation = simulation
        self.env_graph = simulation.env_graph
        self.inpatient_care_plugin = cast(
            "InpatientCarePlugin", plugins[0]
        )
        self.cycle_length = simulation.time_status.cycle_length
        self.initial_global_population = self.env_graph.get_population_size()
        self.base_path = Path("output_logs") / simulation.experiment_name
        self.data_frames_path = self.base_path / "data_frames"
        self.inpatient_care_plugin.add_event_listener(
            self.__class__.__name__, self._log_event
        )

    def setup_logger(self):
        self.data_frames_path.mkdir(parents=True, exist_ok=True)

    def update_time_step(self, cycle_step: int, simulation_step: int):
        self.cycle_step = cycle_step
        self.sim_step = simulation_step

    def _log_event(self, event: dict):
        event["admission_delay_steps"] = (
            max(0, event["admission_step"] - event["request_step"])
            if event["admission_step"] >= 0
            else None
        )
        self.events.append(event)

    def _events_for_step(
        self,
        event_type: str,
        hospital_id: int | None = None,
        specialty: str | None = None,
        bed_type: str | None = None,
        payer: str | None = None,
    ) -> list[dict]:
        return [
            event
            for event in self.events
            if event["simulation_step"] == self.sim_step
            and event["event_type"] == event_type
            and (
                hospital_id is None
                or event["hospital_id"] == hospital_id
            )
            and (specialty is None or event["specialty"] == specialty)
            and (bed_type is None or event["bed_type"] == bed_type)
            and (payer is None or event["payer"] == payer)
        ]

    @staticmethod
    def _population(events: list[dict]) -> int:
        return sum(event["population"] for event in events)

    def log_simulation_step(self):
        cycle = self.sim_step // self.cycle_length
        admissions = self._events_for_step("admitted")
        discharges = self._events_for_step("discharged")
        reroutes = self._events_for_step("rerouted")
        admitted = self._population(admissions)
        delays = [
            (event["admission_delay_steps"], event["population"])
            for event in admissions
        ]

        configured_capacity = 0
        occupancy = 0
        overflow = 0
        bed_rows_for_step = []
        for (node_id, specialty, bed_type), capacity in sorted(
            self.inpatient_care_plugin.capacities.items(),
            key=lambda item: (
                item[1].region,
                item[1].hospital,
                item[1].specialty,
                item[1].bed_type,
            ),
        ):
            hospital = self.env_graph.get_node_by_id(node_id)
            payer_rows = []
            for payer in ("sus", "private"):
                payer_capacity = (
                    self.inpatient_care_plugin.configured_capacity(
                        node_id, specialty, bed_type, payer
                    )
                )
                payer_occupancy = self.inpatient_care_plugin.occupancy(
                    node_id, specialty, bed_type, payer
                )
                payer_rows.append((payer, payer_capacity, payer_occupancy))
            payer_rows.append(
                (
                    "total",
                    sum(row[1] for row in payer_rows),
                    sum(row[2] for row in payer_rows),
                )
            )
            for payer, payer_capacity, payer_occupancy in payer_rows:
                admitted_events = self._events_for_step(
                    "admitted",
                    node_id,
                    specialty,
                    bed_type,
                    None if payer == "total" else payer,
                )
                discharged_events = self._events_for_step(
                    "discharged",
                    node_id,
                    specialty,
                    bed_type,
                    None if payer == "total" else payer,
                )
                row = {
                    "Simulation Step": self.sim_step,
                    "Cycle Step": self.cycle_step,
                    "Cycle": cycle,
                    "Hospital ID": node_id,
                    "Hospital": capacity.hospital,
                    "Region": capacity.region,
                    "Specialty": specialty,
                    "Bed Type": bed_type,
                    "Payer": payer,
                    "Configured Capacity": payer_capacity,
                    "Occupancy": payer_occupancy,
                    "Available Capacity": max(
                        0, payer_capacity - payer_occupancy
                    ),
                    "Overflow": max(
                        0, payer_occupancy - payer_capacity
                    ),
                    "Utilization": (
                        payer_occupancy / payer_capacity
                        if payer_capacity
                        else 0.0
                    ),
                    "Admitted": self._population(admitted_events),
                    "Discharged": self._population(discharged_events),
                    "Synthetic Capacity": int(capacity.synthetic),
                }
                self.bed_rows.append(row)
                bed_rows_for_step.append(row)
                if payer in {"sus", "private"}:
                    configured_capacity += payer_capacity
                    occupancy += payer_occupancy
                    overflow += max(
                        0, payer_occupancy - payer_capacity
                    )

        waiting_by_region = self._waiting_by_origin_region()
        regions = sorted(
            {row["Region"] for row in bed_rows_for_step}
            | set(waiting_by_region)
        )
        for region in regions:
            rows = [
                row
                for row in bed_rows_for_step
                if row["Region"] == region and row["Payer"] == "total"
            ]
            region_capacity = sum(
                row["Configured Capacity"] for row in rows
            )
            region_occupancy = sum(row["Occupancy"] for row in rows)
            self.region_rows.append(
                {
                    "Simulation Step": self.sim_step,
                    "Cycle Step": self.cycle_step,
                    "Cycle": cycle,
                    "Region": region,
                    "Configured Capacity": region_capacity,
                    "Occupancy": region_occupancy,
                    "Available Capacity": max(
                        0, region_capacity - region_occupancy
                    ),
                    "Overflow": sum(row["Overflow"] for row in rows),
                    "Utilization": (
                        region_occupancy / region_capacity
                        if region_capacity
                        else 0.0
                    ),
                    "Waiting Origin Demand": waiting_by_region.get(
                        region, 0
                    ),
                }
            )

        weighted_delay = sum(delay * pop for delay, pop in delays)
        self.step_rows.append(
            {
                "Simulation Step": self.sim_step,
                "Cycle Step": self.cycle_step,
                "Cycle": cycle,
                "Global Population": self.env_graph.get_population_size(),
                "Population Delta From Initial": (
                    self.env_graph.get_population_size()
                    - self.initial_global_population
                ),
                "New Demand": (
                    self.inpatient_care_plugin.new_demand_by_step.get(
                        self.sim_step, 0
                    )
                ),
                "Admitted": admitted,
                "Discharged": self._population(discharges),
                "Rerouted": self._population(reroutes),
                "Waiting": self.inpatient_care_plugin.waiting_population(),
                "Occupancy": occupancy,
                "Configured Capacity": configured_capacity,
                "Overflow": overflow,
                "Capacity Constrained": int(
                    self.inpatient_care_plugin.waiting_population() > 0
                ),
                "Average Admission Delay Steps": (
                    weighted_delay / admitted if admitted else 0.0
                ),
                "Maximum Admission Delay Steps": max(
                    (delay for delay, _ in delays), default=0
                ),
            }
        )

    def _waiting_by_origin_region(self) -> dict[str, int]:
        result: dict[str, int] = {}
        plugin = self.inpatient_care_plugin
        for node in self.env_graph.get_nodes_by_type(
            plugin.patient_origin_node_type
        ):
            for blob in node.contained_blobs:
                if (
                    blob.get_traceable_characteristic(plugin.PATIENT)
                    and blob.get_traceable_characteristic(plugin.STATUS)
                    == "waiting"
                ):
                    region = node.containing_region_name
                    result[region] = (
                        result.get(region, 0)
                        + blob.get_population_size()
                    )
        return result

    def _events_dataframe(self) -> pd.DataFrame:
        rows = []
        for event in self.events:
            rows.append(
                {
                    "Simulation Step": event["simulation_step"],
                    "Cycle Step": event["cycle_step"],
                    "Cycle": event["cycle"],
                    "Event": event["event_type"],
                    "Population": event["population"],
                    "Demand ID": event["demand_id"],
                    "CID": event["cid"],
                    "Origin ID": event["origin_id"],
                    "Origin": event["origin"],
                    "Origin Region": event["origin_region"],
                    "Hospital ID": event["hospital_id"],
                    "Hospital": event["hospital"],
                    "Hospital Region": event["hospital_region"],
                    "Preferred Hospital": event[
                        "preferred_hospital"
                    ],
                    "Specialty": event["specialty"],
                    "Bed Type": event["bed_type"],
                    "Payer": event["payer"],
                    "Request Step": event["request_step"],
                    "Admission Step": event["admission_step"],
                    "Discharge Step": event["discharge_step"],
                    "Length Of Stay": event["length_of_stay"],
                    "Admission Delay Steps": event[
                        "admission_delay_steps"
                    ],
                    "Distance Km": event["distance_km"],
                }
            )
        return pd.DataFrame(rows, columns=self.EVENT_COLUMNS)

    def _locations_dataframe(self) -> pd.DataFrame:
        rows = []
        for name, node in sorted(
            self.inpatient_care_plugin.hospital_nodes.items()
        ):
            rows.append(
                {
                    "Hospital ID": node.id,
                    "Hospital": name,
                    "Complete Name": node.get_complete_name(),
                    "Region": node.containing_region_name,
                    "Longitude": node.long_lat[0],
                    "Latitude": node.long_lat[1],
                }
            )
        return pd.DataFrame(rows, columns=self.LOCATION_COLUMNS)

    def stop_logger(self):
        self.setup_logger()
        outputs = {
            "inpatient_events.csv": self._events_dataframe(),
            "inpatient_step.csv": pd.DataFrame(
                self.step_rows, columns=self.STEP_COLUMNS
            ),
            "inpatient_bed_step.csv": pd.DataFrame(
                self.bed_rows, columns=self.BED_COLUMNS
            ),
            "inpatient_region_step.csv": pd.DataFrame(
                self.region_rows, columns=self.REGION_COLUMNS
            ),
            "inpatient_locations.csv": self._locations_dataframe(),
        }
        for filename, dataframe in outputs.items():
            dataframe.to_csv(
                self.data_frames_path / filename,
                sep=";",
                encoding="utf-8-sig",
                index=False,
            )
        if self.generate_plots:
            generate_inpatient_care_visualizations(
                self.base_path, export_png=self.export_png
            )

    def unload_plugin(self):
        if hasattr(self, "inpatient_care_plugin"):
            self.inpatient_care_plugin.remove_event_listener(
                self.__class__.__name__
            )
