#!/usr/bin/env python3
import sys
from pathlib import Path
# allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from util.data_parse import generate_lodus_simulation
from util.random_instance import FixedRandom
from Plugins.Flood.lvl_flood import LevelFloodPlugin

if __name__ == '__main__':
    FixedRandom(random_seed=0, numpy_seed=0)
    # generate simulation using experiments/BaselineGwide.json for data_gwide_experiments
    sim = generate_lodus_simulation('BaselineGwide')

    # instantiate and load plugin
    flood_plugin = LevelFloodPlugin(sim.env_graph)
    sim.load_plugin(flood_plugin)

    # read pontos and apply a test flood level (in metres)
    pontos = flood_plugin.read_pontos_aleatorios()
    test_flood_level_m = 9.0
    flood_plugin.update_blob_attributes(pontos, test_flood_level_m)

    # count flooded nodes
    flooded = [n for n in sim.env_graph.node_list if n.attributes.get('is_flooded')]
    print(f"Total nodes: {len(sim.env_graph.node_list)}")
    print(f"Flooded nodes: {len(flooded)}")
    if flooded:
        print('Examples:')
        for n in flooded[:10]:
            print(f" - {n.get_complete_name()} @ {n.long_lat}")
