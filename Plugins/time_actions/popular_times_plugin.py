# Recebendo parâmetros do json
import csv
from pathlib import Path
from core.plugin import ActionPlugin
from core.simulator import LodusSimulation
import core.environment


import data_pop_times_generator


class PopularTimesPlugin(ActionPlugin):

    def __init__(self):
        super().__init__()
        self.name = "PopularTimesPlugin"
        self.description = "Plugin que carrega dados de horários populares por tipo de local (POI) e fornece quantidade de pessoas por hora para gather_population"
        
        self.popular_times_data_by_node_type: dict[str, list[tuple[int, int]]] = {} # Ex: "restaurant" -> [(0, 10), (1, 5), ..., (23, 20)]
        self.bairro_multipliers: dict[str, float] = {}
        self.setores_multipliers: dict[str, float] = {}
        self.data_path = Path(__file__).parent.parent.parent / "data_input" / "popular_times"


    def load_plugin(self, simulation: LodusSimulation):
        self.simulation = simulation
        self.env_graph = simulation.env_graph
        #self.simulation.cycle_lenght = simulation.cycle_lenght
        print("[PopularTimes] Plugin carregado!")
        
        # Regenera CSVs a cada simulação para valores diferentes
        pop_times = data_pop_times_generator.generate_popular_times
        pop_times("restaurant", 1000)
        pop_times("marketplace", 1000)
        pop_times("pharmacy", 1000)
        print("[PopularTimes] CSVs regenerados!")

        simulation.add_action_type_to_function('popular_times', self.popular_times_action, False)
        #print("[PopularTimes] Ação 'popular_times' registrada!")

    def _load_csv_for_node_type(self, node_type: str):
        """Carrega CSV para um tipo de nó específico."""
        csv_filename = f"{node_type}.csv"
        csv_path = self.data_path / csv_filename
        
        if not csv_path.exists():
            print(f"Arquivo CSV não encontrado: {csv_path}")
            return
        
        data = []
        try:
            with open(csv_path, 'r', encoding='utf8') as csvfile:
                reader = csv.reader(csvfile)
                next(reader)  # Pula cabeçalho
                for row in reader:
                    # Formato: hora (int), quantidade (int)
                    cicle = int(row[0])
                    hour = int(row[1])
                    quantity = int(row[2])
                    data.append((cicle, hour, quantity))
            self.popular_times_data_by_node_type[node_type] = data
            #print(f"Carregado {len(data)} entradas para node_type '{node_type}'")
        except Exception as e:
            print(f"Erro ao carregar CSV para {node_type}: {e}")

    def _load_bairros_csv(self):
        """Carrega o CSV 'bairros.csv' que contém 'bairro,multiplicador'."""
        csv_path = self.data_path / "bairros.csv"
        if not csv_path.exists():
            print(f"Arquivo de bairros não encontrado: {csv_path}")
            return

        try:
            with open(csv_path, 'r', encoding='utf8') as csvfile:
                reader = csv.reader(csvfile)
                #header = next(reader, None)
                for row in reader:
                    if not row:
                        continue
                    if len(row) < 2:
                        continue
                    nome = row[0].strip().lower()
                    try:
                        mult = float(row[1])
                    except Exception:
                        mult = 1.0
                    self.bairro_multipliers[nome] = mult
            #print(f"Carregados {len(self.bairro_multipliers)} bairros com multiplicadores")
        except Exception as e:
            print(f"Erro ao carregar CSV de bairros: {e}")

    def _load_setores_csv(self):
        csv_path = self.data_path / "Setores-13Bairros.csv"
        if not csv_path.exists():
            print(f"Arquivo de setores não encontrado: {csv_path}")
            return

        try:
            with open(csv_path, 'r', encoding='utf8') as csvfile:
                reader = csv.reader(csvfile)
                #header = next(reader, None)
                for row in reader:
                    if not row:
                        continue
                    if len(row) < 2:
                        continue
                    nome = row[0].strip().lower()
                    try:
                        mult = float(row[1])
                    except Exception:
                        mult = 1.0
                    self.setores_multipliers[nome] = mult
            print(f"Carregados {len(self.setores_multipliers)} setores com multiplicadores")
        except Exception as e:
            print(f"Erro ao carregar CSV de setores: {e}")

    def get_quantity_for_hour(self, sim_step: int, node_type: str, hour: int, region: str, node: str | None = None) -> int:
        """Retorna a quantidade de pessoas para um node_type em uma hora específica.

        A quantidade será multiplicada por um multiplicador que corresponde a população
        total arredondada para um valor divisivel por 1000 (arredondado parea baixo, a menos
        que a população seja inferior a 1000), depois divido por 7, recebendo um multiplicador
        esse valor (arredondada para inteiro).
        """
        if node_type not in self.popular_times_data_by_node_type:
            return 0

        data = self.popular_times_data_by_node_type[node_type]

        cycle_length = self.simulation.cycle_lenght
        current_cycle = (sim_step // cycle_length) % 7
        base_quantity = 0

        for cicle, h, quantity in data:
            if cicle == current_cycle and h == hour:
                base_quantity = quantity
                break

        #NO MOMENTO SETADO APENAS PARA SETORES, COM BAIRROS APLICA O MULTIPLICADOR ERRADO
        if region:
            if node:
                number = node.split("_")[1]
                region_key = region.strip().lower()
                region_key = region_key+"//home_"+number
            else:
                region_key = region.strip().lower()

            if not self.setores_multipliers:
            #if not self.bairro_multipliers:
                #self._load_bairros_csv()
                self._load_setores_csv()

            #mult = self.bairro_multipliers.get(region_key, 1.0)
            mult = self.setores_multipliers.get(region_key, 1.0)

            return int(round(base_quantity * mult))

        return round(base_quantity)


    def popular_times_action(self,  pop_template, values: dict, cycle_step: int, sim_step: int):
        """Ação TimeAction que chama gather_population com quantidade do CSV."""
        node_type = values.get("node_type")
        if not node_type:
            print("Erro: node_type não definido em values")
            return []
        
        #print(f"[PopularTimes] Ação chamada para node_type: {node_type}, cycle_step: {cycle_step}")
        
        if node_type not in self.popular_times_data_by_node_type:
            #print(f"[PopularTimes] Carregando CSV para {node_type}...")
            self._load_csv_for_node_type(node_type)
        
        current_hour = cycle_step
        current_sim_step = sim_step
        
        region = values.get('region')
        unique_name_node = values.get('node')

        quantity = self.get_quantity_for_hour(current_sim_step, node_type, current_hour, region, unique_name_node)
        #print(f"[PopularTimes] Quantidade para {node_type} às {current_hour}h: {quantity}")
        
        # parâmetros para o gather_population
        gather_values = {
            'region': values['region'],
            'node': f"{values['region']}//{values['node']}",
            'quantity': quantity,
            'different_node_name': values.get('different_node_name', False)
        }
        
        # Chama gather_population
        gather_population_func = self.simulation.routine_controller.action_type_to_function.get('gather_population')
        if gather_population_func:
            print(f"[PopularTimes] Chamando gather_population com quantity={quantity}")
            return gather_population_func(pop_template, gather_values, cycle_step, sim_step)
        else:
            print("Erro: gather_population não registrada")
            return []

    def update_time_step(self, cycle_step, simulation_step):
        self.cycle_length = self.simulation.cycle_lenght
        self.cycle_step = cycle_step
        self.sim_step = simulation_step
        self.cycle = (simulation_step // self.cycle_length)
    
    def unload_plugin(self):
        return super().unload_plugin()

        