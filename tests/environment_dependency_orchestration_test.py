import json
from types import SimpleNamespace

from core.environment import EnvironmentGraph, EnvNode
from plugins.data.node_dependency_data_plugin import NodeDependencyDataPlugin


def make_graph_with_nodes(tmp_path):
    graph = EnvironmentGraph()

    # Create a single region name and nodes with unique names matching dependency rules
    region = "Region1"

    names = ["Grid", "PowerPlant", "WaterPlant", "Pump1", "Pump2", "Pump3", "Backup1", "Backup2", "EnvNode_A"]
    for nm in names:
        node = EnvNode("type", nm)
        node.containing_region_name = region
        graph.node_list.append(node)
        graph.node_dict[node.get_complete_name()] = node

    return graph


def write_dependency_file(tmp_path):
    cfg = {
        "node_dependencies": {
            "Region1//EnvNode_A": {
                "all_of": ["Region1//WaterPlant", "Region1//PowerPlant"],
                "min_of": [
                    {"minimum_enabled": 2, "nodes": ["Region1//Pump1", "Region1//Pump2", "Region1//Pump3"]},
                    {"minimum_enabled": 1, "nodes": ["Region1//Backup1", "Region1//Backup2"]},
                ],
            },
            "Region1//WaterPlant": {"all_of": ["Region1//Grid"]},
            "Region1//PowerPlant": {"all_of": ["Region1//Grid"]},
            "Region1//Grid": {},
        }
    }
    p = tmp_path / "deps.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    return p


def test_disable_cascades(tmp_path):
    graph = make_graph_with_nodes(tmp_path)
    dep_file = write_dependency_file(tmp_path)

    plugin = NodeDependencyDataPlugin()
    dummy_sim = SimpleNamespace(env_graph=graph, experiment_config={"node_dependency_data_plugin": {"dependency_files": [str(dep_file)]}})
    plugin.load_plugin(dummy_sim)

    # Ensure all nodes start enabled
    for n in graph.node_list:
        n.enable()

    summary = graph.set_node_enabled("Region1//Grid", enabled=False)

    # Grid and its dependents (PowerPlant, WaterPlant, EnvNode_A) should be disabled
    disabled = set(s.split("//")[-1] for s in summary["disabled"])
    assert "Grid" in disabled
    assert "PowerPlant" in disabled
    assert "WaterPlant" in disabled
    assert "EnvNode_A" in disabled


def test_enable_blocked_by_prerequisites(tmp_path):
    graph = make_graph_with_nodes(tmp_path)
    dep_file = write_dependency_file(tmp_path)

    plugin = NodeDependencyDataPlugin()
    dummy_sim = SimpleNamespace(env_graph=graph, experiment_config={"node_dependency_data_plugin": {"dependency_files": [str(dep_file)]}})
    plugin.load_plugin(dummy_sim)

    # Disable Grid so PowerPlant/WaterPlant/EnvNode_A prerequisites are missing
    graph.set_node_enabled("Region1//Grid", enabled=False)

    # Try to enable EnvNode_A
    summary = graph.set_node_enabled("Region1//EnvNode_A", enabled=True)

    # Should be blocked and report missing prerequisites (Grid at least)
    assert summary["enabled"] == []
    blocked_keys = list(summary["blocked"].keys())
    assert any("EnvNode_A" in k for k in blocked_keys)
    missing = summary["blocked"][blocked_keys[0]]
    assert any(m.endswith("Grid") or m.endswith("PowerPlant") or m.endswith("WaterPlant") for m in missing)
