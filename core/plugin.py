from abc import ABC, abstractmethod
from typing import Callable

class BasePlugin(ABC):
    """Base class for all plugins. This class is used to extend the functionality of the simulator with additional features."""
    @abstractmethod
    def setup_logger(self, logger):
        pass

    @abstractmethod
    def update_time_step(self, cycle_step: int, simulation_step: int):
        pass

    @abstractmethod
    def log_data(self, logger):
        pass

    @abstractmethod
    def stop_logger(self, logger):
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
        self.action_type_to_function: dict[str, Callable] = {}
        self.execution_times:list[float] = []

    def add_execution_time(self, time: float) -> None:
        """Adds an execution time to the list."""
        if not isinstance(time, (int, float)):
            raise ValueError(f"time must be of type int or float, is {type(time)}")
        self.execution_times.append(time)

    def print_execution_time_data(self) -> str:
        """Prints and returns a summary of execution time data."""
        num_executions = len(self.execution_times)
        total_time = sum(self.execution_times)
        avg_time = total_time / num_executions if num_executions else 0

        out = (
            f"\n{self.__class__.__name__} Execution Time Data:\n"
            f"---Number of executions: {num_executions}\n"
            f"---Total execution time: {total_time}\n"
            f"---Average execution time: {avg_time}\n"
        )
        print(out)
        return out

    def add_action_type_to_function(self, action_type: str, action_function: Callable) -> None:
        """Sets an action type and its corresponding function."""
        if not isinstance(action_type, str):
            raise ValueError(f"action_type must be of type str, is {type(action_type)}")
        if not callable(action_function):
            raise ValueError(f"action_function must be a callable, is {type(action_function)}")
        self.action_type_to_function[action_type] = action_function

    def get_action_type_to_function(self) -> dict:
        """Returns the dictionary of action type-function pairs."""
        return self.action_type_to_function

class RoutinePlugin(BasePlugin):
    def __init__(self):
        self.start_of_step_global_actions = []
        self.start_of_step_actions = []
        self.end_of_step_global_actions = []
        self.end_of_step_actions = []

    @abstractmethod
    def process_start_of_step_actions(self, cycle_step, simulation_step):
        pass

    @abstractmethod
    def process_end_of_step_actions(self, cycle_step, simulation_step):
        pass