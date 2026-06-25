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

class ReadFloodStep(ActionPlugin):

    def __init__(self, env_graph):
        super().__init__()

        self.graph = env_graph
        self.__header = "Level Flood Plugin:"

    def read_flood_time_step(self):
        entries = []
        file_path = Path(__file__).parent / "flood_time_step.csv"

        with open(file_path, 'r', encoding='utf-8') as file:

            for line in file:
                parts = line.strip().split(",")

                if len(parts) >= 3:
                    dt = datetime.strptime(parts[0], "%d/%m/%Y %H:%M")
                    flood_lvl_cm = float(parts[2].replace(",", "."))
                    flood_lvl = flood_lvl_cm / 100
                    entries.append((dt, flood_lvl))

        entries.sort(key=lambda item: item[0])

        days = [i for i in range(len(entries))]
        flood_lvls = [lvl for _, lvl in entries]

        return days, flood_lvls
    
    def get_flood_lvl_for_day():
        return
    
    def get_hour_day():
        return