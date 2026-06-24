import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from datetime import datetime
from pathlib import Path
import time
import core.environment
from core.environment import FLOODED_ATTRIBUTES
from core.population import PopulationTemplate
from core.plugin import ActionPlugin
import copy
import math
import json
from Plugins.flood.data_flood import read_flood_step

class UpdateTime(ActionPlugin):

    def __init__(self, env_graph):
        super().__init__()
        self.graph = env_graph
        self.__header = "Level Flood Plugin:"
        self.reader = read_flood_step(env_graph)

    def update_time_step(self, cycle_step, simulation_step):
        cycle_length = self.graph.routine_cycle_length
        current_day = simulation_step // cycle_length
        days, flood_lvls = self.reader.read_flood_time_step()
        flood_lvl = self.reader.get_flood_level_for_day(
            current_day,
            days,
            flood_lvls
        )

        print(f"{self.__header} Flood level atual: {flood_lvl}m")
        return flood_lvl