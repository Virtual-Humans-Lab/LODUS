import json
from types import SimpleNamespace

import pytest

from core.environment import EnvironmentGraph, EnvNode
from plugins.data.node_dependency_data_plugin import NodeDependencyDataPlugin


@pytest.fixture
def dependency_config_path(tmp_path):
    config_path = tmp_path / "node_dependencies.json"
    config_path.write_text(
        json.dumps(
            {
                "dependency_rules": {
                    "grid_rule": {"all_of": ["Grid"]},
                    "env_node_a_rule": {
                        "all_of": ["WaterPlant", "PowerPlant"],
                        "min_of": [
                            {"minimum_enabled": 2, "nodes": ["Pump1", "Pump2", "Pump3"]},
                            {"minimum_enabled": 1, "nodes": ["Backup1", "Backup2"]},
                        ],
                    },
                },
                "node_dependencies": {
                    "EnvNode_A": ["env_node_a_rule"],
                    "WaterPlant": ["grid_rule"],
                    "PowerPlant": ["grid_rule"],
                    "Grid": [],
                }
            }
        ),
        encoding="utf-8",
    )
    return config_path


@pytest.fixture
def dependency_graph(dependency_config_path):
    graph = EnvironmentGraph()
    region = "Region1"
    for nm in ["Grid", "WaterPlant", "PowerPlant", "Pump1", "Pump2", "Pump3", "Backup1", "Backup2", "EnvNode_A"]:
        node = EnvNode("type", nm)
        node.containing_region_name = region
        graph.node_list.append(node)
        graph.node_dict[node.get_complete_name()] = node
    graph.experiment_config = {
        "node_dependency_data_plugin": {"dependency_files": [str(dependency_config_path)]}
    }
    plugin = NodeDependencyDataPlugin()
    plugin.load_plugin(SimpleNamespace(env_graph=graph, experiment_config=graph.experiment_config))
    return graph


class TestNodeDependencyDataPlugin:
    def test_loads_multiple_min_of_groups(self, dependency_graph):
        assert dependency_graph.data_action_map["node_dependency"](
            "can_node_be_enabled",
            "Region1//EnvNode_A",
            {"Region1//WaterPlant", "Region1//PowerPlant", "Region1//Grid", "Region1//Pump1", "Region1//Pump2", "Region1//Backup1"},
        ) is True

        assert dependency_graph.data_action_map["node_dependency"](
            "can_node_be_enabled",
            "Region1//EnvNode_A",
            {"Region1//WaterPlant", "Region1//PowerPlant", "Region1//Grid", "Region1//Pump1", "Region1//Backup1"},
        ) is False

    def test_transitive_prerequisite_lookup(self, dependency_graph):
        assert set(dependency_graph.data_action_map["node_dependency"]("get_direct_dependency_nodes", "Region1//EnvNode_A")) == {
            "Region1//Backup1",
            "Region1//Backup2",
            "Region1//PowerPlant",
            "Region1//Pump1",
            "Region1//Pump2",
            "Region1//Pump3",
            "Region1//WaterPlant",
        }

        assert set(dependency_graph.data_action_map["node_dependency"]("get_transitive_dependency_nodes", "Region1//EnvNode_A")) == {
            "Region1//Backup1",
            "Region1//Backup2",
            "Region1//Grid",
            "Region1//PowerPlant",
            "Region1//Pump1",
            "Region1//Pump2",
            "Region1//Pump3",
            "Region1//WaterPlant",
        }

    def test_transitive_dependent_lookup(self, dependency_graph):
        assert set(dependency_graph.data_action_map["node_dependency"]("get_direct_dependent_nodes", "Region1//Grid")) == {"Region1//PowerPlant", "Region1//WaterPlant"}

        assert set(dependency_graph.data_action_map["node_dependency"]("get_transitive_dependent_nodes", "Region1//Grid")) == {
            "Region1//EnvNode_A",
            "Region1//PowerPlant",
            "Region1//WaterPlant",
        }

    def test_environment_graph_dependency_helpers(self, dependency_graph):
        assert set(dependency_graph.data_action_map["node_dependency"]("get_nodes_to_disable_when_node_is_disabled", "Region1//Grid")) == {
            "Region1//EnvNode_A",
            "Region1//PowerPlant",
            "Region1//WaterPlant",
        }
        assert set(dependency_graph.data_action_map["node_dependency"]("get_nodes_to_reenable_when_node_is_enabled", "Region1//Grid")) == {
            "Region1//EnvNode_A",
            "Region1//PowerPlant",
            "Region1//WaterPlant",
        }