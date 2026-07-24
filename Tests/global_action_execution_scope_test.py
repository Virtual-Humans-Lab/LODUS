import json
from pathlib import Path

import pytest

from core.environment import EnvNode, EnvRegion, EnvironmentGraph
from core.population import PopulationTemplate
from core.routine import GlobalAction, GlobalActionExecutionScope
from core.simulator import LodusSimulation
from util.data_parse import parse_global_routines


def _simulation_with_two_nodes():
    graph = EnvironmentGraph()
    region = EnvRegion("Region", [0.0, 0.0])
    for unique_name, node_type in (("home", "home"), ("eta", "water_source")):
        node = EnvNode(node_type, unique_name)
        node.containing_region_name = region.name
        region.node_list.append(node)
        region.node_dict[unique_name] = node
        graph.node_list.append(node)
        graph.node_dict[node.get_complete_name()] = node
        graph.node_id_dict[node.id] = node
    graph.region_list.append(region)
    graph.region_dict[region.name] = region
    graph.region_id_dict[region.id] = region
    return LodusSimulation(graph)


def test_global_action_defaults_to_per_node():
    action = GlobalAction(
        "test",
        PopulationTemplate(),
        {},
        [3],
    )
    assert action.execution_scope == GlobalActionExecutionScope.PER_NODE


def test_omitted_scope_expands_once_per_node_with_context():
    simulation = _simulation_with_two_nodes()
    actions = parse_global_routines(
        {
            "global_routine": [
                {
                    "cycle_step": [3],
                    "action": {"type": "test", "values": {"configured": True}},
                }
            ]
        }
    )

    expanded = simulation.routine_controller.process_repeating_global_actions(
        actions, 3
    )

    assert len(expanded) == 2
    assert {action.values["node_unique_name"] for action in expanded} == {
        "home",
        "eta",
    }
    assert all(action.values["region"] == "Region" for action in expanded)
    assert all(action.values["configured"] is True for action in expanded)
    assert all(action.values["frames"] == [3] for action in expanded)


def test_explicit_per_node_scope_is_parsed_and_expanded():
    simulation = _simulation_with_two_nodes()
    actions = parse_global_routines(
        {
            "global_routine": [
                {
                    "cycle_step": [4],
                    "execution_scope": "per_node",
                    "action": {"type": "test"},
                }
            ]
        }
    )

    expanded = simulation.routine_controller.process_repeating_global_actions(
        actions, 4
    )

    assert actions[0].execution_scope == GlobalActionExecutionScope.PER_NODE
    assert len(expanded) == 2
    assert all("node_id" in action.values for action in expanded)


def test_once_scope_creates_one_action_without_node_context():
    simulation = _simulation_with_two_nodes()
    global_action = GlobalAction(
        "test",
        PopulationTemplate(),
        {"configured": True},
        2,
        GlobalActionExecutionScope.ONCE,
    )

    assert (
        simulation.routine_controller.process_repeating_global_actions(
            [global_action], 1
        )
        == []
    )

    expanded = simulation.routine_controller.process_repeating_global_actions(
        [global_action], 2
    )

    assert len(expanded) == 1
    assert expanded[0].values == {
        "configured": True,
        "cycle_length": 2,
    }


def test_invalid_execution_scope_fails_during_parsing():
    with pytest.raises(
        ValueError,
        match="Invalid global routine execution_scope 'somewhere'",
    ):
        parse_global_routines(
            {
                "global_routine": [
                    {
                        "cycle_step": [1],
                        "execution_scope": "somewhere",
                        "action": {"type": "test"},
                    }
                ]
            }
        )


def test_eta_graph_wide_actions_are_configured_to_execute_once():
    routine_path = (
        Path(__file__).parents[1]
        / "data_input"
        / "dialysis_clinics"
        / "OffCycleRoutine-DisableETAs.json"
    )
    routine_data = json.loads(routine_path.read_text(encoding="utf8"))
    actions = parse_global_routines(routine_data)
    simulation = _simulation_with_two_nodes()

    graph_wide_action = next(
        action
        for action in actions
        if action.action_type == "set_nodes_enabled_by_type"
    )
    expanded = simulation.routine_controller.process_repeating_global_actions(
        [graph_wide_action],
        graph_wide_action.cycle_step_definition[0],
    )

    assert graph_wide_action.execution_scope == GlobalActionExecutionScope.ONCE
    assert len(expanded) == 1
    assert "node_id" not in expanded[0].values
