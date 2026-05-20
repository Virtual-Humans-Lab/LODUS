from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

from core.environment import EnvironmentGraph
from core.plugin import ActionPlugin


@dataclass(frozen=True)
class MinOfRule:
    minimum_enabled: int
    nodes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class NodeDependencyRule:
    all_of: tuple[str, ...] = field(default_factory=tuple)
    min_of: tuple[MinOfRule, ...] = field(default_factory=tuple)


class NodeDependencyDataPlugin(ActionPlugin):
    def __init__(self, env_graph: EnvironmentGraph):
        super().__init__()
        self.graph = env_graph
        self.config: dict[str, Any] = self.graph.experiment_config.get("node_dependency_data_plugin", {})

        if "configuration_file" in self.config:
            config_path = Path(self.config["configuration_file"])
            if not config_path.is_absolute():
                config_path = Path(__file__).resolve().parents[2] / "data_input" / config_path
            with open(config_path, "r", encoding="utf-8") as content:
                self.config = json.load(content)

        self.node_dependency_rules: dict[str, NodeDependencyRule] = self._parse_node_dependency_rules(self.config)
        self.node_to_dependents: dict[str, set[str]] = self._build_reverse_dependency_map(self.node_dependency_rules)
        # Register a single dispatcher callable on the graph for dependency queries.
        # Usage: graph.data_action_map['node_dependency'](command, *args, **kwargs)
        self.graph.data_action_map["node_dependency"] = self._node_dependency_action

    def load_plugin(self, simulation):
        return None

    def update_time_step(self, cycle_step, simulation_step):
        return None

    def unload_plugin(self):
        return None

    def _parse_node_dependency_rules(self, config: dict[str, Any]) -> dict[str, NodeDependencyRule]:
        dependency_config = config.get("node_dependencies", config)
        if not isinstance(dependency_config, dict):
            raise ValueError("node_dependencies must be provided as a mapping")

        parsed_rules: dict[str, NodeDependencyRule] = {}

        for node_name, rule_config in dependency_config.items():
            if not isinstance(rule_config, dict):
                raise ValueError(f"dependency rule for node {node_name} must be a mapping")

            all_of = tuple(str(node) for node in rule_config.get("all_of", []))
            min_of_config = rule_config.get("min_of", [])
            if isinstance(min_of_config, dict):
                min_of_config = [min_of_config]
            if not isinstance(min_of_config, list):
                raise ValueError(f"min_of for node {node_name} must be a list of mappings")

            min_of_rules: list[MinOfRule] = []
            for rule in min_of_config:
                if not isinstance(rule, dict):
                    raise ValueError(f"min_of rule for node {node_name} must be a mapping")
                minimum_enabled = rule.get("minimum_enabled", rule.get("count"))
                if minimum_enabled is None:
                    raise ValueError(f"min_of rule for node {node_name} must define minimum_enabled")
                nodes = tuple(str(node) for node in rule.get("nodes", []))
                min_of_rules.append(MinOfRule(minimum_enabled=int(minimum_enabled), nodes=nodes))

            parsed_rules[str(node_name)] = NodeDependencyRule(all_of=all_of, min_of=tuple(min_of_rules))

        return parsed_rules

    def _build_reverse_dependency_map(self, node_dependency_rules: dict[str, NodeDependencyRule]) -> dict[str, set[str]]:
        reverse_map: dict[str, set[str]] = {}

        for node_name in node_dependency_rules:
            reverse_map.setdefault(node_name, set())

        for node_name, rule in node_dependency_rules.items():
            for prerequisite in self.get_direct_dependency_nodes_from_rule(rule):
                reverse_map.setdefault(prerequisite, set()).add(node_name)

        return reverse_map

    def get_dependency_rule(self, node_name: str) -> NodeDependencyRule:
        return self.node_dependency_rules.get(node_name, NodeDependencyRule())

    def get_direct_dependency_nodes_from_rule(self, rule: NodeDependencyRule) -> list[str]:
        dependency_nodes = list(rule.all_of)
        for min_of_rule in rule.min_of:
            dependency_nodes.extend(min_of_rule.nodes)
        return sorted(set(dependency_nodes))

    def get_direct_dependency_nodes(self, node_name: str) -> list[str]:
        return self.get_direct_dependency_nodes_from_rule(self.get_dependency_rule(node_name))

    def get_transitive_dependency_nodes(self, node_name: str) -> list[str]:
        return self._walk_dependency_graph(node_name, self.get_direct_dependency_nodes)

    def get_direct_dependent_nodes(self, node_name: str) -> list[str]:
        return sorted(self.node_to_dependents.get(node_name, set()))

    def get_transitive_dependent_nodes(self, node_name: str) -> list[str]:
        return self._walk_dependency_graph(node_name, self.get_direct_dependent_nodes)

    def _walk_dependency_graph(self, start_node: str, next_nodes_function) -> list[str]:
        visited: set[str] = set()
        pending = list(next_nodes_function(start_node))

        while pending:
            current_node = pending.pop()
            if current_node in visited:
                continue
            visited.add(current_node)
            pending.extend(node for node in next_nodes_function(current_node) if node not in visited)

        return sorted(visited)

    def can_node_be_enabled(self, node_name: str, enabled_nodes: set[str]) -> bool:
        rule = self.get_dependency_rule(node_name)

        for prerequisite in rule.all_of:
            if prerequisite not in enabled_nodes:
                return False

        for min_of_rule in rule.min_of:
            if sum(1 for node in min_of_rule.nodes if node in enabled_nodes) < min_of_rule.minimum_enabled:
                return False

        return True

    def _node_dependency_action(self, command: str, *args, **kwargs):
        """Dispatch node-dependency related commands.

        Supported commands:
          - "get_direct_dependency_nodes"
          - "get_transitive_dependency_nodes"
          - "get_direct_dependent_nodes"
          - "get_transitive_dependent_nodes"
          - "get_nodes_to_disable_when_node_is_disabled" (alias -> transitive_dependent)
          - "get_nodes_to_reenable_when_node_is_enabled" (alias -> transitive_dependent)
          - "can_node_be_enabled"
        """
        mapping = {
            "get_direct_dependency_nodes": self.get_direct_dependency_nodes,
            "get_transitive_dependency_nodes": self.get_transitive_dependency_nodes,
            "get_direct_dependent_nodes": self.get_direct_dependent_nodes,
            "get_transitive_dependent_nodes": self.get_transitive_dependent_nodes,
            "get_nodes_to_disable_when_node_is_disabled": self.get_transitive_dependent_nodes,
            "get_nodes_to_reenable_when_node_is_enabled": self.get_transitive_dependent_nodes,
            "can_node_be_enabled": self.can_node_be_enabled,
            "get_dependency_rule": self.get_dependency_rule,
        }

        if command not in mapping:
            raise KeyError(f"Unknown node_dependency command: {command}")

        return mapping[command](*args, **kwargs)