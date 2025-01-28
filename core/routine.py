from core.population import PopulationTemplate

class TimeAction:
    """Describes a command-like Action.

    Actions should be modeled and described in a contract for the simulator.
    Type and expected values should be respected.

    Actions are either base actions or composite actions.

    Each Action is to be associated either:
        - With a graph operator, for base actions; or
        - A base Action's decomposition, for composite actions.
    """
    def __init__(self, action_type: str, pop_template: PopulationTemplate, values: dict):
        if not isinstance(pop_template, PopulationTemplate):
            raise ValueError("pop_template must be of type PopulationTemplate")

        self.action_type: str = action_type
        self.pop_template: PopulationTemplate = pop_template
        self.values: dict = values
        self.values.pop("population_template", None)

    def __str__(self) -> str:
        return (
            f'{{"type" : "{self.action_type}", '
            f'"pop_template" : "{self.pop_template}", '
            f'"values"  : {self.values}}}'
        )

    def __repr__(self) -> str:
        return self.__str__()


class Routine:
    """Describes a mapping of time slot -> TimeAction.

    This mapping should describe the routine an EnvNode follows during the simulation period, cyclically.
    The period of Routine repetition is part of simulation modeling.

    Each time slot matches to one specific TimeAction, describing the requested operation for any given time slot.
    """
    def __init__(self, routine_label: str = ""):
        self.actions: dict[int, list[TimeAction]] = {}
        self.label: str = routine_label

    def add_time_action(self, cycle_step: int, time_action: TimeAction):
        """Add a TimeAction to the Routine."""
        if not isinstance(time_action, TimeAction):
            raise ValueError(f"time_action must be of type TimeAction, is {type(time_action)}")
        if cycle_step < 0:
            raise ValueError(f"cycle_step must be a non-negative integer, is {cycle_step}")
        self.actions.setdefault(cycle_step, []).append(time_action)

    def process_routine(self, cycle_step: int) -> list[TimeAction]:
        """Return the list of Actions for the given cycle_step."""
        return self.actions.get(cycle_step, [])

    def __str__(self) -> str:
        return f'{{"name" : "{self.label}", "actions"  : {self.actions}}}'

    def __repr__(self) -> str:
        return self.__str__()
