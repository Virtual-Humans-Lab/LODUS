"""Inpatient admissions, bed capacity, queues, and patient returns."""

from __future__ import annotations

import csv
import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from core.environment import EnvNode, EnvironmentGraph
from core.plugin import ActionPlugin
from core.population import Blob, PopulationTemplate
from core.routine import Action
from core.simulator import LodusSimulation
from util.math import pyproj_distance_metre
from util.random_instance import FixedRandom


@dataclass(frozen=True)
class BedCapacity:
    hospital: str
    region: str
    longitude: float
    latitude: float
    specialty: str
    bed_type: str
    total_beds: int
    sus_beds: int
    synthetic: bool = False

    @property
    def private_beds(self) -> int:
        return self.total_beds - self.sus_beds


@dataclass(frozen=True)
class AdmissionDemand:
    demand_id: str
    request_step: int
    origin_region: str
    preferred_hospital: str
    specialty: str
    bed_type: str
    cid: str
    payer: str
    quantity: int
    los_min_steps: int
    los_max_steps: int


class InpatientCarePlugin(ActionPlugin):
    """Models inpatient demand with separate SUS and private bed pools."""

    ACTION_TYPE = "inpatient_care"

    PATIENT = "inpatient_patient"
    EVER_ADMITTED = "inpatient_ever_admitted"
    STATUS = "inpatient_status"
    ORIGIN = "inpatient_origin_node"
    DEMAND_ID = "inpatient_demand_id"
    CID = "inpatient_cid"
    SPECIALTY = "inpatient_specialty"
    BED_TYPE = "inpatient_bed_type"
    PAYER = "inpatient_payer"
    PREFERRED_HOSPITAL = "inpatient_preferred_hospital"
    ACTUAL_HOSPITAL = "inpatient_actual_hospital"
    REQUEST_STEP = "inpatient_request_step"
    ADMISSION_STEP = "inpatient_admission_step"
    DISCHARGE_STEP = "inpatient_discharge_step"
    LENGTH_OF_STAY = "inpatient_length_of_stay"

    VALID_POLICIES = {"overflow", "queue"}
    VALID_PAYERS = {"sus", "private"}

    def __init__(self):
        super().__init__()
        self.simulation: LodusSimulation
        self.env_graph: EnvironmentGraph
        self.config: dict[str, Any] = {}
        self.capacity_policy = "overflow"
        self.allow_hospital_change = False
        self.hospital_node_type = "hospital"
        self.patient_origin_node_type = "home"
        self.hospital_name_attribute = "hospital_name"
        self.capacities: dict[tuple[int, str, str], BedCapacity] = {}
        self.hospital_nodes: dict[str, EnvNode] = {}
        self.demands_by_step: dict[int, list[AdmissionDemand]] = {}
        self.new_demand_by_step: dict[int, int] = {}
        self._event_callbacks: dict[str, Callable[[dict], None]] = {}

    def add_event_listener(self, name: str, callback: Callable[[dict], None]):
        self._event_callbacks[name] = callback

    def remove_event_listener(self, name: str):
        self._event_callbacks.pop(name, None)

    def load_plugin(self, simulation: LodusSimulation):
        self.simulation = simulation
        self.env_graph = simulation.env_graph
        self.config = simulation.experiment_config.get(
            "inpatient_care_plugin", {}
        )
        self.capacity_policy = self.config.get("capacity_policy", "overflow")
        if self.capacity_policy not in self.VALID_POLICIES:
            raise ValueError(
                "inpatient_care_plugin.capacity_policy must be "
                "'overflow' or 'queue'"
            )
        self.allow_hospital_change = self._boolean(
            self.config.get("allow_hospital_change", False),
            "allow_hospital_change",
        )
        self.hospital_node_type = self.config.get(
            "hospital_node_type", "hospital"
        )
        self.patient_origin_node_type = self.config.get(
            "patient_origin_node_type", "home"
        )
        self.hospital_name_attribute = self.config.get(
            "hospital_name_attribute", "hospital_name"
        )

        simulation.add_action_type_to_function(
            self.ACTION_TYPE, self.inpatient_care, True
        )
        self._add_traceable_defaults()
        self._index_hospitals()
        self.capacities = self._load_capacities()
        self.demands_by_step = self._load_demands()
        self._validate_demand_population()

    def unload_plugin(self):
        self._event_callbacks.clear()
        self.capacities.clear()
        self.hospital_nodes.clear()
        self.demands_by_step.clear()
        self.new_demand_by_step.clear()

    def update_time_step(self, cycle_step: int, simulation_step: int):
        self.simulation.direct_action_invoke(
            Action(self.ACTION_TYPE, PopulationTemplate(), {}),
            cycle_step,
            simulation_step,
        )

    def inpatient_care(
        self,
        pop_template: PopulationTemplate,
        values: dict,
        cycle_step: int,
        simulation_step: int,
    ):
        self._discharge_due(cycle_step, simulation_step)
        self._materialize_demands(cycle_step, simulation_step)
        self._admit_waiting(cycle_step, simulation_step)

    def _add_traceable_defaults(self):
        defaults = {
            self.PATIENT: False,
            self.EVER_ADMITTED: False,
            self.STATUS: "not_selected",
            self.ORIGIN: -1,
            self.DEMAND_ID: "",
            self.CID: "",
            self.SPECIALTY: "",
            self.BED_TYPE: "",
            self.PAYER: "",
            self.PREFERRED_HOSPITAL: "",
            self.ACTUAL_HOSPITAL: "",
            self.REQUEST_STEP: -1,
            self.ADMISSION_STEP: -1,
            self.DISCHARGE_STEP: -1,
            self.LENGTH_OF_STAY: 0,
        }
        for key, value in defaults.items():
            self.env_graph.add_blobs_traceable_property(key, value)

    def _index_hospitals(self):
        for node in self.env_graph.get_nodes_by_type(self.hospital_node_type):
            name = str(
                node.attributes.get(self.hospital_name_attribute, node.unique_name)
            ).strip()
            if not name:
                raise ValueError(
                    f"Hospital node {node.get_complete_name()} has no name"
                )
            if name in self.hospital_nodes:
                raise ValueError(f"Duplicate hospital node name: {name}")
            self.hospital_nodes[name] = node
        if not self.hospital_nodes:
            raise ValueError(
                f"No nodes of type '{self.hospital_node_type}' were found"
            )

    def _load_capacities(self) -> dict[tuple[int, str, str], BedCapacity]:
        configured = self.config.get("capacity_file")
        if not configured:
            raise ValueError(
                "inpatient_care_plugin.capacity_file is required"
            )
        rows = self._load_records(configured)
        overrides = self.config.get("capacity_overrides", [])
        if isinstance(overrides, (str, Path)):
            overrides = self._load_records(overrides)
        if not isinstance(overrides, list):
            raise ValueError("capacity_overrides must be a list or data file")

        by_name: dict[tuple[str, str, str], BedCapacity] = {}
        for raw in rows:
            capacity = self._parse_capacity(raw)
            key = (capacity.hospital, capacity.specialty, capacity.bed_type)
            if key in by_name:
                raise ValueError(f"Duplicate hospital capacity row: {key}")
            by_name[key] = capacity
        for raw in overrides:
            override = dict(raw)
            override["synthetic"] = override.get("synthetic", True)
            capacity = self._parse_capacity(override)
            by_name[
                (capacity.hospital, capacity.specialty, capacity.bed_type)
            ] = capacity

        capacities = {}
        for (hospital, specialty, bed_type), capacity in by_name.items():
            if hospital not in self.hospital_nodes:
                raise ValueError(
                    f"Hospital '{hospital}' from capacity data was not found "
                    "in the environment"
                )
            node = self.hospital_nodes[hospital]
            if node.containing_region_name != capacity.region:
                raise ValueError(
                    f"Hospital '{hospital}' is in region "
                    f"'{node.containing_region_name}', not '{capacity.region}'"
                )
            capacities[(node.id, specialty, bed_type)] = capacity
        return capacities

    def _parse_capacity(self, raw: dict[str, Any]) -> BedCapacity:
        required = {
            "hospital",
            "region",
            "longitude",
            "latitude",
            "specialty",
            "bed_type",
            "total_beds",
            "sus_beds",
        }
        missing = required.difference(raw)
        if missing:
            raise ValueError(
                f"Hospital capacity row is missing fields: {sorted(missing)}"
            )
        total = self._nonnegative_int(raw["total_beds"], "total_beds")
        sus = self._nonnegative_int(raw["sus_beds"], "sus_beds")
        if sus > total:
            raise ValueError(
                f"sus_beds ({sus}) exceeds total_beds ({total}) for "
                f"{raw['hospital']} / {raw['specialty']} / {raw['bed_type']}"
            )
        return BedCapacity(
            hospital=str(raw["hospital"]).strip(),
            region=str(raw["region"]).strip(),
            longitude=float(raw["longitude"]),
            latitude=float(raw["latitude"]),
            specialty=str(raw["specialty"]).strip(),
            bed_type=str(raw["bed_type"]).strip(),
            total_beds=total,
            sus_beds=sus,
            synthetic=self._boolean(raw.get("synthetic", False), "synthetic"),
        )

    def _load_demands(self) -> dict[int, list[AdmissionDemand]]:
        sources = self.config.get("demand_sources")
        if not isinstance(sources, list) or not sources:
            raise ValueError(
                "inpatient_care_plugin.demand_sources must be a list"
            )
        demands: list[AdmissionDemand] = []
        for index, source in enumerate(sources):
            if not isinstance(source, dict):
                raise ValueError("Each demand source must be an object")
            adapter = source.get("adapter")
            if adapter == "specialty_totals":
                demands.extend(self._load_specialty_totals(source, index))
            elif adapter == "cid_counts":
                demands.extend(self._load_cid_counts(source, index))
            else:
                raise ValueError(
                    f"Unknown inpatient care demand adapter: {adapter!r}"
                )

        schedule: dict[int, list[AdmissionDemand]] = {}
        total_steps = (
            self.simulation.time_status.total_cycles
            * self.simulation.time_status.cycle_length
        )
        for demand in demands:
            if demand.request_step < 0 or demand.request_step >= total_steps:
                raise ValueError(
                    f"Demand {demand.demand_id} has request_step "
                    f"{demand.request_step}, outside 0..{total_steps - 1}"
                )
            self._validate_demand_route(demand)
            schedule.setdefault(demand.request_step, []).append(demand)
        for step_demands in schedule.values():
            step_demands.sort(key=lambda item: item.demand_id)
        return schedule

    def _load_specialty_totals(
        self, source: dict[str, Any], source_index: int
    ) -> list[AdmissionDemand]:
        records = self._source_records(source)
        total_steps = (
            self.simulation.time_status.total_cycles
            * self.simulation.time_status.cycle_length
        )
        demands: list[AdmissionDemand] = []
        for record_index, raw in enumerate(records):
            required = {
                "origin_region",
                "specialty",
                "bed_type",
                "total_admissions",
                "sus_admissions",
                "los_min_steps",
                "los_max_steps",
            }
            missing = required.difference(raw)
            if missing:
                raise ValueError(
                    "specialty_totals row is missing fields: "
                    f"{sorted(missing)}"
                )
            total = self._nonnegative_int(
                raw["total_admissions"], "total_admissions"
            )
            sus = self._nonnegative_int(
                raw["sus_admissions"], "sus_admissions"
            )
            if sus > total:
                raise ValueError(
                    f"sus_admissions ({sus}) exceeds total_admissions ({total})"
                )
            los_min, los_max = self._length_of_stay(raw)
            start = self._nonnegative_int(
                raw.get("start_step", 0), "start_step"
            )
            end = self._nonnegative_int(
                raw.get("end_step", total_steps - 1), "end_step"
            )
            if end < start:
                raise ValueError("end_step must be greater than start_step")
            if end >= total_steps:
                raise ValueError(
                    f"end_step {end} exceeds final simulation step "
                    f"{total_steps - 1}"
                )
            base = {
                "origin_region": str(raw["origin_region"]).strip(),
                "preferred_hospital": str(
                    raw.get("preferred_hospital", "")
                ).strip(),
                "specialty": str(raw["specialty"]).strip(),
                "bed_type": str(raw["bed_type"]).strip(),
                "cid": str(raw.get("cid", "")).strip(),
                "los_min_steps": los_min,
                "los_max_steps": los_max,
            }
            for payer, quantity in (
                ("sus", sus),
                ("private", total - sus),
            ):
                distribution = self._uniform_distribution(
                    quantity, start, end
                )
                for step, step_quantity in enumerate(
                    distribution, start=start
                ):
                    if step_quantity == 0:
                        continue
                    demands.append(
                        AdmissionDemand(
                            demand_id=(
                                f"specialty-{source_index}-{record_index}-"
                                f"{payer}-{step}"
                            ),
                            request_step=step,
                            payer=payer,
                            quantity=step_quantity,
                            **base,
                        )
                    )
        return demands

    def _load_cid_counts(
        self, source: dict[str, Any], source_index: int
    ) -> list[AdmissionDemand]:
        records = self._source_records(source)
        mappings = self._load_cid_mappings(source)
        aliases = {
            str(key).strip(): str(value).strip()
            for key, value in source.get("region_aliases", {}).items()
        }
        legacy_columns = any("REGIAO_HOSPITAL" in row for row in records)
        one_based = self._boolean(
            source.get("one_based_steps", legacy_columns),
            "one_based_steps",
        )
        has_default_share = "sus_share" in source
        sus_share = (
            self._ratio(source["sus_share"], "sus_share")
            if has_default_share
            else None
        )
        default_los = {
            "los_min_steps": source.get("los_min_steps", 1),
            "los_max_steps": source.get("los_max_steps", 4),
        }
        demands: list[AdmissionDemand] = []
        for record_index, raw in enumerate(records):
            region = self._first(raw, "origin_region", "REGIAO_HOSPITAL")
            step_value = self._first(
                raw, "request_step", "time_index", "MES_INTER"
            )
            cid = self._first(raw, "cid", "DIAG_PRINC")
            quantity = self._nonnegative_int(
                self._first(raw, "quantity", "QUANTIDADE"), "quantity"
            )
            region = aliases.get(str(region).strip(), str(region).strip())
            step = int(step_value) - int(one_based)
            mapping = self._match_cid(str(cid).strip(), mappings)
            raw_sus = self._optional_first(
                raw, "sus_quantity", "QUANTIDADE_SUS"
            )
            if raw_sus is None:
                if sus_share is None:
                    raise ValueError(
                        "cid_counts requires sus_quantity in every row or "
                        "an explicit sus_share"
                    )
                sus = int(round(quantity * sus_share))
            else:
                sus = self._nonnegative_int(raw_sus, "sus_quantity")
            if sus > quantity:
                raise ValueError(
                    f"sus_quantity ({sus}) exceeds quantity ({quantity})"
                )
            los_min, los_max = self._length_of_stay(
                {
                    "los_min_steps": raw.get(
                        "los_min_steps", default_los["los_min_steps"]
                    ),
                    "los_max_steps": raw.get(
                        "los_max_steps", default_los["los_max_steps"]
                    ),
                }
            )
            preferred = str(
                raw.get(
                    "preferred_hospital",
                    source.get("preferred_hospital", ""),
                )
            ).strip()
            for payer, payer_quantity in (
                ("sus", sus),
                ("private", quantity - sus),
            ):
                if payer_quantity == 0:
                    continue
                demands.append(
                    AdmissionDemand(
                        demand_id=(
                            f"cid-{source_index}-{record_index}-{payer}-{step}"
                        ),
                        request_step=step,
                        origin_region=region,
                        preferred_hospital=preferred,
                        specialty=mapping["specialty"],
                        bed_type=mapping["bed_type"],
                        cid=str(cid).strip(),
                        payer=payer,
                        quantity=payer_quantity,
                        los_min_steps=los_min,
                        los_max_steps=los_max,
                    )
                )
        return demands

    def _load_cid_mappings(
        self, source: dict[str, Any]
    ) -> list[dict[str, str]]:
        configured = source.get("cid_mapping_file")
        if not configured:
            raise ValueError("cid_counts.cid_mapping_file is required")
        rows = self._load_records(configured)
        mappings = []
        seen = set()
        for raw in rows:
            required = {"cid_pattern", "specialty", "bed_type"}
            missing = required.difference(raw)
            if missing:
                raise ValueError(
                    f"CID mapping is missing fields: {sorted(missing)}"
                )
            pattern = str(raw["cid_pattern"]).strip().upper()
            if pattern in seen:
                raise ValueError(f"Duplicate CID mapping pattern: {pattern}")
            seen.add(pattern)
            mappings.append(
                {
                    "cid_pattern": pattern,
                    "specialty": str(raw["specialty"]).strip(),
                    "bed_type": str(raw["bed_type"]).strip(),
                }
            )
        return mappings

    @staticmethod
    def _match_cid(cid: str, mappings: list[dict[str, str]]) -> dict[str, str]:
        normalized = cid.upper()
        matches = [
            row
            for row in mappings
            if fnmatch.fnmatchcase(normalized, row["cid_pattern"])
        ]
        if not matches:
            raise ValueError(f"No CID mapping found for '{cid}'")
        if len(matches) > 1:
            raise ValueError(f"Ambiguous CID mappings found for '{cid}'")
        return matches[0]

    def _validate_demand_route(self, demand: AdmissionDemand):
        if demand.payer not in self.VALID_PAYERS:
            raise ValueError(f"Unknown payer: {demand.payer}")
        if demand.quantity <= 0:
            raise ValueError("Demand quantity must be positive")
        if demand.origin_region not in self.env_graph.region_dict:
            raise ValueError(
                f"Demand region '{demand.origin_region}' was not found"
            )
        origin_nodes = self._origin_nodes(demand.origin_region)
        if not origin_nodes:
            raise ValueError(
                f"Region '{demand.origin_region}' has no "
                f"'{self.patient_origin_node_type}' nodes"
            )
        if (
            demand.preferred_hospital
            and demand.preferred_hospital not in self.hospital_nodes
        ):
            raise ValueError(
                f"Preferred hospital '{demand.preferred_hospital}' "
                "was not found"
            )
        candidates = self._compatible_hospitals(demand)
        if not candidates:
            raise ValueError(
                f"No hospital capacity matches {demand.specialty} / "
                f"{demand.bed_type} / {demand.payer}"
            )
        if demand.preferred_hospital:
            preferred = self.hospital_nodes[demand.preferred_hospital]
            if preferred not in candidates:
                raise ValueError(
                    f"Preferred hospital '{demand.preferred_hospital}' has "
                    f"no {demand.payer} capacity for {demand.specialty} / "
                    f"{demand.bed_type}"
                )

    def _validate_demand_population(self):
        totals: dict[str, int] = {}
        for demands in self.demands_by_step.values():
            for demand in demands:
                totals[demand.origin_region] = (
                    totals.get(demand.origin_region, 0) + demand.quantity
                )
        available = PopulationTemplate(
            traceable_characteristics={
                self.EVER_ADMITTED: False,
                self.STATUS: "not_selected",
            }
        )
        for region, required in totals.items():
            population = sum(
                node.get_population_size(available)
                for node in self._origin_nodes(region)
            )
            if required > population:
                raise ValueError(
                    f"Inpatient demand in '{region}' requires {required} "
                    f"never-admitted people, but only {population} are "
                    f"available in '{self.patient_origin_node_type}' nodes"
                )

    def _materialize_demands(
        self, cycle_step: int, simulation_step: int
    ):
        demands = self.demands_by_step.get(simulation_step, [])
        self.new_demand_by_step[simulation_step] = sum(
            demand.quantity for demand in demands
        )
        for demand in demands:
            self._emit_demand_event(
                "demanded", demand, demand.quantity, cycle_step, simulation_step
            )
            los_distribution = self._uniform_distribution(
                demand.quantity,
                demand.los_min_steps,
                demand.los_max_steps,
            )
            for offset, quantity in enumerate(
                los_distribution, start=demand.los_min_steps
            ):
                if quantity:
                    self._select_waiting_population(
                        demand,
                        quantity,
                        offset,
                        cycle_step,
                        simulation_step,
                    )

    def _select_waiting_population(
        self,
        demand: AdmissionDemand,
        quantity: int,
        length_of_stay: int,
        cycle_step: int,
        simulation_step: int,
    ):
        template = PopulationTemplate(
            traceable_characteristics={
                self.EVER_ADMITTED: False,
                self.STATUS: "not_selected",
            }
        )
        remaining = quantity
        for origin in self._origin_nodes(demand.origin_region):
            if remaining == 0:
                break
            grabbed = origin.grab_population(remaining, template)
            for blob in grabbed:
                self._set_waiting_state(
                    blob, demand, origin.id, length_of_stay
                )
            origin.add_blobs(grabbed)
            remaining -= sum(blob.get_population_size() for blob in grabbed)
        if remaining:
            raise RuntimeError(
                f"Demand {demand.demand_id} could not select {remaining} "
                "people at runtime"
            )

    def _set_waiting_state(
        self,
        blob: Blob,
        demand: AdmissionDemand,
        origin_id: int,
        length_of_stay: int,
    ):
        values = {
            self.PATIENT: True,
            self.STATUS: "waiting",
            self.ORIGIN: origin_id,
            self.DEMAND_ID: demand.demand_id,
            self.CID: demand.cid,
            self.SPECIALTY: demand.specialty,
            self.BED_TYPE: demand.bed_type,
            self.PAYER: demand.payer,
            self.PREFERRED_HOSPITAL: demand.preferred_hospital,
            self.ACTUAL_HOSPITAL: "",
            self.REQUEST_STEP: demand.request_step,
            self.ADMISSION_STEP: -1,
            self.DISCHARGE_STEP: -1,
            self.LENGTH_OF_STAY: length_of_stay,
        }
        for key, value in values.items():
            blob.set_traceable_characteristic(key, value)

    def _admit_waiting(self, cycle_step: int, simulation_step: int):
        waiting: list[tuple[int, str, int, EnvNode, Blob]] = []
        for origin in self.env_graph.get_nodes_by_type(
            self.patient_origin_node_type
        ):
            for blob in list(origin.contained_blobs):
                if (
                    blob.get_traceable_characteristic(self.PATIENT)
                    and blob.get_traceable_characteristic(self.STATUS)
                    == "waiting"
                ):
                    waiting.append(
                        (
                            blob.get_traceable_characteristic(
                                self.REQUEST_STEP
                            ),
                            blob.get_traceable_characteristic(self.DEMAND_ID),
                            blob.blob_id,
                            origin,
                            blob,
                        )
                    )
        waiting.sort(key=lambda item: item[:3])
        for _, _, _, origin, blob in waiting:
            if blob not in origin.contained_blobs:
                continue
            self._admit_blob(
                origin, blob, cycle_step, simulation_step
            )

    def _admit_blob(
        self,
        origin: EnvNode,
        blob: Blob,
        cycle_step: int,
        simulation_step: int,
    ):
        demand = self._demand_from_blob(blob)
        candidates = self._ranked_hospitals(origin, demand)
        if not candidates:
            self._emit_blob_event(
                "queued", origin, None, blob, cycle_step, simulation_step
            )
            return
        for target in candidates:
            if blob not in origin.contained_blobs:
                break
            quantity = blob.get_population_size()
            if self.capacity_policy == "queue":
                quantity = min(
                    quantity,
                    self.available_capacity(
                        target.id,
                        demand.specialty,
                        demand.bed_type,
                        demand.payer,
                    ),
                )
            if quantity <= 0:
                continue
            admitted = blob.grab_population(quantity)
            if admitted is None:
                continue
            if admitted is blob:
                origin.remove_blob(blob)
            self._set_admitted_state(
                admitted, target, simulation_step
            )
            preferred = admitted.get_traceable_characteristic(
                self.PREFERRED_HOSPITAL
            )
            if preferred and preferred != self._hospital_name(target):
                self._emit_blob_event(
                    "rerouted",
                    origin,
                    target,
                    admitted,
                    cycle_step,
                    simulation_step,
                )
            self.env_graph.log_blob_movement(origin, target, [admitted])
            target.add_blob(admitted)
            self._emit_blob_event(
                "admitted",
                origin,
                target,
                admitted,
                cycle_step,
                simulation_step,
            )
            if admitted is blob:
                break
        if blob in origin.contained_blobs and blob.get_population_size() > 0:
            self._emit_blob_event(
                "queued", origin, None, blob, cycle_step, simulation_step
            )

    def _set_admitted_state(
        self, blob: Blob, target: EnvNode, simulation_step: int
    ):
        blob.set_traceable_characteristic(self.STATUS, "admitted")
        blob.set_traceable_characteristic(self.EVER_ADMITTED, True)
        blob.set_traceable_characteristic(
            self.ACTUAL_HOSPITAL,
            self._hospital_name(target),
        )
        blob.set_traceable_characteristic(
            self.ADMISSION_STEP, simulation_step
        )
        blob.set_traceable_characteristic(
            self.DISCHARGE_STEP,
            simulation_step
            + blob.get_traceable_characteristic(self.LENGTH_OF_STAY),
        )

    def _discharge_due(self, cycle_step: int, simulation_step: int):
        for hospital in self.hospital_nodes.values():
            for blob in list(hospital.contained_blobs):
                if (
                    blob.get_traceable_characteristic(self.PATIENT)
                    and blob.get_traceable_characteristic(self.STATUS)
                    == "admitted"
                    and blob.get_traceable_characteristic(self.DISCHARGE_STEP)
                    == simulation_step
                ):
                    origin = self.env_graph.get_node_by_id(
                        blob.get_traceable_characteristic(self.ORIGIN)
                    )
                    hospital.remove_blob(blob)
                    self._emit_blob_event(
                        "discharged",
                        origin,
                        hospital,
                        blob,
                        cycle_step,
                        simulation_step,
                    )
                    blob.set_traceable_characteristic(
                        self.STATUS, "discharged"
                    )
                    self.env_graph.log_blob_movement(
                        hospital, origin, [blob]
                    )
                    origin.add_blob(blob)

    def _ranked_hospitals(
        self, origin: EnvNode, demand: AdmissionDemand
    ) -> list[EnvNode]:
        candidates = [
            node
            for node in self._compatible_hospitals(demand)
            if node.is_enabled()
        ]
        preferred = (
            self.hospital_nodes.get(demand.preferred_hospital)
            if demand.preferred_hospital
            else None
        )
        if preferred is not None and not self.allow_hospital_change:
            candidates = [preferred] if preferred in candidates else []
        candidates.sort(
            key=lambda node: (
                0 if preferred is not None and node is preferred else 1,
                self._distance(origin, node),
                self._hospital_name(node),
            )
        )
        if self.capacity_policy == "queue":
            candidates = [
                node
                for node in candidates
                if self.available_capacity(
                    node.id,
                    demand.specialty,
                    demand.bed_type,
                    demand.payer,
                )
                > 0
            ]
        return candidates

    def _compatible_hospitals(
        self, demand: AdmissionDemand
    ) -> list[EnvNode]:
        result = []
        for (node_id, specialty, bed_type), capacity in self.capacities.items():
            if specialty != demand.specialty or bed_type != demand.bed_type:
                continue
            payer_capacity = (
                capacity.sus_beds
                if demand.payer == "sus"
                else capacity.private_beds
            )
            if payer_capacity > 0:
                result.append(self.env_graph.get_node_by_id(node_id))
        return result

    def configured_capacity(
        self, node_id: int, specialty: str, bed_type: str, payer: str
    ) -> int:
        capacity = self.capacities[(node_id, specialty, bed_type)]
        return (
            capacity.sus_beds if payer == "sus" else capacity.private_beds
        )

    def occupancy(
        self, node_id: int, specialty: str, bed_type: str, payer: str
    ) -> int:
        node = self.env_graph.get_node_by_id(node_id)
        template = PopulationTemplate(
            traceable_characteristics={
                self.PATIENT: True,
                self.STATUS: "admitted",
                self.SPECIALTY: specialty,
                self.BED_TYPE: bed_type,
                self.PAYER: payer,
            }
        )
        return node.get_population_size(template)

    def available_capacity(
        self, node_id: int, specialty: str, bed_type: str, payer: str
    ) -> int:
        return max(
            0,
            self.configured_capacity(node_id, specialty, bed_type, payer)
            - self.occupancy(node_id, specialty, bed_type, payer),
        )

    def waiting_population(self) -> int:
        template = PopulationTemplate(
            traceable_characteristics={
                self.PATIENT: True,
                self.STATUS: "waiting",
            }
        )
        return self.env_graph.get_population_size(template)

    def admitted_population(self) -> int:
        template = PopulationTemplate(
            traceable_characteristics={
                self.PATIENT: True,
                self.STATUS: "admitted",
            }
        )
        return self.env_graph.get_population_size(template)

    def _origin_nodes(self, region_name: str) -> list[EnvNode]:
        return self.env_graph.get_region_by_name(region_name).get_nodes_by_type(
            self.patient_origin_node_type
        )

    def _demand_from_blob(self, blob: Blob) -> AdmissionDemand:
        return AdmissionDemand(
            demand_id=blob.get_traceable_characteristic(self.DEMAND_ID),
            request_step=blob.get_traceable_characteristic(
                self.REQUEST_STEP
            ),
            origin_region=self.env_graph.get_node_by_id(
                blob.get_traceable_characteristic(self.ORIGIN)
            ).containing_region_name,
            preferred_hospital=blob.get_traceable_characteristic(
                self.PREFERRED_HOSPITAL
            ),
            specialty=blob.get_traceable_characteristic(self.SPECIALTY),
            bed_type=blob.get_traceable_characteristic(self.BED_TYPE),
            cid=blob.get_traceable_characteristic(self.CID),
            payer=blob.get_traceable_characteristic(self.PAYER),
            quantity=blob.get_population_size(),
            los_min_steps=blob.get_traceable_characteristic(
                self.LENGTH_OF_STAY
            ),
            los_max_steps=blob.get_traceable_characteristic(
                self.LENGTH_OF_STAY
            ),
        )

    def _emit_demand_event(
        self,
        event_type: str,
        demand: AdmissionDemand,
        population: int,
        cycle_step: int,
        simulation_step: int,
    ):
        origin = self._origin_nodes(demand.origin_region)[0]
        hospital = self.hospital_nodes.get(demand.preferred_hospital)
        event = self._event_base(
            event_type,
            origin,
            hospital,
            population,
            cycle_step,
            simulation_step,
        )
        event.update(
            {
                "demand_id": demand.demand_id,
                "cid": demand.cid,
                "specialty": demand.specialty,
                "bed_type": demand.bed_type,
                "payer": demand.payer,
                "preferred_hospital": demand.preferred_hospital,
                "request_step": demand.request_step,
                "admission_step": -1,
                "discharge_step": -1,
                "length_of_stay": 0,
            }
        )
        self._notify(event)

    def _emit_blob_event(
        self,
        event_type: str,
        origin: EnvNode,
        hospital: EnvNode | None,
        blob: Blob,
        cycle_step: int,
        simulation_step: int,
    ):
        event = self._event_base(
            event_type,
            origin,
            hospital,
            blob.get_population_size(),
            cycle_step,
            simulation_step,
        )
        event.update(
            {
                "demand_id": blob.get_traceable_characteristic(
                    self.DEMAND_ID
                ),
                "cid": blob.get_traceable_characteristic(self.CID),
                "specialty": blob.get_traceable_characteristic(
                    self.SPECIALTY
                ),
                "bed_type": blob.get_traceable_characteristic(self.BED_TYPE),
                "payer": blob.get_traceable_characteristic(self.PAYER),
                "preferred_hospital": blob.get_traceable_characteristic(
                    self.PREFERRED_HOSPITAL
                ),
                "request_step": blob.get_traceable_characteristic(
                    self.REQUEST_STEP
                ),
                "admission_step": blob.get_traceable_characteristic(
                    self.ADMISSION_STEP
                ),
                "discharge_step": blob.get_traceable_characteristic(
                    self.DISCHARGE_STEP
                ),
                "length_of_stay": blob.get_traceable_characteristic(
                    self.LENGTH_OF_STAY
                ),
            }
        )
        self._notify(event)

    def _event_base(
        self,
        event_type: str,
        origin: EnvNode,
        hospital: EnvNode | None,
        population: int,
        cycle_step: int,
        simulation_step: int,
    ) -> dict[str, Any]:
        return {
            "simulation_step": simulation_step,
            "cycle_step": cycle_step,
            "cycle": (
                simulation_step // self.simulation.time_status.cycle_length
            ),
            "event_type": event_type,
            "population": population,
            "origin_id": origin.id,
            "origin": origin.get_complete_name(),
            "origin_region": origin.containing_region_name,
            "hospital_id": hospital.id if hospital else -1,
            "hospital": self._hospital_name(hospital) if hospital else "",
            "hospital_region": (
                hospital.containing_region_name if hospital else ""
            ),
            "distance_km": (
                self._distance(origin, hospital) / 1000 if hospital else None
            ),
        }

    def _notify(self, event: dict[str, Any]):
        for callback in tuple(self._event_callbacks.values()):
            callback(event.copy())

    def _source_records(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        if "records" in source:
            records = source["records"]
            if not isinstance(records, list):
                raise ValueError("demand source records must be a list")
            return records
        configured = source.get("file")
        if not configured:
            raise ValueError("Demand source requires either file or records")
        return self._load_records(configured)

    @classmethod
    def _load_records(cls, configured: str | Path) -> list[dict[str, Any]]:
        path = cls._data_path(configured)
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                data = data.get("records", data.get("demands", data))
            if not isinstance(data, list):
                raise ValueError(f"JSON data file must contain a list: {path}")
            return [dict(row) for row in data]
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            sample = handle.read(4096)
            handle.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel
            return [dict(row) for row in csv.DictReader(handle, dialect=dialect)]

    @staticmethod
    def _data_path(configured: str | Path) -> Path:
        path = Path(configured)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / "data_input" / path
        if not path.is_file():
            raise FileNotFoundError(
                f"Inpatient care data file not found: {path}"
            )
        return path

    @staticmethod
    def _first(raw: dict[str, Any], *names: str) -> Any:
        value = InpatientCarePlugin._optional_first(raw, *names)
        if value is None or str(value).strip() == "":
            raise ValueError(f"Missing required field; expected one of {names}")
        return value

    @staticmethod
    def _optional_first(raw: dict[str, Any], *names: str) -> Any | None:
        for name in names:
            if name in raw and str(raw[name]).strip() != "":
                return raw[name]
        return None

    @staticmethod
    def _length_of_stay(raw: dict[str, Any]) -> tuple[int, int]:
        minimum = InpatientCarePlugin._positive_int(
            raw["los_min_steps"], "los_min_steps"
        )
        maximum = InpatientCarePlugin._positive_int(
            raw["los_max_steps"], "los_max_steps"
        )
        if maximum < minimum:
            raise ValueError(
                "los_max_steps must be greater than or equal to los_min_steps"
            )
        return minimum, maximum

    @staticmethod
    def _uniform_distribution(
        quantity: int, start: int, end: int
    ) -> list[int]:
        if end < start:
            raise ValueError("Distribution end must be greater than start")
        counts = [0] * (end - start + 1)
        for _ in range(quantity):
            counts[FixedRandom.instance.randrange(len(counts))] += 1
        return counts

    @staticmethod
    def _nonnegative_int(value: Any, name: str) -> int:
        number = int(value)
        if number < 0:
            raise ValueError(f"{name} must be nonnegative")
        return number

    @staticmethod
    def _positive_int(value: Any, name: str) -> int:
        number = int(value)
        if number <= 0:
            raise ValueError(f"{name} must be positive")
        return number

    @staticmethod
    def _ratio(value: Any, name: str) -> float:
        number = float(value)
        if number < 0 or number > 1:
            raise ValueError(f"{name} must be between 0 and 1")
        return number

    @staticmethod
    def _boolean(value: Any, name: str) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in {"true", "false"}:
            return value.lower() == "true"
        if isinstance(value, (int, float)) and value in {0, 1}:
            return bool(value)
        raise ValueError(f"{name} must be a boolean")

    def _hospital_name(self, node: EnvNode) -> str:
        return str(
            node.attributes.get(self.hospital_name_attribute, node.unique_name)
        )

    @staticmethod
    def _distance(node_a: EnvNode, node_b: EnvNode) -> float:
        return pyproj_distance_metre(node_a.long_lat, node_b.long_lat)
