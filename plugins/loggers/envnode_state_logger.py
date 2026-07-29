from pathlib import Path

import pandas as pd

from core.plugin import LoggerPlugin
from core.simulator import LodusSimulation


class EnvNodeStateLogger(LoggerPlugin):
    """Logs an initial EnvNode snapshot and then only state changes."""

    def __init__(self):
        self.rows: list[list] = []
        self.transition_rows: list[dict] = []
        self.water_level_rows: list[list] = []
        self.last_enabled_by_node: dict[str, int] = {}
        self.logged_initial_snapshot = False
        self.next_state_event_index = 0

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
            node_key = node.get_complete_name()
            enabled = int(node.is_enabled())
            previous_enabled = self.last_enabled_by_node.get(node_key)

            if self.logged_initial_snapshot or previous_enabled is not None:
                if previous_enabled == enabled:
                    continue

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
                    enabled,
                ]
            )
            self.last_enabled_by_node[node_key] = enabled

        self.logged_initial_snapshot = True
        new_events = self.env_graph.node_state_events[
            self.next_state_event_index:
        ]
        self.transition_rows.extend(new_events)
        self.next_state_event_index = len(
            self.env_graph.node_state_events
        )

        water_level_action = self.env_graph.data_action_map.get(
            "current_water_level"
        )
        if water_level_action is not None:
            self.water_level_rows.append(
                [
                    self.sim_step,
                    cycle_step,
                    cycle,
                    water_level_action(),
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
        transition_columns = [
            "simulation_step",
            "cycle_step",
            "node",
            "region",
            "node_type",
            "cause",
            "action",
            "previous_enabled",
            "enabled",
            "previous_blockers",
            "blockers",
        ]
        pd.DataFrame(
            self.transition_rows, columns=transition_columns
        ).to_csv(
            self.data_frames_path + "node_state_transitions.csv",
            sep=";",
            encoding="utf-8-sig",
            index=False,
        )
        pd.DataFrame(
            self.water_level_rows,
            columns=[
                "Simulation Step",
                "Cycle Step",
                "Cycle",
                "Water Level",
            ],
        ).to_csv(
            self.data_frames_path + "water_level_step.csv",
            sep=";",
            encoding="utf-8-sig",
            index=False,
        )

    def unload_plugin(self):
        return super().unload_plugin()
