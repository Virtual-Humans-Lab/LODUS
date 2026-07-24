from util.random_instance import FixedRandom

import pytest
from core.population import Blob, BlobFactory, CharacteristicsFactory, PopulationTemplate, SampledCharacteristic, SampledCharacteristicCollection
from core.routine import (
    Action,
    GlobalAction,
    GlobalActionExecutionScope,
    Routine,
    RoutineFactory,
    RoutineTemplate,
)

@pytest.fixture(scope="session", autouse=True)
def start_fixedrandom():
    """Initialize FixedRandom to ensure deterministic behavior in tests."""
    FixedRandom()  # Ensure FixedRandom is defined or imported properly.

class TestAction:
    def test_time_action_initialization(self):
        pop_template = PopulationTemplate()
        values = {"key1": "value1", "key2": "value2"}
        action = Action(action_type="TestAction", pop_template=pop_template, values=values)
        
        assert action.action_type == "TestAction"
        assert action.pop_template == pop_template
        assert action.values == values

    def test_time_action_invalid_pop_template(self):
        with pytest.raises(ValueError, match="pop_template must be of type PopulationTemplate"):
            Action(action_type="TestAction", pop_template="InvalidTemplate", values={}) # type: ignore

class TestGlobalAction:
    def test_global_action_initialization(self):
        pop_template = PopulationTemplate()
        values = {"key1": "value1", "key2": "value2"}
        cycle_step_definition = 5
        global_action = GlobalAction(action_type="GlobalTestAction", population_template=pop_template, values=values, cycle_step_definition=cycle_step_definition)
        
        assert global_action.action_type == "GlobalTestAction"
        assert global_action.pop_template == pop_template
        assert global_action.values == values
        assert global_action.cycle_step_definition == cycle_step_definition
        assert global_action.execution_scope == GlobalActionExecutionScope.PER_NODE

    def test_global_action_should_process_action_int(self):
        pop_template = PopulationTemplate()
        values = {"key1": "value1", "key2": "value2"}
        cycle_step_definition = 5
        global_action = GlobalAction(action_type="GlobalTestAction", population_template=pop_template, values=values, cycle_step_definition=cycle_step_definition)
        
        assert global_action.should_process_action(5) == True
        assert global_action.should_process_action(10) == True
        assert global_action.should_process_action(3) == False

    def test_global_action_should_process_action_list(self):
        pop_template = PopulationTemplate()
        values = {"key1": "value1", "key2": "value2"}
        cycle_step_definition = [1, 3, 5]
        global_action = GlobalAction(action_type="GlobalTestAction", population_template=pop_template, values=values, cycle_step_definition=cycle_step_definition)
        
        assert global_action.should_process_action(1) == True
        assert global_action.should_process_action(3) == True
        assert global_action.should_process_action(5) == True
        assert global_action.should_process_action(2) == False

class TestRoutineTemplate:
    def test_routine_template_initialization(self):
        routine_template = RoutineTemplate()
        assert routine_template.cycle_step_to_action_list == {}

    def test_add_action_to_template(self):
        routine_template = RoutineTemplate()
        pop_template = PopulationTemplate()
        action = Action(action_type="TestAction", pop_template=pop_template, values={})
        
        routine_template.add_action_to_template(0, action)
        assert 0 in routine_template.cycle_step_to_action_list
        assert routine_template.cycle_step_to_action_list[0] == [action]

    def test_add_multiple_actions_to_same_cycle_step(self):
        routine_template = RoutineTemplate()
        pop_template = PopulationTemplate()
        action1 = Action(action_type="TestAction1", pop_template=pop_template, values={})
        action2 = Action(action_type="TestAction2", pop_template=pop_template, values={})
        
        routine_template.add_action_to_template(0, action1)
        routine_template.add_action_to_template(0, action2)
        assert routine_template.cycle_step_to_action_list[0] == [action1, action2]

    def test_add_actions_to_different_cycle_steps(self):
        routine_template = RoutineTemplate()
        pop_template = PopulationTemplate()
        action1 = Action(action_type="TestAction1", pop_template=pop_template, values={})
        action2 = Action(action_type="TestAction2", pop_template=pop_template, values={})
        
        routine_template.add_action_to_template(0, action1)
        routine_template.add_action_to_template(1, action2)
        assert routine_template.cycle_step_to_action_list[0] == [action1]
        assert routine_template.cycle_step_to_action_list[1] == [action2]

    def test_add_invalid_action_to_template(self):
        routine_template = RoutineTemplate()
        with pytest.raises(ValueError, match="Action must be of type Action"):
            routine_template.add_action_to_template(0, "InvalidAction")  # type: ignore

    def test_add_action_to_invalid_cycle_step(self):
        routine_template = RoutineTemplate()
        pop_template = PopulationTemplate()
        action = Action(action_type="TestAction", pop_template=pop_template, values={})
        
        with pytest.raises(ValueError, match="cycle_step must be a non-negative integer"):
            routine_template.add_action_to_template(-1, action)
class TestRoutine:
    def test_routine_initialization(self):
        routine = Routine(routine_label="TestRoutine")
        assert routine.label == "TestRoutine"
        assert routine.actions == {}

    def test_add_time_action(self):
        routine = Routine()
        pop_template = PopulationTemplate()
        action = Action(action_type="TestAction", pop_template=pop_template, values={})
        
        routine.add_action_to_routine(0, action)
        assert 0 in routine.actions
        assert routine.actions[0] == [action]

    def test_add_time_action_multiple(self):
        routine = Routine()
        pop_template = PopulationTemplate()
        action1 = Action(action_type="TestAction1", pop_template=pop_template, values={})
        action2 = Action(action_type="TestAction2", pop_template=pop_template, values={})
        action3 = Action(action_type="TestAction3", pop_template=pop_template, values={})
        
        routine.add_action_to_routine(0, action1)
        routine.add_action_to_routine(0, action2)
        routine.add_action_to_routine(1, action3)
        assert 0 in routine.actions
        assert routine.actions[0] == [action1, action2]
        assert routine.actions[1] == [action3]

    def test_add_time_action_invalid_time_action(self):
        routine = Routine()
        with pytest.raises(ValueError, match="time_action must be of type TimeAction"):
            routine.add_action_to_routine(0, "InvalidAction")  # type: ignore

    def test_add_time_action_invalid_cycle_step(self):
        routine = Routine()
        pop_template = PopulationTemplate()
        action = Action(action_type="TestAction", pop_template=pop_template, values={})
        
        with pytest.raises(ValueError, match="cycle_step must be a non-negative integer"):
            routine.add_action_to_routine(-1, action)

    def test_process_routine(self):
        routine = Routine()
        pop_template = PopulationTemplate()
        action1 = Action(action_type="TestAction1", pop_template=pop_template, values={})
        action2 = Action(action_type="TestAction2", pop_template=pop_template, values={})
        action3 = Action(action_type="TestAction3", pop_template=pop_template, values={})
        
        routine.add_action_to_routine(0, action1)
        routine.add_action_to_routine(0, action2)
        routine.add_action_to_routine(1, action3)
        
        actions = routine.process_routine(0)
        assert actions == [action1, action2]
        actions = routine.process_routine(1)
        assert actions == [action3]

    def test_process_routine_no_actions(self):
        routine = Routine()
        actions = routine.process_routine(1)
        assert actions == []

    def test_routine_str(self):
        routine = Routine(routine_label="TestRoutine")
        pop_template = PopulationTemplate()
        action = Action(action_type="TestAction", pop_template=pop_template, values={})
        
        routine.add_action_to_routine(0, action)
        routine_str = str(routine)
        assert routine_str == f'{{"name" : "TestRoutine", "actions"  : {{0: [{str(action)}]}}}}'

class TestRoutineFactory:
    def test_generate_routine_empty_template(self):
        routine_template = RoutineTemplate()
        factory = RoutineFactory()
        routine = factory.generate_routine(routine_template)
        
        assert routine.actions == {}

    def test_generate_routine_single_action(self):
        routine_template = RoutineTemplate()
        pop_template = PopulationTemplate()
        action = Action(action_type="TestAction", pop_template=pop_template, values={})
        routine_template.add_action_to_template(0, action)
        
        factory = RoutineFactory()
        routine = factory.generate_routine(routine_template)
        
        assert 0 in routine.actions
        assert routine.actions[0] == [action]

    def test_generate_routine_multiple_actions(self):
        routine_template = RoutineTemplate()
        pop_template = PopulationTemplate()
        action1 = Action(action_type="TestAction1", pop_template=pop_template, values={})
        action2 = Action(action_type="TestAction2", pop_template=pop_template, values={})
        action3 = Action(action_type="TestAction3", pop_template=pop_template, values={})
        
        routine_template.add_action_to_template(0, action1)
        routine_template.add_action_to_template(1, action2)
        routine_template.add_action_to_template(2, action3)
        
        factory = RoutineFactory()
        routine = factory.generate_routine(routine_template)
        
        assert 0 in routine.actions
        assert 1 in routine.actions
        assert 2 in routine.actions
        assert routine.actions[0] == [action1]
        assert routine.actions[1] == [action2]
        assert routine.actions[2] == [action3]

    def test_generate_routine_multiple_actions_same_cycle_step(self):
        routine_template = RoutineTemplate()
        pop_template = PopulationTemplate()
        action1 = Action(action_type="TestAction1", pop_template=pop_template, values={})
        action2 = Action(action_type="TestAction2", pop_template=pop_template, values={})
        
        routine_template.add_action_to_template(0, action1)
        routine_template.add_action_to_template(0, action2)
        
        factory = RoutineFactory()
        routine = factory.generate_routine(routine_template)
        
        assert 0 in routine.actions
        assert routine.actions[0] == [action1, action2]
