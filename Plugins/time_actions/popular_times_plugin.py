# Recebendo parâmetros do json
import csv
from pathlib import Path
from core.plugin import ActionPlugin
from core.simulator import LodusSimulation

import data_pop_times_generator


class PopularTimesPlugin(ActionPlugin):

    def __init__(self):
        super().__init__()
        self.name = "PopularTimesPlugin"
        self.description = "Plugin que carrega dados de horários populares por tipo de local (POI) e fornece quantidade de pessoas por hora para gather_population"
        
        # Mapeia node_type para dados de popular times
        self.popular_times_data_by_node_type: dict[str, list[tuple[int, int]]] = {} # Ex: "restaurant" -> [(0, 10), (1, 5), ..., (23, 20)]
        self.data_path = Path(__file__).parent.parent.parent / "data_input" / "popular_times"

    def load_plugin(self, simulation: LodusSimulation):
        self.simulation = simulation
        print("[PopularTimes] Plugin carregado!")
        
        # Regenera CSVs a cada simulação para valores diferentes
        #pop_times = data_pop_times_generator.generate_popular_times
        #pop_times("restaurant", 1000)
        #pop_times("marketplace", 1000)
        #pop_times("pharmacy", 1000)
        #print("[PopularTimes] CSVs regenerados!")

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
                    hour = int(row[0])
                    quantity = int(row[1])
                    data.append((hour, quantity))
            self.popular_times_data_by_node_type[node_type] = data
            #print(f"Carregado {len(data)} entradas para node_type '{node_type}'")
        except Exception as e:
            print(f"Erro ao carregar CSV para {node_type}: {e}")

    def get_quantity_for_hour(self, node_type: str, hour: int) -> int:
        """Retorna a quantidade de pessoas para um node_type em uma hora específica."""
        if node_type not in self.popular_times_data_by_node_type:
            #print(f"node_type '{node_type}' não carregado")
            return 0
        
        data = self.popular_times_data_by_node_type[node_type]
        for h, quantity in data:
            if h == hour:
                return quantity
        
        return 0

    def popular_times_action(self, pop_template, values: dict, cycle_step: int, sim_step: int):
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
        
        # Obtém quantidade do CSV
        quantity = self.get_quantity_for_hour(node_type, current_hour)
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
        return super().update_time_step(cycle_step, simulation_step)
    
    def unload_plugin(self):
        return super().unload_plugin()

        