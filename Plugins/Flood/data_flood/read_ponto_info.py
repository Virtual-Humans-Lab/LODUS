import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from datetime import datetime
from pathlib import Path
import time
from core.environment import EnvNode
from core.population import PopulationTemplate
from core.plugin import ActionPlugin
import copy
import math
import json


class ReadPontoInfo(ActionPlugin):
    def __init__(self, env_graph):
        super().__init__()
        self.graph = env_graph
        self.__header = "Level Flood Plugin:"
        self.add_atribute("active", bool)

    def read_pontos_aleatorios(self):
        file_path = Path(__file__).parent / "ponto.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        for bairro in dados["bairros"]:
            nm_bairro = bairro["nome_bairro"]
            for regiao in bairro["regioes"]:
                id_regiao = regiao["id_regiao"]
                pontos = regiao["random_points"]
                pontos.add_atribute("active", bool)
                for ponto in regiao["random_points"]:
                    lvl = ponto["flood_level_response"]

        return dados