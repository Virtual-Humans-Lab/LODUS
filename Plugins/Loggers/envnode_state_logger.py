from pathlib import Path

import pandas as pd

from core.plugin import LoggerPlugin
from core.simulator import LodusSimulation


class EnvNodeStateLogger(LoggerPlugin):
    """Logs a full EnvNode enabled/disabled snapshot for every simulation step."""

    def __init__(self):
        self.rows: list[list] = []

    def load_plugin(self, simulation: LodusSimulation):
        self.env_graph = simulation.env_graph
        self.cycle_length = simulation.time_status.cycle_length
        self.sim_step = 0

        self.base_path = "output_logs/" + simulation.experiment_name + "/"
        self.data_frames_path = self.base_path + "/data_frames/"

    def setup_logger(self):
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
        Path(self.data_frames_path).mkdir(parents=True, exist_ok=True)

    def update_time_step(self, cycle_step: int, simulation_step: int):
        self.sim_step = simulation_step

    def log_simulation_step(self):
        cycle_step = self.sim_step % self.cycle_length
        cycle = self.sim_step // self.cycle_length

        for node in self.env_graph.node_list:
            enumeration_area = node.attributes.get("enumeration_area")
            self.rows.append(
                [
                    self.sim_step,
                    cycle_step,
                    cycle,
                    node.containing_region_name,
                    node.get_complete_name(),
                    node.unique_name,
                    node.node_type,
                    node.long_lat[0],
                    node.long_lat[1],
                    enumeration_area,
                    int(node.is_enabled()),
                ]
            )

    def stop_logger(self):
        columns = [
            "Simulation Step",
            "Cycle Step",
            "Cycle",
            "Region",
            "Node",
            "Unique Name",
            "Node Type",
            "Longitude",
            "Latitude",
            "Enumeration Area",
            "Enabled",
        ]
        df = pd.DataFrame(self.rows, columns=columns)
        df.to_csv(
            self.data_frames_path + "envnode_state.csv",
            sep=";",
            encoding="utf-8-sig",
            index=False,
        )

    def unload_plugin(self):
        return super().unload_plugin()
