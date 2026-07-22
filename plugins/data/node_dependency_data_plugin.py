from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

from core.environment import EnvironmentGraph
from core.plugin import ActionPlugin
from core.simulator import LodusSimulation


@dataclass(frozen=True)
class MinOfRule:
    minimum_enabled: int
    nodes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class NodeDependencyRule:
    all_of: tuple[str, ...] = field(default_factory=tuple)
    min_of: tuple[MinOfRule, ...] = field(default_factory=tuple)


class NodeDependencyDataPlugin(ActionPlugin):
    def __init__(self, graph: EnvironmentGraph | None = None):
        super().__init__()
        self.__header = "Node Dependency Data Plugin:"
        self.graph = graph

    def load_plugin(self, simulation: Any):
        self.graph = simulation.env_graph
        self.config: dict[str, Any] = simulation.experiment_config.get("node_dependency_data_plugin", {})

        self._load_dependency_files()
        parsed = self._parse_node_dependency_rules(self.config)

        self.node_dependency_rules = self._normalize_dependency_rules(parsed)

        self.node_to_dependents: dict[str, set[str]] = self._build_reverse_dependency_map(self.node_dependency_rules)
        
        print(f"{self.__header} Loaded node dependency rules for {len(self.node_dependency_rules)} nodes.")

        # Register a single dispatcher callable on the graph for dependency queries.
        # Usage: graph.data_action_map['node_dependency'](command, *args, **kwargs)
        self.graph.data_action_map["node_dependency"] = self._node_dependency_action

    def merge_dependency_rules(self, new_rules: dict[str, NodeDependencyRule]) -> None:
        """Add dependency rules without discarding existing ones.

        Rules are normalized to complete node names before merging, then any
        rules already stored for a node are combined additively.
        """
        normalized_rules = self._normalize_dependency_rules(new_rules)

        for node_name, rule in normalized_rules.items():
            existing_rule = self.node_dependency_rules.get(node_name, NodeDependencyRule())
            self.node_dependency_rules[node_name] = self._combine_dependency_rules([existing_rule, rule])

        self.node_to_dependents = self._build_reverse_dependency_map(self.node_dependency_rules)

    def _normalize_dependency_rules(self, rules: dict[str, NodeDependencyRule]) -> dict[str, NodeDependencyRule]:
        """Resolve rule targets and prerequisites to complete node names."""
        normalized_rules: dict[str, NodeDependencyRule] = {}

        for node_name, rule in rules.items():
            resolved_node = self._resolve_to_complete_name(node_name)
            all_of = tuple(self._resolve_to_complete_name(n) for n in rule.all_of)
            min_of = []
            for mof in rule.min_of:
                nodes = tuple(self._resolve_to_complete_name(n) for n in mof.nodes)
                min_of.append(MinOfRule(minimum_enabled=mof.minimum_enabled, nodes=nodes))
            normalized_rules[resolved_node] = NodeDependencyRule(all_of=all_of, min_of=tuple(min_of))

        return normalized_rules

    def _load_dependency_files(self):
        # Allow specifying one or more dependency files via the `dependency_files` key.
        # Accepts a single string or a list of strings. Files are resolved relative
        # to the repository `data_input` folder when given as relative paths.
        if "dependency_files" in self.config:
            files = self.config["dependency_files"]
            if isinstance(files, str):
                files = [files]
            if not isinstance(files, list):
                raise ValueError("dependency_files must be a string or list of strings")

            # Start from any other keys present in the plugin config (except the
            # dependency_files key) so inline settings are preserved.
            merged_config: dict[str, Any] = {k: v for k, v in self.config.items() if k != "dependency_files"}

            for file_entry in files:
                config_path = Path(file_entry)
                if not config_path.is_absolute():
                    config_path = Path(__file__).resolve().parents[2] / "data_input" / config_path
                with open(config_path, "r", encoding="utf-8") as fh:
                    file_data = json.load(fh)
                if not isinstance(file_data, dict):
                    raise ValueError(f"dependency file {config_path} must contain a JSON object at top level")

                # Merge top-level keys. For nested mappings, perform a shallow merge
                # so that e.g. multiple files can contribute entries under
                # "node_dependencies".
                for key, value in file_data.items():
                    if key in merged_config and isinstance(merged_config[key], dict) and isinstance(value, dict):
                        merged_config[key].update(value)
                    else:
                        merged_config[key] = value

            self.config = merged_config

    def _parse_node_dependency_rules(self, config: dict[str, Any]) -> dict[str, NodeDependencyRule]:
        dependency_rules_config = config.get("dependency_rules", {})
        if dependency_rules_config and not isinstance(dependency_rules_config, dict):
            raise ValueError("dependency_rules must be provided as a mapping")

        dependency_rules = self._parse_rule_mapping(dependency_rules_config, "dependency_rules")

        node_dependency_config = config.get("node_dependencies", config if not dependency_rules_config else {})
        if not isinstance(node_dependency_config, dict):
            raise ValueError("node_dependencies must be provided as a mapping")

        parsed_rules: dict[str, NodeDependencyRule] = {}
        for node_name, node_config in node_dependency_config.items():
            parsed_rules[str(node_name)] = self._parse_node_dependency_entry(node_name, node_config, dependency_rules)

        return parsed_rules

    def _parse_rule_mapping(self, rule_mapping: dict[str, Any], section_name: str) -> dict[str, NodeDependencyRule]:
        parsed_rules: dict[str, NodeDependencyRule] = {}

        for rule_name, rule_config in rule_mapping.items():
            if not isinstance(rule_config, dict):
                raise ValueError(f"{section_name} entry '{rule_name}' must be a mapping")
            parsed_rules[str(rule_name)] = self._parse_rule_config(rule_config, f"{section_name}['{rule_name}']")

        return parsed_rules

    def _parse_node_dependency_entry(
        self,
        node_name: str,
        node_config: Any,
        dependency_rules: dict[str, NodeDependencyRule],
    ) -> NodeDependencyRule:
        if isinstance(node_config, str):
            rule_names = [node_config]
            inline_rule = NodeDependencyRule()
        elif isinstance(node_config, list):
            rule_names = node_config
            inline_rule = NodeDependencyRule()
        elif isinstance(node_config, dict):
            rule_names = node_config.get("rules", [])
            if isinstance(rule_names, str):
                rule_names = [rule_names]
            if not isinstance(rule_names, list):
                raise ValueError(f"rules for node {node_name} must be a string or list of strings")

            inline_rule_config = {k: v for k, v in node_config.items() if k != "rules"}
            inline_rule = self._parse_rule_config(inline_rule_config, f"node_dependencies['{node_name}']") if inline_rule_config else NodeDependencyRule()
        else:
            raise ValueError(f"dependency entry for node {node_name} must be a string, list, or mapping")

        referenced_rules: list[NodeDependencyRule] = []
        for rule_name in rule_names:
            if not isinstance(rule_name, str):
                raise ValueError(f"rules for node {node_name} must contain only strings")
            if rule_name not in dependency_rules:
                raise ValueError(f"node {node_name} references unknown dependency rule '{rule_name}'")
            referenced_rules.append(dependency_rules[rule_name])

        if inline_rule == NodeDependencyRule() and not referenced_rules:
            return NodeDependencyRule()

        return self._combine_dependency_rules([*referenced_rules, inline_rule])

    def _parse_rule_config(self, rule_config: dict[str, Any], context: str) -> NodeDependencyRule:
        all_of = tuple(str(node) for node in rule_config.get("all_of", []))
        min_of_config = rule_config.get("min_of", [])
        if isinstance(min_of_config, dict):
            min_of_config = [min_of_config]
        if not isinstance(min_of_config, list):
            raise ValueError(f"min_of for {context} must be a list of mappings")

        min_of_rules: list[MinOfRule] = []
        for rule in min_of_config:
            if not isinstance(rule, dict):
                raise ValueError(f"min_of rule for {context} must be a mapping")
            minimum_enabled = rule.get("minimum_enabled", rule.get("count"))
            if minimum_enabled is None:
                raise ValueError(f"min_of rule for {context} must define minimum_enabled")
            nodes = tuple(str(node) for node in rule.get("nodes", []))
            min_of_rules.append(MinOfRule(minimum_enabled=int(minimum_enabled), nodes=nodes))

        return NodeDependencyRule(all_of=all_of, min_of=tuple(min_of_rules))

    def _combine_dependency_rules(self, rules: list[NodeDependencyRule]) -> NodeDependencyRule:
        all_of: list[str] = []
        min_of: list[MinOfRule] = []

        for rule in rules:
            all_of.extend(rule.all_of)
            min_of.extend(rule.min_of)

        return NodeDependencyRule(all_of=tuple(sorted(set(all_of))), min_of=tuple(min_of))

    def _resolve_to_complete_name(self, name: str) -> str:
        """Resolve an identifier from the dependency file to a complete node name.

        If `name` already contains '//' it is treated as a complete name and must
        exist in the graph. Otherwise it is treated as a unique name and resolved
        against `graph.node_list`. If multiple matches exist an error is raised.
        """
        # If already a complete name
        graph = self.graph
        if graph is None:
            raise RuntimeError("NodeDependencyDataPlugin graph is not initialized")

        if "//" in name:
            if name not in graph.node_dict:
                raise ValueError(f"Dependency references unknown node complete name: {name}")
            return name

        # Treat as unique name: attempt to find unique match across graph
        matches = [n.get_complete_name() for n in graph.node_list if n.unique_name == name]
        if not matches:
            raise ValueError(f"Dependency references unknown node unique name: {name}")
        if len(matches) > 1:
            raise ValueError(f"Ambiguous dependency node name '{name}' resolves to multiple complete names: {matches}")
        return matches[0]

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

    def update_time_step(self, cycle_step, simulation_step):
        return None

    def unload_plugin(self):
        return None