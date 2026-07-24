"""Hourly dialysis demand, clinic capacity, treatment, and return movement."""

from __future__ import annotations

import csv
from pathlib import Path
import time

from core.plugin import ActionPlugin
from core.population import PopulationTemplate
from core.routine import Action
from core.simulator import LodusSimulation


class DialysisPlugin(ActionPlugin):
    """Models recurring dialysis demand with traceable population state.

    Experiment configuration example::

        "dialysis_plugin": {
            "patient_count": 120,
            "treatment_frequency_days": 3,
            "clinic_data_file": "dialysis_clinics/opening_hours.csv"
        }

    The clinic CSV must contain ``clinic_name``, ``opening_hour``,
    ``closing_hour``, and ``treatment_capacity_per_hour``. Clinic names are
    matched against the ``clinic_name`` attribute of ``dialysis_clinic`` nodes.
    """

    ACTION_TYPE = "dialysis"
    PATIENT = "dialysis_patient"
    FREQUENCY = "dialysis_frequency_days"
    NEXT_DUE = "dialysis_next_due_day"
    STATUS = "dialysis_status"
    ORIGIN = "dialysis_origin_node"
    TREATMENT_FRAME = "dialysis_treatment_frame"

    def __init__(self):
        super().__init__()
        self.simulation: LodusSimulation | None = None
        self.env_graph = None
        self.clinic_schedules = {}

    def load_plugin(self, simulation: LodusSimulation):
        self.simulation = simulation
        self.env_graph = simulation.env_graph
        simulation.add_action_type_to_function(
            self.ACTION_TYPE, self.dialysis, True
        )

        self.config = simulation.experiment_config.get("dialysis_plugin", {})
        self.patient_count = self._positive_int(
            self.config.get(
                "patient_count",
                self.config.get("dialysis_patient_count", 0),
            ),
            "patient_count",
            allow_zero=True,
        )
        self.frequency_days = self._positive_int(
            self.config.get(
                "treatment_frequency_days",
                self.config.get("treatment_frequency", 1),
            ),
            "treatment_frequency_days",
        )

        data_file = self.config.get(
            "clinic_data_file", self.config.get("data_file")
        )
        if not data_file:
            raise ValueError(
                "dialysis_plugin requires a 'clinic_data_file'"
            )

        self._add_traceable_defaults()
        self.clinic_schedules = self._load_clinic_schedules(data_file)
        self._select_patients()

    def update_time_step(self, cycle_step: int, simulation_step: int):
        if self.simulation is None:
            return
        self.simulation.direct_action_invoke(
            Action(self.ACTION_TYPE, PopulationTemplate(), {}),
            cycle_step,
            simulation_step,
        )

    def unload_plugin(self):
        self.simulation = None
        self.env_graph = None
        self.clinic_schedules = {}

    def dialysis(
        self,
        pop_template: PopulationTemplate,
        values: dict,
        cycle_step: int,
        simulation_step: int,
    ):
        """Treat last frame's arrivals, return them, then admit this hour's demand."""
        started = time.perf_counter()
        self._complete_treatments(simulation_step)
        self._dispatch_due_patients(cycle_step, simulation_step)
        self.add_execution_time(self.ACTION_TYPE, time.perf_counter() - started)

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

    def _select_patients(self):
        available = self.env_graph.get_population_size()
        if self.patient_count > available:
            raise ValueError(
                f"dialysis patient_count ({self.patient_count}) exceeds "
                f"the simulation population ({available})"
            )

        # Prefer homes, then use other non-clinic nodes if necessary.
        nodes = sorted(
            self.env_graph.node_list,
            key=lambda node: (
                node.node_type == "dialysis_clinic",
                node.node_type != "home",
                node.get_complete_name(),
            ),
        )
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
                available_nonpatients = PopulationTemplate(
                    traceable_characteristics={self.PATIENT: False}
                )
                quantity = min(
                    remaining, node.get_population_size(available_nonpatients)
                )
                blobs = node.grab_population(quantity, available_nonpatients)
                for blob in blobs:
                    blob.set_traceable_characteristic(self.PATIENT, True)
                    blob.set_traceable_characteristic(
                        self.FREQUENCY, self.frequency_days
                    )
                    blob.set_traceable_characteristic(self.NEXT_DUE, phase)
                    blob.set_traceable_characteristic(self.STATUS, "waiting")
                    node.add_blob(blob)
                remaining -= quantity

    def _load_clinic_schedules(self, configured_path):
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
            rows = list(csv.DictReader(handle, dialect=dialect))

        required = {
            "clinic_name",
            "opening_hour",
            "closing_hour",
            "treatment_capacity_per_hour",
        }
        if not rows:
            raise ValueError(f"Dialysis clinic data file is empty: {path}")
        missing = required.difference(rows[0])
        if missing:
            raise ValueError(
                f"Dialysis clinic data is missing columns: {sorted(missing)}"
            )

        clinics_by_name = {}
        for node in self.env_graph.node_list:
            if node.node_type != "dialysis_clinic":
                continue
            name = node.attributes.get("clinic_name")
            if name:
                clinics_by_name[name] = node
            clinics_by_name[node.get_complete_name()] = node

        schedules = {}
        for row in rows:
            name = row["clinic_name"].strip()
            if name not in clinics_by_name:
                raise ValueError(
                    f"Clinic '{name}' from {path} was not found in the environment"
                )
            node = clinics_by_name[name]
            opening = self._hour(row["opening_hour"], "opening_hour")
            closing = self._hour(row["closing_hour"], "closing_hour")
            capacity = self._positive_int(
                row["treatment_capacity_per_hour"],
                "treatment_capacity_per_hour",
                allow_zero=True,
            )
            schedules.setdefault(node.id, []).append(
                (opening, closing, capacity)
            )
        return schedules

    def _complete_treatments(self, simulation_step: int):
        template = PopulationTemplate(
            traceable_characteristics={
                self.PATIENT: True,
                self.STATUS: "in_treatment",
                self.TREATMENT_FRAME: simulation_step,
            }
        )
        current_day = simulation_step // self.simulation.time_status.cycle_length
        for clinic_id in self.clinic_schedules:
            clinic = self.env_graph.get_node_by_id(clinic_id)
            for blob in list(clinic.contained_blobs):
                if blob.get_population_size(template) == 0:
                    continue
                origin_id = blob.get_traceable_characteristic(self.ORIGIN)
                origin = self.env_graph.get_node_by_id(origin_id)
                clinic.remove_blob(blob)
                blob.set_traceable_characteristic(
                    self.NEXT_DUE,
                    current_day
                    + blob.get_traceable_characteristic(self.FREQUENCY),
                )
                blob.set_traceable_characteristic(self.STATUS, "waiting")
                blob.set_traceable_characteristic(self.ORIGIN, -1)
                blob.set_traceable_characteristic(self.TREATMENT_FRAME, -1)
                self.env_graph.log_blob_movement(clinic, origin, [blob])
                origin.add_blob(blob)

    def _dispatch_due_patients(self, cycle_step: int, simulation_step: int):
        current_day = simulation_step // self.simulation.time_status.cycle_length
        open_slots = []
        for clinic_id, schedules in self.clinic_schedules.items():
            clinic = self.env_graph.get_node_by_id(clinic_id)
            if not clinic.is_enabled():
                continue
            capacity = sum(
                cap
                for opening, closing, cap in schedules
                if self._is_open(cycle_step, opening, closing)
            )
            if capacity > 0:
                open_slots.append([clinic, capacity])

        due = PopulationTemplate(
            traceable_characteristics={
                self.PATIENT: True,
                self.STATUS: "waiting",
                self.NEXT_DUE: lambda day: day <= current_day,
            }
        )
        origins = sorted(
            self.env_graph.node_list, key=lambda node: node.get_complete_name()
        )
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
                self.env_graph.log_blob_movement(origin, clinic, blobs)
                clinic.add_blobs(blobs)
                clinic_slot[1] -= quantity
                if clinic_slot[1] == 0:
                    open_slots.remove(clinic_slot)

    @staticmethod
    def _distance(node_a, node_b):
        return sum(
            (a - b) ** 2 for a, b in zip(node_a.long_lat, node_b.long_lat)
        )

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
