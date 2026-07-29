from __future__ import annotations

from typing import Any, cast

from core.environment import EnvNode, EnvironmentGraph
from core.plugin import ActionPlugin
from core.simulator import LodusSimulation
try:
    from data.node_dependency_data_plugin import (
        MinOfRule,
        NodeDependencyDataPlugin,
        NodeDependencyRule,
    )
except ModuleNotFoundError:
    from plugins.data.node_dependency_data_plugin import (
        MinOfRule,
        NodeDependencyDataPlugin,
        NodeDependencyRule,
    )

class CustomDependencyDataPlugin(ActionPlugin):
    """Load custom dependency data."""

    def __init__(self):
        super().__init__()
        self.__header = "Custom Dependency Data Plugin:"
        self.config: dict[str, Any] = {}

    def load_plugin(self, simulation: LodusSimulation):
        self.graph = simulation.env_graph

        if not simulation.plugin_controller.has_plugin(NodeDependencyDataPlugin):
            raise ValueError(f"{self.__header} NodeDependencyDataPlugin is required for CustomDependencyDataPlugin.")  
            

        self.node_dependency_plugin = cast(
            NodeDependencyDataPlugin,
            simulation.plugin_controller.get_first_plugin_of_type(NodeDependencyDataPlugin),
        )

        self.config = simulation.experiment_config.get("custom_dependency_data_plugin", {})

        self.setup_dependencies()



    def setup_dependencies(self):
        if not self.config:
            raise ValueError(f"{self.__header} No configuration found for custom dependency data plugin.")
        
        dependency_rules_config = self.config.get("dependency_rules")
        if not isinstance(dependency_rules_config, list):
            raise ValueError(f"{self.__header} 'dependency_rules' key is missing in the configuration.")

        generated_rules: dict[str, NodeDependencyRule] = {}

        for rule in dependency_rules_config:
            if not isinstance(rule, dict):
                raise ValueError(f"{self.__header} Each dependency rule must be a mapping.")

            required_keys = ["target_node_type", "target_node_attribute", "dependency_node_type", "dependency_node_attribute", "dependency_rule"]
            missing_keys = [key for key in required_keys if key not in rule]
            if missing_keys:
                raise ValueError(f"{self.__header} Dependency rule is missing required keys: {missing_keys}")

            target_node_type = str(rule["target_node_type"])
            target_node_attribute = str(rule["target_node_attribute"])
            dependency_node_type = str(rule["dependency_node_type"])
            dependency_node_attribute = str(rule["dependency_node_attribute"])
            dependency_rule = str(rule["dependency_rule"])

            print(f"{self.__header} Setting up dependency rule: {rule["rule_name"] if "rule_name" in rule else 'Unnamed Rule'}")
            target_nodes: list[EnvNode] = self.graph.get_nodes_by_type(target_node_type)
            dependency_nodes: list[EnvNode] = self.graph.get_nodes_by_type(dependency_node_type)

            for target_node in target_nodes:
                _target_values = target_node.attributes.get(target_node_attribute)
                if _target_values is None:
                    continue
                if isinstance(_target_values, (str, bytes)):
                    looking_for = [_target_values]
                elif isinstance(_target_values, (list, tuple, set)):
                    looking_for = list(_target_values)
                else:
                    looking_for = [_target_values]

                relevant_dependency_nodes = [
                    dep_node
                    for dep_node in dependency_nodes
                    if dep_node.attributes.get(dependency_node_attribute) in looking_for
                ]

                dependency_names = tuple(node.get_complete_name() for node in relevant_dependency_nodes)
                if not dependency_names:
                    continue

                if dependency_rule == "min_of":
                    min_of = (MinOfRule(minimum_enabled=int(rule.get("minimum_enabled", 1)), nodes=dependency_names),)
                    node_rule = NodeDependencyRule(min_of=min_of)
                elif dependency_rule == "all_of":
                    node_rule = NodeDependencyRule(all_of=dependency_names)
                else:
                    raise ValueError(f"{self.__header} Unsupported dependency_rule '{dependency_rule}'")

                target_complete_name = target_node.get_complete_name()
                existing_rule = generated_rules.get(target_complete_name)
                if existing_rule is None:
                    generated_rules[target_complete_name] = node_rule
                else:
                    generated_rules[target_complete_name] = self._merge_two_rules(existing_rule, node_rule)

        if generated_rules:
            self.node_dependency_plugin.merge_dependency_rules(generated_rules)
        print(f"{self.__header} Merged {len(generated_rules)} custom dependency rules into the NodeDependencyDataPlugin.")

    def _merge_two_rules(self, first: NodeDependencyRule, second: NodeDependencyRule) -> NodeDependencyRule:
        all_of = tuple(sorted(set((*first.all_of, *second.all_of))))
        min_of = (*first.min_of, *second.min_of)
        return NodeDependencyRule(all_of=all_of, min_of=min_of)

    def unload_plugin(self):
        super().unload_plugin()


    def update_time_step(self, cycle_step: int, simulation_step: int):
        super().update_time_step(cycle_step, simulation_step)
