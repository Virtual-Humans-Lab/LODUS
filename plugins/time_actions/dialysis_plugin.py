"""Hourly dialysis demand, clinic capacity, treatment, and return movement."""

from __future__ import annotations

import csv
from pathlib import Path
import time
from typing import Callable

from core import environment
from core.plugin import ActionPlugin
from core.population import PopulationTemplate
from core.routine import Action
from core.simulator import LodusSimulation
from util.math import pyproj_distance_metre
from util.random_instance import FixedRandom


class DialysisPlugin(ActionPlugin):
    """Models recurring dialysis demand with traceable population state.

    Experiment configuration example::

        "dialysis_plugin": {
            "patient_count": 120,
            "treatment_frequency_days": 3,
            "patient_node_type": "home",
            "max_patients_per_node": 20,
            "clinic_data_file": "dialysis_clinics/opening_hours.csv",
            "default_values": {
                "opening_step": 6,
                "closing_step": 18,
                "treatment_capacity_per_step": 2
            }
        }

    The optional clinic CSV must contain ``clinic_name``, ``opening_frame``,
    ``closing_frame``, and ``treatment_capacity_per_frame``. Clinic names are
    matched against the ``clinic_name`` attribute of ``dialysis_clinic`` nodes.
    CSV values override ``default_values`` for matching clinics. At least one
    of ``clinic_data_file`` and ``default_values`` must be configured.
    """

    ACTION_TYPE = "dialysis"
    PATIENT = "dialysis_patient"
    FREQUENCY = "dialysis_frequency_days"
    NEXT_DUE = "dialysis_next_due_day"
    STATUS = "dialysis_status"
    ORIGIN = "dialysis_origin_node"
    TREATMENT_FRAME = "dialysis_treatment_frame"

    CLINIC_NODE_TYPE = "dialysis_clinic"
    CLINIC_NAME_ATTRIBUTE = "clinic_name"
    PATIENT_HOME_NODE_TYPE = "home"

    def __init__(self):
        super().__init__()
        self._header = "Dialysis Plugin:"
        self.simulation: LodusSimulation
        self.env_graph:environment.EnvironmentGraph
        self.clinic_schedules = {}
        self._event_callbacks: dict[str, Callable[[dict], None]] = {}
        self.new_due_sessions_by_step: dict[int, int] = {}

    def add_event_listener(self, name: str, callback: Callable[[dict], None]):
        """Registers a listener for dialysis admission and completion events."""
        self._event_callbacks[name] = callback

    def remove_event_listener(self, name: str):
        """Removes a previously registered dialysis event listener."""
        self._event_callbacks.pop(name, None)

    def _emit_event(
        self,
        event_type: str,
        origin,
        clinic,
        blob,
        cycle_step: int,
        simulation_step: int,
    ):
        due_day = blob.get_traceable_characteristic(self.NEXT_DUE)
        due_step = due_day * self.simulation.time_status.cycle_length
        admission_step = (
            simulation_step
            if event_type == "admitted"
            else blob.get_traceable_characteristic(self.TREATMENT_FRAME) - 1
        )
        event = {
            "simulation_step": simulation_step,
            "cycle_step": cycle_step,
            "cycle": (
                simulation_step // self.simulation.time_status.cycle_length
            ),
            "event_type": event_type,
            "population": blob.get_population_size(),
            "origin_id": origin.id,
            "origin": origin.get_complete_name(),
            "origin_region": origin.containing_region_name,
            "clinic_id": clinic.id,
            "clinic": clinic.get_complete_name(),
            "clinic_region": clinic.containing_region_name,
            "due_day": due_day,
            "due_step": due_step,
            "admission_step": admission_step,
            "admission_delay_steps": max(0, admission_step - due_step),
            "treatment_frame": blob.get_traceable_characteristic(
                self.TREATMENT_FRAME
            ),
            "distance": self._distance(origin, clinic) / 1000,
        }
        for callback in tuple(self._event_callbacks.values()):
            callback(event.copy())

    def load_plugin(self, simulation: LodusSimulation):
        self.simulation = simulation
        self.env_graph = simulation.env_graph
        simulation.add_action_type_to_function(self.ACTION_TYPE, self.dialysis, True)

        self.config:dict = simulation.experiment_config.get("dialysis_plugin", {})
        self.patient_count = self._positive_int(
            self.config.get("patient_count",self.config.get("dialysis_patient_count", 0),),
            "patient_count",
            allow_zero=True,
        )
        self.frequency_days = self._positive_int(
            self.config.get("treatment_frequency_days",self.config.get("treatment_frequency", 1),),
            "treatment_frequency_days",
        )

        self.patient_node_type = self.config.get(
            "patient_node_type",
            self.config.get("patient_home_node_type", self.PATIENT_HOME_NODE_TYPE),
        )
        self.max_patients_per_node = self._positive_int(
            self.config.get(
                "max_patients_per_node",
                max(1, self.patient_count),
            ),
            "max_patients_per_node",
        )
        self.clinic_node_type = self.config.get("clinic_node_type", self.CLINIC_NODE_TYPE)
        self.clinic_name_attribute = self.config.get("clinic_name_attribute", self.CLINIC_NAME_ATTRIBUTE)
        self.default_values = self.config.get("default_values", {})
        data_file = self.config.get("clinic_data_file", self.config.get("data_file"))

        self._add_traceable_defaults()
        self.clinic_schedules = self._load_clinic_schedules(data_file)
        self._select_patients()

    def update_time_step(self, cycle_step: int, simulation_step: int):
        if self.simulation is None:
            return
        self.simulation.direct_action_invoke(Action(self.ACTION_TYPE, PopulationTemplate(), {}),cycle_step,simulation_step,)

    def unload_plugin(self):
        self._event_callbacks.clear()
        self.clinic_schedules = {}
        self.new_due_sessions_by_step = {}

    def _add_traceable_defaults(self):
        defaults = {
            self.PATIENT: False,
            self.FREQUENCY: 0,
            self.NEXT_DUE: -1,
            self.STATUS: "not_required",
            self.ORIGIN: -1,
            self.TREATMENT_FRAME: -1,
        }
        for key, value in defaults.items():
            self.env_graph.add_blobs_traceable_property(key, value)

    
    def _load_clinic_schedules(self, configured_path):
        """Builds schedules for simulation clinics from CSV data and defaults."""
        schedule_fields = {
            "opening_step",
            "closing_step",
            "treatment_capacity_per_step",
        }
        defaults = self.default_values or {}
        if not configured_path and not defaults:
            raise ValueError(
                "dialysis_plugin requires either 'clinic_data_file' or "
                "'default_values'"
            )
        missing_defaults = schedule_fields.difference(defaults)
        if defaults and missing_defaults:
            raise ValueError(f"Dialysis clinic default_values is missing fields: {sorted(missing_defaults)}")

        clinics_by_name = {}
        clinics = []
        for node in self.env_graph.node_list:
            if node.node_type != self.clinic_node_type:
                continue
            clinics.append(node)
            name = node.attributes.get(self.clinic_name_attribute)
            if name:
                clinics_by_name[name] = node
            clinics_by_name[node.get_complete_name()] = node

        rows = []
        path = None
        if configured_path:
            path = Path(configured_path)
            if not path.is_absolute():
                path = Path(__file__).resolve().parents[2] / "data_input" / path

            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                sample = handle.read(4096)
                handle.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\\t")
                except csv.Error:
                    dialect = csv.excel
                reader = csv.DictReader(handle, dialect=dialect)
                fieldnames = set(reader.fieldnames or [])
                if "clinic_name" not in fieldnames:
                    raise ValueError(
                        "Dialysis clinic data is missing columns: ['clinic_name']"
                    )
                unresolved = schedule_fields.difference(
                    fieldnames | set(defaults)
                )
                if unresolved:
                    raise ValueError(
                        "Dialysis clinic data is missing columns without "
                        f"defaults: {sorted(unresolved)}"
                    )
                rows = list(reader)

        schedules = {}
        for row in rows:
            name = row["clinic_name"].strip()
            if name not in clinics_by_name:
                raise ValueError(f"Clinic '{name}' from {path} was not found in the environment")
            node = clinics_by_name[name]
            schedules.setdefault(node.id, []).append(
                self._parse_schedule(row, defaults)
            )

        if defaults:
            default_schedule = self._parse_schedule(defaults)
            for clinic in clinics:
                schedules.setdefault(clinic.id, [default_schedule])
        return schedules

    def _parse_schedule(self, values, fallbacks=None):
        fallbacks = fallbacks or {}

        def resolved(field):
            value = values.get(field)
            if value is None or str(value).strip() == "":
                value = fallbacks.get(field)
            if value is None or str(value).strip() == "":
                raise ValueError(
                    f"Dialysis clinic schedule is missing '{field}'"
                )
            return value

        return (
            self._hour(resolved("opening_step"), "opening_step"),
            self._hour(resolved("closing_step"), "closing_step"),
            self._positive_int(
                resolved("treatment_capacity_per_step"),
                "treatment_capacity_per_step",
                allow_zero=True,
            ),
        )


    def _select_patients(self):
        """Selects the configured number of dialysis patients from the configured node type."""
        nodes = [node for node in self.env_graph.node_list if node.node_type == self.patient_node_type]
        available_nonpatients = PopulationTemplate(traceable_characteristics={self.PATIENT: False})
        selection_capacity = sum(
            min(self.max_patients_per_node,node.get_population_size(available_nonpatients)) 
            for node in nodes
        )

        if self.patient_count > selection_capacity:
            raise ValueError(
                f"dialysis patient_count ({self.patient_count}) exceeds the "
                f"selection capacity ({selection_capacity}) of "
                f"'{self.patient_node_type}' nodes with "
                f"max_patients_per_node={self.max_patients_per_node}"
            )

        FixedRandom.instance.shuffle(nodes)

        phase_counts = [
            (self.patient_count + self.frequency_days - phase - 1)
            // self.frequency_days
            for phase in range(self.frequency_days)
        ]
        for phase, phase_count in enumerate(phase_counts):
            remaining = phase_count
            for node in nodes:
                if remaining == 0:
                    break
                current_patients = node.get_population_size(PopulationTemplate(traceable_characteristics={self.PATIENT: True}))
                
                remaining_node_capacity = (self.max_patients_per_node - current_patients)
                quantity = min(remaining, remaining_node_capacity, node.get_population_size(available_nonpatients))

                if quantity == 0:
                    continue
                print("Selecting", quantity, "patients from node", node.get_complete_name(), "for phase", phase)
                blobs = node.grab_population(quantity, available_nonpatients)
                for blob in blobs:
                    blob.set_traceable_characteristic(self.PATIENT, True)
                    blob.set_traceable_characteristic(self.FREQUENCY, self.frequency_days)
                    blob.set_traceable_characteristic(self.NEXT_DUE, phase)
                    blob.set_traceable_characteristic(self.STATUS, "waiting")
                    node.add_blob(blob)
                remaining -= quantity


    def dialysis(
            self,
            pop_template: PopulationTemplate,
            values: dict,
            cycle_step: int,
            simulation_step: int,
        ):
            """Treat last frame's arrivals, return them, then admit this hour's demand."""
            started = time.perf_counter()
            self._record_new_due_sessions(cycle_step, simulation_step)
            self._complete_treatments(cycle_step, simulation_step)
            self._dispatch_due_patients(cycle_step, simulation_step)
            self.add_execution_time(self.ACTION_TYPE, time.perf_counter() - started)

    def _record_new_due_sessions(
        self, cycle_step: int, simulation_step: int
    ) -> None:
        if cycle_step != 0:
            self.new_due_sessions_by_step[simulation_step] = 0
            return
        current_day = (
            simulation_step // self.simulation.time_status.cycle_length
        )
        template = PopulationTemplate(
            traceable_characteristics={
                self.PATIENT: True,
                self.NEXT_DUE: current_day,
            }
        )
        self.new_due_sessions_by_step[simulation_step] = (
            self.env_graph.get_population_size(template)
        )

    def _complete_treatments(self, cycle_step: int, simulation_step: int):
        """Completes treatment for patients who were admitted in the previous simulation step 
        and returns them to their origin nodes."""
        template = PopulationTemplate(
            traceable_characteristics={
                self.PATIENT: True,
                self.STATUS: "in_treatment",
                self.TREATMENT_FRAME: simulation_step,
            }
        )
        current_day = (
            simulation_step // self.simulation.time_status.cycle_length
        )
        for clinic_id in self.clinic_schedules:
            clinic = self.env_graph.get_node_by_id(clinic_id)
            for blob in list(clinic.contained_blobs):
                if blob.get_population_size(template) == 0:
                    continue
                origin_id = blob.get_traceable_characteristic(self.ORIGIN)
                origin = self.env_graph.get_node_by_id(origin_id)
                clinic.remove_blob(blob)
                self._emit_event(
                    "completed",
                    origin,
                    clinic,
                    blob,
                    cycle_step,
                    simulation_step,
                )
                blob.set_traceable_characteristic(
                    self.NEXT_DUE,
                    current_day
                    + blob.get_traceable_characteristic(self.FREQUENCY),
                )
                blob.set_traceable_characteristic(self.STATUS, "waiting")
                blob.set_traceable_characteristic(self.ORIGIN, -1)
                blob.set_traceable_characteristic(self.TREATMENT_FRAME, -1)
                self.env_graph.log_blob_movement(clinic, origin, [blob])
                # print(f"Returning {blob.get_population_size()} patients in {blob.blob_id} from clinic {clinic.get_complete_name()} to origin {origin.get_complete_name()}")
                origin.add_blob(blob)

    def _dispatch_due_patients(self, cycle_step: int, simulation_step: int):
        """Dispatches patients who are due for treatment to open clinics."""
        current_day = (
            simulation_step // self.simulation.time_status.cycle_length
        )
        open_slots = []
        for clinic_id, schedules in self.clinic_schedules.items():
            clinic = self.env_graph.get_node_by_id(clinic_id)
            if not clinic.is_enabled():
                continue
            capacity = sum(cap for opening, closing, cap in schedules if self._is_open(cycle_step, opening, closing))
            if capacity > 0:
                open_slots.append([clinic, capacity])

        due = PopulationTemplate(
            traceable_characteristics={
                self.PATIENT: True,
                self.STATUS: "waiting",
                self.NEXT_DUE: lambda day: day <= current_day,
            }
        )
        origins = list(self.env_graph.node_list)
        FixedRandom.instance.shuffle(origins)

        for origin in origins:
            while origin.get_population_size(due) > 0 and open_slots:
                clinic_slot = min(
                    open_slots,
                    key=lambda item: self._distance(origin, item[0]),
                )
                clinic, capacity = clinic_slot
                quantity = min(capacity, origin.get_population_size(due))
                blobs = origin.grab_population(quantity, due)
                for blob in blobs:
                    blob.set_traceable_characteristic(
                        self.STATUS, "in_treatment"
                    )
                    blob.set_traceable_characteristic(self.ORIGIN, origin.id)
                    blob.set_traceable_characteristic(
                        self.TREATMENT_FRAME, simulation_step + 1
                    )
                    self._emit_event(
                        "admitted",
                        origin,
                        clinic,
                        blob,
                        cycle_step,
                        simulation_step,
                    )
                self.env_graph.log_blob_movement(origin, clinic, blobs)
                clinic.add_blobs(blobs)
                clinic_slot[1] -= quantity
                if clinic_slot[1] == 0:
                    open_slots.remove(clinic_slot)
                # print("Dispatching", quantity, "patients from origin", origin.get_complete_name(), "to clinic", clinic.get_complete_name())

    @staticmethod
    def _distance(node_a, node_b):
        return pyproj_distance_metre(node_a.long_lat, node_b.long_lat)

    @staticmethod
    def _is_open(hour: int, opening: int, closing: int):
        if opening == closing:
            return True
        if opening < closing:
            return opening <= hour < closing
        return hour >= opening or hour < closing

    @staticmethod
    def _hour(value, name):
        hour = int(value)
        if hour < 0 or hour > 23:
            raise ValueError(f"{name} must be between 0 and 23")
        return hour

    @staticmethod
    def _positive_int(value, name, allow_zero=False):
        number = int(value)
        minimum = 0 if allow_zero else 1
        if number < minimum:
            raise ValueError(f"{name} must be at least {minimum}")
        return number
