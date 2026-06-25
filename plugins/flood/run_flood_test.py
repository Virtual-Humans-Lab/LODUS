import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from util.data_parse import generate_lodus_simulation
from util.random_instance import FixedRandom
from plugins.flood.lvl_flood import LevelFloodPlugin


def run_flood_test(n_cycles: int = 5):
    FixedRandom(random_seed=0, numpy_seed=0)
    sim = generate_lodus_simulation('BaselineGwide')
    flood_plugin = LevelFloodPlugin(sim.env_graph)
    sim.load_plugin(flood_plugin)

    days, flood_lvls = flood_plugin.read_flood_time_step()
    pontos = flood_plugin.read_pontos_aleatorios()

    cycle_length = getattr(sim, 'cycle_lenght', 24)
    total_steps = n_cycles * cycle_length

    for simulation_step in range(total_steps):
        cycle_step = simulation_step % cycle_length
        flood_plugin.update_time_step(cycle_step, simulation_step, days, flood_lvls)
        if flood_plugin.flood_lvl is not None:
            flood_plugin.update_blob_attributes(pontos, flood_plugin.flood_lvl)

    flooded = [n for n in sim.env_graph.node_list if n.attributes.get('active') == False]
    print(f"Total nodes: {len(sim.env_graph.node_list)}")
    print(f"Flooded nodes after {n_cycles} cycles ({total_steps} steps): {len(flooded)}")
    if flooded:
        print('Examples:')
        for n in flooded[:10]:
            print(f" - {n.get_complete_name()} @ {n.long_lat}")
            


if __name__ == '__main__':
    run_flood_test(n_cycles=1)

    
