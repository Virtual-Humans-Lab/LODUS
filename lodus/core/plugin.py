from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.simulator import LodusSimulation
from .routine import Action, GlobalAction

class BasePlugin(ABC):
    """Base class for all plugins. This class is used to extend the functionality of the simulator with additional features."""
    @abstractmethod
    def load_plugin(self, simulation: 'LodusSimulation'):
        pass

    @abstractmethod
    def update_time_step(self, cycle_step: int, simulation_step: int):
        pass

    @abstractmethod
    def unload_plugin(self):
        pass

class ActionPlugin(BasePlugin):
    """Describes a set of Action types and action function pairs.
    This class is used to extend the functionality of the simulator with additional TimeActions.
    
    Added functions should be 
    (string, dict) -> [TimeAction]

    the dict is a dictionary of values to be read from the input json.

    This parameters passed in the dictionary are defined by the plugin contracts.
    """ 
    def __init__(self):
        # self.action_type_to_function: dict[str, Callable] = {}
        self.execution_times:dict[str, list[float]] = {}

    def add_execution_time(self, action_type: str, time: float) -> None:
        """Adds an execution time to the list."""
        if not isinstance(time, (int, float)):
            raise ValueError(f"time must be of type int or float, is {type(time)}")
        if not isinstance(action_type, str):
            raise ValueError(f"action_type must be of type str, is {type(action_type)}")
        if action_type not in self.execution_times:
            self.execution_times[action_type] = []
        self.execution_times[action_type].append(time)

    def print_execution_time_data(self) -> str:
        """Prints and returns a summary of execution time data."""
        out = f"\n{self.__class__.__name__} Execution Time Data:\n"

        for action_type, times in self.execution_times.items():
            num_executions = len(times)
            total_time = sum(times)
            avg_time = total_time / num_executions if num_executions else 0
            out += (
                f"---Action Type: {action_type}\n"
                f"------Number of executions: {num_executions}\n"
                f"------Total execution time: {total_time}\n"
                f"------Average execution time: {avg_time}\n"
            )
        print(out)
        return out

class RoutinePlugin(BasePlugin):
    def __init__(self):
        self.start_of_step_global_actions:list[GlobalAction] = []
        self.start_of_step_actions:list[Action] = []
        self.end_of_step_global_actions:list[GlobalAction] = []
        self.end_of_step_actions:list[Action] = []

    @abstractmethod
    def process_start_of_step_actions(self, cycle_step, simulation_step) -> list[Action]:
        pass

    @abstractmethod
    def process_end_of_step_actions(self, cycle_step, simulation_step) -> list[Action]:
        pass

class LoggerPlugin(BasePlugin):
    """Describes a logger plugin that can be used to log simulation data."""
    def __init__(self):
        pass

    @abstractmethod
    def setup_logger(self):
        pass

    @abstractmethod
    def log_simulation_step(self):
        pass

    @abstractmethod
    def stop_logger(self):
        pass