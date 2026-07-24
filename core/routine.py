from enum import Enum
from typing import Any
from core.population import PopulationTemplate

class Action:
    """Describes a command-like Action.

    Actions should be modeled and described in a contract for the simulator.
    Type and expected values should be respected.

    Actions are either base actions or composite actions.

    Each Action is to be associated either:
        - With a graph operator, for base actions; or
        - A base Action's decomposition, for composite actions.
    """
    def __init__(self, action_type: str, pop_template: PopulationTemplate, values: dict[str, Any]):
        if not isinstance(pop_template, PopulationTemplate):
            raise ValueError("pop_template must be of type PopulationTemplate")

        self.action_type: str = action_type
        self.pop_template: PopulationTemplate = pop_template
        self.values: dict[str, Any] = values
        self.values.pop("population_template", None)

    def __str__(self) -> str:
        return (
            f'{{"type" : "{self.action_type}", '
            f'"pop_template" : "{self.pop_template}", '
            f'"values"  : {self.values}}}'
        )

    def __repr__(self) -> str:
        return self.__str__()
    
class GlobalActionExecutionScope(str, Enum):
    """Controls how a GlobalAction is expanded when it is scheduled."""

    PER_NODE = "per_node"
    ONCE = "once"


class GlobalAction (Action):
    """Describes a scheduled action executed once globally or once per EnvNode."""
    def __init__(
        self,
        action_type: str,
        population_template: PopulationTemplate,
        values: dict,
        cycle_step_definition: int | list[int],
        execution_scope: GlobalActionExecutionScope | str = GlobalActionExecutionScope.PER_NODE,
    ):
        """Initializes a GlobalAction.
        If cycle_step_definition is an int, the action will be performed every cycle_step_definition cycles.
        If cycle_step_definition is a list of ints, the action will be performed at the specified cycle_steps.
        """
        self.cycle_step_definition: int | list[int] = cycle_step_definition
        self.execution_scope = GlobalActionExecutionScope(execution_scope)
        super().__init__(action_type, population_template, values)

    def should_process_action(self, cycle_step: int) -> bool:
        """Returns True if the action should be processed at the given cycle_step."""
        return (isinstance(self.cycle_step_definition, int) and cycle_step % self.cycle_step_definition == 0) or (isinstance(self.cycle_step_definition, list) and cycle_step in self.cycle_step_definition)


class RoutineTemplate:
    """Describes a template for a Routine.
    
    A bit redundant with the Routine class, but this is a template for it.
    """
    def __init__(self):
        self.cycle_step_to_action_list: dict[int, list[Action]] = {}

    def add_action_to_template(self, cycle_step: int, action: Action) -> None:
        """Adds an Action to the designated cycle step."""
        if not isinstance(action, Action):
            raise ValueError("Action must be of type Action")
        if not isinstance(cycle_step, int) or cycle_step < 0:
            raise ValueError("cycle_step must be a non-negative integer")
        self.cycle_step_to_action_list.setdefault(cycle_step, []).append(action)

class Routine:
    """Describes a mapping of time slot -> list of Actions.

    This mapping should describe the routine an EnvNode follows during the simulation period, cyclically.
    The period of Routine repetition is part of simulation modeling.
    """
    def __init__(self, routine_label: str = ""):
        self.actions: dict[int, list[Action]] = {}
        self.label: str = routine_label

    def add_action_to_routine(self, cycle_step: int, time_action: Action):
        """Add a TimeAction to the Routine."""
        if not isinstance(time_action, Action):
            raise ValueError(f"time_action must be of type TimeAction, is {type(time_action)}")
        if cycle_step < 0:
            raise ValueError(f"cycle_step must be a non-negative integer, is {cycle_step}")
        self.actions.setdefault(cycle_step, []).append(time_action)

    def process_routine(self, cycle_step: int) -> list[Action]:
        """Return the list of Actions for the given cycle_step."""
        if cycle_step < 0:
            raise ValueError(f"cycle_step must be a non-negative integer, is {cycle_step}")
        return self.actions.get(cycle_step, [])

    def __str__(self) -> str:
        return f'{{"name" : "{self.label}", "actions"  : {self.actions}}}'

    def __repr__(self) -> str:
        return self.__str__()

class RoutineFactory:
    """Generates a Routine from a RoutineTemplate."""
    def __init__(self):
        pass

    def generate_routine(self, routine_template: RoutineTemplate) -> Routine:
        """Generates a Routine from the given RoutineTemplate."""
        routine = Routine()
        for cycle_step, action_list in routine_template.cycle_step_to_action_list.items():
            for action in action_list:
                routine.add_action_to_routine(cycle_step, action)
        return routine
