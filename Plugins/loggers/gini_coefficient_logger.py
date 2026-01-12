# LODUS core
import environment
from population import PopTemplate
import util
from environment import EnvironmentGraph

from pathlib import Path
from enum import Enum

import csv
from logger_plugin import LoggerPlugin

# CSV file names
CSV_FILES = {
    'global': 'gini_global.csv',
    'region': 'gini_region.csv',
    'node': 'gini_node.csv',
}

class GiniLevel(Enum):
    GLOBAL = 0
    REGION = 1
    NODE = 2


class GiniCoefficientLogger(LoggerPlugin):
    
    def __init__(self, base_filename, graph:environment.EnvironmentGraph, time_cycle=24):
        self.graph = graph
        self.time_cycle = time_cycle

        # Sets paths and create folders
        self.base_path = Path('output_logs') / base_filename
        self.data_frames_path = self.base_path / "data_frames"
        self.figures_path = self.base_path / "figures"
        self.html_plots_path = self.base_path / "html_plots"
        
        # Custom Logging
        self.global_sampled_characteristics: dict[str, list[PopTemplate]] = {}
        self.region_sampled_characteristics: dict[str, list[PopTemplate]] = {}
        self.node_sampled_characteristics: dict[str, list[PopTemplate]] = {}
        
        # File handles
        self.global_file = None
        self.region_file = None
        self.node_file = None
        
        # CSV writers
        self.global_writer = None
        self.region_writer = None
        self.node_writer = None


    def add_sampled_characteristic_logging(self, characteristic_label: str, levels: set[GiniLevel]):
        """Adds a characteristic to be sampled at a given level for Gini calculation."""
        # Validate characteristic exists
        if characteristic_label not in self.graph.original_block_template.buckets:
            raise ValueError(f"Unknown characteristic: {characteristic_label}")
        
        possible_values = self.graph.original_block_template.buckets[characteristic_label]
        print(f"Possible values for {characteristic_label}: {possible_values}")
        
        templates = [PopTemplate(sampled_properties={characteristic_label: value}) 
                     for value in possible_values]
        
        for template_value in possible_values:
            print(f" - Creating template for {characteristic_label} = {template_value}")

        for level in levels:
            if level == GiniLevel.GLOBAL:
                self.global_sampled_characteristics[characteristic_label] = templates
            elif level == GiniLevel.REGION:
                self.region_sampled_characteristics[characteristic_label] = templates
            elif level == GiniLevel.NODE:
                self.node_sampled_characteristics[characteristic_label] = templates
            else:
                raise ValueError("Invalid GiniCoefficientRecordKey level.")


    def load_to_environment(self, env:EnvironmentGraph):
        # Attaches itself to the EnvGraph
        self.graph = env

        # Cycle length and Current SimulationStep
        self.cycle_length:int = self.graph.routine_cycle_length
        self.sim_step: int = 0 



    def start_logger(self):
        """Initialize CSV files and writers for logging."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.data_frames_path.mkdir(parents=True, exist_ok=True)

        # Remove existing files
        for filename in CSV_FILES.values():
            (self.base_path / filename).unlink(missing_ok=True)

        # Global data file
        if self.global_sampled_characteristics:
            header = self._build_header(["Simulation_Step", "Cycle_Step", "Cycle"], self.global_sampled_characteristics)
            self.global_file = open(self.base_path / CSV_FILES['global'], 'w', encoding='utf-8-sig', newline='')
            self.global_writer = csv.writer(self.global_file)
            self.global_writer.writerow(header)

        # Region data file
        if self.region_sampled_characteristics:
            header = self._build_header(["Simulation_Step", "Cycle_Step", "Cycle", "Region"], self.region_sampled_characteristics)
            self.region_file = open(self.base_path / CSV_FILES['region'], 'w', encoding='utf-8-sig', newline='')
            self.region_writer = csv.writer(self.region_file)
            self.region_writer.writerow(header)

        # Node data file
        if self.node_sampled_characteristics:
            header = self._build_header(["Simulation_Step", "Cycle_Step", "Cycle", "Node"], self.node_sampled_characteristics)
            self.node_file = open(self.base_path / CSV_FILES['node'], 'w', encoding='utf-8-sig', newline='')
            self.node_writer = csv.writer(self.node_file)
            self.node_writer.writerow(header)

    def update_time_step(self, cycle_step, simulation_step):
        """Update the current simulation step."""
        self.sim_step = simulation_step

    def log_simulation_step(self):
        """Log all enabled sampling levels for the current simulation step."""
        if self.global_sampled_characteristics:
            self.global_frame(self.graph, self.sim_step)
            if self.global_file:
                self.global_file.flush()
        if self.region_sampled_characteristics:
            self.region_frame(self.graph, self.sim_step)
            if self.region_file:
                self.region_file.flush()
        if self.node_sampled_characteristics:
            self.node_frame(self.graph, self.sim_step)
            if self.node_file:
                self.node_file.flush()

    def _build_header(self, base_columns: list, characteristics_dict: dict) -> list:
        """Build CSV header from base columns and characteristics."""
        return base_columns + list(characteristics_dict.keys())

    def _get_base_row(self, simulation_step: int) -> list:
        """Get the base row with standard time columns."""
        return [simulation_step, simulation_step % self.cycle_length, simulation_step // self.cycle_length]

    def _write_frame(self, writer, base_row: list, characteristics_dict: dict, graph, entity_data=None):
        """Generic frame writer to reduce duplication."""
        if writer is None:
            return
        
        if entity_data is None:
            # Global case
            _row = base_row[:]
            for characteristic, pts in characteristics_dict.items():
                populations = [graph.get_population_size(pt) for pt in pts]
                gini_value = util.gini_coefficient(populations)
                _row.append(gini_value)
            writer.writerow(_row)
        else:
            # Region or Node case
            for entity_name, entity in entity_data.items():
                _row = base_row + [entity_name]
                for characteristic, pts in characteristics_dict.items():
                    populations = [entity.get_population_size(pt) for pt in pts]
                    gini_value = util.gini_coefficient(populations)
                    _row.append(gini_value)
                writer.writerow(_row)

    def global_frame(self, graph: environment.EnvironmentGraph, simulation_step: int):
        """Log global frame for Gini Coefficient calculation."""
        base_row = self._get_base_row(simulation_step)
        self._write_frame(self.global_writer, base_row, self.global_sampled_characteristics, graph)

    def region_frame(self, graph: environment.EnvironmentGraph, simulation_step: int):
        """Log region frame for Gini Coefficient calculation."""
        base_row = self._get_base_row(simulation_step)
        self._write_frame(self.region_writer, base_row, self.region_sampled_characteristics, graph, graph.region_dict)

    def node_frame(self, graph: environment.EnvironmentGraph, simulation_step: int):
        """Log node frame for Gini Coefficient calculation."""
        base_row = self._get_base_row(simulation_step)
        self._write_frame(self.node_writer, base_row, self.node_sampled_characteristics, graph, graph.node_dict)

    def stop_logger(self):
        """Close all open file handles safely."""
        if self.global_file:
            self.global_file.close()
        if self.region_file:
            self.region_file.close()
        if self.node_file:
            self.node_file.close()
