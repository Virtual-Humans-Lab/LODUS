# atualiza o nivel do guaiba. pode ser um passo na simulacao, ou pode ser automatico.
# ou toda vez que o cycle chega em 0 x vezes o que eu acho que vai ser melhor.

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
from core.environment import EnvNode
from util.math import geopy_distance_metre

class LevelFloodPlugin(ActionPlugin):

    def __init__(self, env_graph: core.environment.EnvironmentGraph):

        super().__init__()
        self.__header:str = "Level Flood Plugin:"
    
        self.graph = env_graph
        try:
            self.pontos = self.read_pontos_aleatorios()
        except FileNotFoundError:
            self.pontos = None

    def update_blob_attributes(self, dados, flood_lvl):
        points = []
        if "bairros" in dados:
            for bairro in dados.get("bairros", []):
                for regiao in bairro.get("regioes", []):
                    for ponto in regiao.get("random_points", []):
                        points.append({
                            "lng": ponto.get("LNG"),
                            "lat": ponto.get("LAT"),
                            "water_lvl": ponto.get("flood_level_response")
                        })
        elif "regions" in dados:
            for region in dados.get("regions", []):
                for poi in region.get("points_of_interest", []):
                    attr = poi.get("attributes", {})
                    points.append({
                        "lng": poi.get("lng_lat", [None, None])[0],
                        "lat": poi.get("lng_lat", [None, None])[1],
                        "water_lvl": attr.get("water_lvl")
                    })

        radius_m = 50
        for node in self.graph.node_list:
            node.add_attribute('active', True)
            #node.add_attribute('is_flooded', False)

        for point in points:
            raw_lvl = point.get("water_lvl")
            if raw_lvl is None:
                continue
            try:
                if isinstance(raw_lvl, str):
                    lvl = float(raw_lvl.replace('m', '').replace(',', '.'))
                else:
                    lvl = float(raw_lvl)
            except Exception:
                continue

            if lvl <= flood_lvl:
                lng = point.get('lng')
                lat = point.get('lat')
                if lng is None or lat is None:
                    continue
                for node in self.graph.node_list:
                    try:
                        dist = geopy_distance_metre([lng, lat], node.long_lat)
                    except Exception:
                        dist = math.inf
                    if dist <= radius_m:
                        node.add_attribute('active', False)

        return dados


    def read_flood_time_step(self):
        entries = []
        repo_root = Path(__file__).resolve().parents[2]
        file_path = repo_root / "data_input" / "data_gwide_experiments" / "flood_time_step.csv"
        if not file_path.exists():
            file_path = Path(__file__).parent / "data_flood" / "flood_time_step.csv"

        if not file_path.exists():
            raise FileNotFoundError(f"Flood time step file not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                parts = line.strip().split(",")

                if len(parts) < 3:
                    continue

                raw_lvl = parts[2].strip()
                if not raw_lvl:
                    continue

                try:
                    dt = datetime.strptime(parts[0], "%d/%m/%Y %H:%M")
                    flood_lvl_cm = float(raw_lvl.replace(",", "."))
                except Exception:
                    continue

                if dt.minute != 0:
                    continue

                if (dt.month < 5) or (dt.month == 5 and dt.day < 5):
                    continue

                flood_lvl = flood_lvl_cm / 100
                entries.append((dt, flood_lvl))

        entries.sort(key=lambda item: item[0])

        days = [i for i in range(len(entries))]
        flood_lvls = [lvl for _, lvl in entries]

        print(flood_lvls[:10])

        return days, flood_lvls


    def read_pontos_aleatorios(self):
        file_path = Path(__file__).parent / "data_flood" / "ponto.json"
        if not file_path.exists():
            file_path = Path(__file__).resolve().parents[1] / "data_input" / "data_gwide_experiments" / "ponto.json"

        with open(file_path, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        return dados


    
    def update_time_step(self, cycle_step:int, simulation_step:int, days: list = None, flood_lvls: list = None):
        # Updates time step data for flood
        self.cycle_length = getattr(self.graph, 'routine_cycle_length', 24)
        self.cycle_step = cycle_step
        self.simulation_step = simulation_step
        self.cycle = (simulation_step // self.cycle_length)
        

        if days is None or flood_lvls is None:
            days, flood_lvls = self.read_flood_time_step()

        current_day = self.simulation_step
        self.current_day = current_day
        self.flood_lvl = self.get_flood_level_for_day(current_day, days, flood_lvls)

        if self.flood_lvl is not None:
            if self.pontos is not None:
                self.update_blob_attributes(self.pontos, self.flood_lvl)
            print(f"{self.__header} Flood level set to {self.flood_lvl}m for day {current_day} (cycle {self.cycle}, step {self.simulation_step}, non active regions: {sum(1 for node in self.graph.node_list if not node.attributes.get('active', True))})")
        else:
            print(f"{self.__header} No flood level available for day {current_day} (cycle {self.cycle}, step {self.simulation_step})")

    def get_flood_level_for_day(self, current_day: int, days: list, flood_lvls: list):
        if not days:
            return None

        best_level = None
        for day, level in zip(days, flood_lvls):
            if day <= current_day:
                best_level = level
            else:
                break
        return best_level
    
    def load_plugin(self, simulation):
        pass

    def unload_plugin(self):
        pass
