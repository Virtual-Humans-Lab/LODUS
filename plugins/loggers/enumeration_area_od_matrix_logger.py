# LODUS core
import sys

from core.simulator import LodusSimulation
sys.path.append("/../../")
from core.environment import EnvironmentGraph, EnvNode
from core.plugin import LoggerPlugin
from core.population import Blob, PopulationTemplate

import pandas as pd
import csv

from pathlib import Path


class EnumerationAreaODMatrixLogger(LoggerPlugin):

    def __init__(self):
        # OD Dict: SimulationStep > OriginEA > DestinationEA > Quantities
        self.enum_area_od_matrix: dict[int, dict[str, dict[str, dict[str, int]]]] = {}

        # Custom PopTemplates
        self.custom_templates: dict[str, PopulationTemplate] = {}

        # EA settings
        self.enum_area_attribute_key: str = "enumeration_area"
        self.fallback_attribute_keys: list[str] = ["enumaration_area", "census_sector", "census_area"]
        self.unknown_area_label: str = "UNKNOWN"

        # All observed enumeration areas, used for metadata and late discovery.
        self.enumeration_areas: list[str] = []
        self._step_stream = None
        self._cycle_stream = None
        self._step_writer = None
        self._cycle_writer = None
        self._cycle_aggregate = {}
        self._total_aggregate = {}
        self._active_cycle = None
        self._last_flushed_step = None

    def load_plugin(self, simulation: LodusSimulation):
        # Attaches itself to the EnvGraph
        self.env_graph: EnvironmentGraph = simulation.env_graph
        self.env_graph.movement_logger_dict["enum_area_od_logger"] = self.log_enumeration_area_movement

        # Cycle length and current simulation step
        self.cycle_lenght: int = simulation.time_status.cycle_length
        self.sim_step: int = 0

        # Paths for folders
        self.base_path = "output_logs/" + simulation.experiment_name + "/"
        self.data_frames_path = self.base_path + "/data_frames/"

        # Build known EA list from all nodes in the loaded environment
        areas = {self._get_enum_area(node) for node in self.env_graph.node_list}
        self.enumeration_areas = sorted(list(areas))

    def setup_logger(self):
        # Create the required directories
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
        Path(self.data_frames_path).mkdir(parents=True, exist_ok=True)
        columns = self._columns()
        self._step_stream = open(
            self.data_frames_path + "od_matrix_enumeration_area_step.csv",
            "w", encoding="utf-8-sig", newline=""
        )
        self._cycle_stream = open(
            self.data_frames_path + "od_matrix_enumeration_area_cycle.csv",
            "w", encoding="utf-8-sig", newline=""
        )
        self._step_writer = csv.DictWriter(
            self._step_stream, fieldnames=columns, delimiter=";"
        )
        self._cycle_writer = csv.DictWriter(
            self._cycle_stream,
            fieldnames=[c for c in columns if c not in {"SimulationStep", "CycleStep"}],
            delimiter=";",
        )
        self._step_writer.writeheader()
        self._cycle_writer.writeheader()

    def update_time_step(self, cycle_step, simulation_step) -> None:
        # Update SimulationStep
        self.sim_step = simulation_step

        cycle = simulation_step // self.cycle_lenght
        if self._active_cycle is not None and cycle != self._active_cycle:
            self._flush_cycle()
        self._active_cycle = cycle
        self.enum_area_od_matrix[self.sim_step] = {}

    def log_simulation_step(self):
        self._flush_step()

    def _get_enum_area(self, node: EnvNode) -> str:
        if self.enum_area_attribute_key in node.attributes:
            return str(node.attributes[self.enum_area_attribute_key])

        for key in self.fallback_attribute_keys:
            if key in node.attributes:
                return str(node.attributes[key])

        return self.unknown_area_label

    def _get_step_entry(self, origin_area: str, destination_area: str) -> dict[str, int]:
        if origin_area not in self.enumeration_areas:
            self.enumeration_areas.append(origin_area)

        if destination_area not in self.enumeration_areas:
            self.enumeration_areas.append(destination_area)

        step_data = self.enum_area_od_matrix[self.sim_step]
        origin_data = step_data.setdefault(origin_area, {})
        if destination_area not in origin_data:
            origin_data[destination_area] = {"Total": 0}
            for _key in self.custom_templates:
                origin_data[destination_area][_key] = 0

        return origin_data[destination_area]

    def log_enumeration_area_movement(self, _ori: EnvNode, _dest: EnvNode, _blobs: list[Blob]):
        # Total population in all blobs
        total = sum([b.get_population_size() for b in _blobs])

        ori_ea = self._get_enum_area(_ori)
        dest_ea = self._get_enum_area(_dest)

        _x = self._get_step_entry(ori_ea, dest_ea)
        _x["Total"] += total

        for _b in _blobs:
            for _key, _pt in self.custom_templates.items():
                _x[_key] += _b.get_population_size(_pt)

    def stop_logger(self):
        self._flush_step()
        self._flush_cycle()
        if self._step_stream is not None:
            self._step_stream.close()
        if self._cycle_stream is not None:
            self._cycle_stream.close()
        columns = ["Origin", "Destination", "Total"] + list(self.custom_templates)
        rows = []
        for (origin, destination), values in sorted(self._total_aggregate.items()):
            rows.append({"Origin": origin, "Destination": destination, **values})
        pd.DataFrame(rows, columns=columns).to_csv(
            self.data_frames_path + "od_matrix_enumeration_area.csv",
            sep=";", encoding="utf-8-sig", index=False,
        )

    def _columns(self):
        return [
            "SimulationStep", "CycleStep", "Cycle", "Origin", "Destination", "Total",
            *self.custom_templates.keys(),
        ]

    def _flush_step(self):
        if self._step_writer is None or self._last_flushed_step == self.sim_step:
            return
        step_data = self.enum_area_od_matrix.pop(self.sim_step, {})
        cycle = self.sim_step // self.cycle_lenght
        for origin, destinations in step_data.items():
            for destination, values in destinations.items():
                row = {
                    "SimulationStep": self.sim_step,
                    "CycleStep": self.sim_step % self.cycle_lenght,
                    "Cycle": cycle,
                    "Origin": origin,
                    "Destination": destination,
                    **values,
                }
                self._step_writer.writerow(row)
                self._add_aggregate(
                    self._cycle_aggregate, (origin, destination), values
                )
                self._add_aggregate(
                    self._total_aggregate, (origin, destination), values
                )
        self._last_flushed_step = self.sim_step

    def _flush_cycle(self):
        if self._cycle_writer is None or self._active_cycle is None:
            return
        for (origin, destination), values in sorted(self._cycle_aggregate.items()):
            self._cycle_writer.writerow(
                {
                    "Cycle": self._active_cycle,
                    "Origin": origin,
                    "Destination": destination,
                    **values,
                }
            )
        self._cycle_aggregate.clear()

    @staticmethod
    def _add_aggregate(target, key, values):
        entry = target.setdefault(key, {name: 0 for name in values})
        for name, value in values.items():
            entry[name] += value

    def write_od_matrix_to_csv(self,
                               label: str,
                               custom_columns: list[str],
                               od_matrix: dict[int, dict[str, dict[str, dict[str, int]]]]):

        # Columns and data setup
        _columns = ["SimulationStep", "CycleStep", "Cycle", "Origin", "Destination", "Total"] + custom_columns
        _data = []

        # Get data entries in dict: SimulationStep > Origin > Destination > Quantities
        for _sim_step_key, _sim_step_val in od_matrix.items():
            for _or_key, _or_val in _sim_step_val.items():
                for _dest_key, _dest_val in _or_val.items():
                    _row = [_sim_step_key,
                            _sim_step_key % self.cycle_lenght,
                            _sim_step_key // self.cycle_lenght,
                            _or_key,
                            _dest_key]
                    for _key, _val in _dest_val.items():
                        _row.append(_val)
                    _data.append(_row)

        # Data per SimulationStep
        df = pd.DataFrame(data=_data, columns=_columns)
        if df.empty:
            df.to_csv(self.data_frames_path + "od_matrix_" + label + "_step.csv", sep=";", encoding="utf-8-sig", index=False)
            df.to_csv(self.data_frames_path + "od_matrix_" + label + "_cycle.csv", sep=";", encoding="utf-8-sig", index=False)
            df.to_csv(self.data_frames_path + "od_matrix_" + label + ".csv", sep=";", encoding="utf-8-sig", index=False)
            return

        df.to_csv(self.data_frames_path + "od_matrix_" + label + "_step.csv", sep=";", encoding="utf-8-sig")

        # Data per Cycle
        df.drop("SimulationStep", inplace=True, axis=1)
        df.drop("CycleStep", inplace=True, axis=1)
        df_cycle = df.groupby(["Cycle", "Origin", "Destination"]).sum().reset_index()
        df_cycle.to_csv(self.data_frames_path + "od_matrix_" + label + "_cycle.csv", sep=";", encoding="utf-8-sig")

        # Data in entire simulation
        df_cycle.drop("Cycle", inplace=True, axis=1)
        df_sim = df_cycle.groupby(["Origin", "Destination"]).sum().reset_index()
        df_sim.to_csv(self.data_frames_path + "od_matrix_" + label + ".csv", sep=";", encoding="utf-8-sig")

    def unload_plugin(self):
        return super().unload_plugin()
