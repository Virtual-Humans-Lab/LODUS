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

class BlobAtributes(ActionPlugin):

    def __init__(self, env_graph):
        super().__init__()
        self.graph = env_graph
        self.__header = "Level Flood Plugin:"


    def update_blob_attributes(self, dados, flood_lvl):
        for bairro in dados["bairros"]:
            for regiao in bairro["regioes"]:
                for ponto in regiao["random_points"]:
                    point_lvl = ponto["water_lvl"]

                    if flood_lvl >= point_lvl:
                        atribute = EnvNode.add_attribute("active", True)
                    else:
                        atribute = EnvNode.add_attribute("active", False)

        return atribute