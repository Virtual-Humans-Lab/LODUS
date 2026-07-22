from __future__ import annotations

from pathlib import Path
from typing import Any, cast
import csv
import json

from core.environment import EnvNode, EnvironmentGraph
from core.plugin import ActionPlugin
from core.simulator import LodusSimulation
from data.node_dependency_data_plugin import MinOfRule, NodeDependencyDataPlugin, NodeDependencyRule

class CustomDependencyDataPlugin(ActionPlugin):
    """Load custom dependency data."""

    def __init__(self):
        super().__init__()
        self.__header = "Custom Dependency Data Plugin:"
        self.config: dict[str, Any] = {}

    def load_plugin(self, simulation: LodusSimulation):
        self.graph = simulation.env_graph
        self.cycle_length = simulation.time_status.cycle_length

        if not simulation.plugin_controller.has_plugin(NodeDependencyDataPlugin):
            raise ValueError(f"{self.__header} NodeDependencyDataPlugin is required for CustomDependencyDataPlugin.")  
            

        self.node_dependency_plugin = cast(
            NodeDependencyDataPlugin,
            simulation.plugin_controller.get_first_plugin_of_type(NodeDependencyDataPlugin),
        )

        self.config = simulation.experiment_config.get("custom_dependency_data_plugin", {})


        self.setup_dependencies()
        print(f"{self.__header} Loaded custom dependency data plugin.")



    def setup_dependencies(self):
        if not self.config:
            raise ValueError(f"{self.__header} No configuration found for custom dependency data plugin.")
        
        if "dependency_rules" not in self.config and not isinstance(self.config["dependency_rules"], list):
            raise ValueError(f"{self.__header} 'dependency_rules' key is missing in the configuration.")
        
        for rule in self.config["dependency_rules"]:
            print(f"{self.__header} Setting up dependency rule: {rule}")
            target_nodes: list[EnvNode] = self.graph.get_nodes_by_type(rule.get("target_node_type"))
            dependency_nodes: list[EnvNode] = self.graph.get_nodes_by_type(rule.get("dependency_node_type"))

            for target_node in target_nodes:
                looking_for:list[str] = target_node.attributes[rule.get("target_node_attribute")]
           
                #print(len(dependency_nodes))

                relevant_dependency_nodes = [
                    dep_node for dep_node in dependency_nodes
                    if dep_node.attributes.get(rule.get("dependency_node_attribute")) in looking_for
                ]

                all_of = tuple()
                min_of = []
                if rule["dependency_rule"] == "min_of":
                   nodes = tuple(n.get_complete_name() for n in relevant_dependency_nodes)
                   min_of.append(MinOfRule(minimum_enabled=rule.get("minimum_enabled", 1), nodes = nodes))

                dep_rule = NodeDependencyRule(all_of=all_of, min_of=tuple(min_of))
                print(dep_rule)

                print(target_node.get_complete_name(), len(relevant_dependency_nodes))

                
                
            exit()    
            print(len(target_nodes))

    

            if "dependent_poi" not in rule or "dependency_poi" not in rule or "dependency_type" not in rule:
                raise ValueError(f"{self.__header} Each dependency rule must contain 'dependent_poi', 'dependency_poi', and 'dependency_type' keys.")

    def unload_plugin(self):
        return


    def update_time_step(self, cycle_step: int, simulation_step: int):
        # This plugin does not update anything during the simulation.
        return