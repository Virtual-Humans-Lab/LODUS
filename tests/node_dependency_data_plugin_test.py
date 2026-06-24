import json

import pytest

from core.environment import EnvironmentGraph
from Plugins.data.node_dependency_data_plugin import NodeDependencyDataPlugin


@pytest.fixture
def dependency_config_path(tmp_path):
    config_path = tmp_path / "node_dependencies.json"
    config_path.write_text(
        json.dumps(
            {
                "node_dependencies": {
                    "EnvNode_A": {
                        "all_of": ["WaterPlant", "PowerPlant"],
                        "min_of": [
                            {"minimum_enabled": 2, "nodes": ["Pump1", "Pump2", "Pump3"]},
                            {"minimum_enabled": 1, "nodes": ["Backup1", "Backup2"]},
                        ],
                    },
                    "WaterPlant": {"all_of": ["Grid"]},
                    "PowerPlant": {"all_of": ["Grid"]},
                    "Grid": {},
                }
            }
        ),
        encoding="utf-8",
    )
    return config_path


@pytest.fixture
def dependency_graph(dependency_config_path):
    graph = EnvironmentGraph()
    graph.experiment_config = {
        "node_dependency_data_plugin": {"configuration_file": str(dependency_config_path)}
    }
    NodeDependencyDataPlugin(graph)
    return graph


class TestNodeDependencyDataPlugin:
    def test_loads_multiple_min_of_groups(self, dependency_graph):
        assert dependency_graph.data_action_map["node_dependency"](
            "can_node_be_enabled",
            "EnvNode_A",
            {"WaterPlant", "PowerPlant", "Grid", "Pump1", "Pump2", "Backup1"},
        ) is True

        assert dependency_graph.data_action_map["node_dependency"](
            "can_node_be_enabled",
            "EnvNode_A",
            {"WaterPlant", "PowerPlant", "Grid", "Pump1", "Backup1"},
        ) is False

    def test_transitive_prerequisite_lookup(self, dependency_graph):
        assert set(dependency_graph.data_action_map["node_dependency"]("get_direct_dependency_nodes", "EnvNode_A")) == {
            "Backup1",
            "Backup2",
            "PowerPlant",
            "Pump1",
            "Pump2",
            "Pump3",
            "WaterPlant",
        }

        assert set(dependency_graph.data_action_map["node_dependency"]("get_transitive_dependency_nodes", "EnvNode_A")) == {
            "Backup1",
            "Backup2",
            "Grid",
            "PowerPlant",
            "Pump1",
            "Pump2",
            "Pump3",
            "WaterPlant",
        }

    def test_transitive_dependent_lookup(self, dependency_graph):
        assert set(dependency_graph.data_action_map["node_dependency"]("get_direct_dependent_nodes", "Grid")) == {"PowerPlant", "WaterPlant"}

        assert set(dependency_graph.data_action_map["node_dependency"]("get_transitive_dependent_nodes", "Grid")) == {
            "EnvNode_A",
            "PowerPlant",
            "WaterPlant",
        }

    def test_environment_graph_dependency_helpers(self, dependency_graph):
        assert set(dependency_graph.data_action_map["node_dependency"]("get_nodes_to_disable_when_node_is_disabled", "Grid")) == {
            "EnvNode_A",
            "PowerPlant",
            "WaterPlant",
        }
        assert set(dependency_graph.data_action_map["node_dependency"]("get_nodes_to_reenable_when_node_is_enabled", "Grid")) == {
            "EnvNode_A",
            "PowerPlant",
            "WaterPlant",
        }