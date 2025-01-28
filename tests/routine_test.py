from typing import List, Set
from random_inst import FixedRandom

import pytest
from core.population import Blob, BlobFactory, CharacteristicsFactory, PopulationTemplate, SampledCharacteristic, SampledCharacteristicCollection
from core.routine import TimeAction, Routine

@pytest.fixture(scope="session", autouse=True)
def start_fixedrandom():
    """Initialize FixedRandom to ensure deterministic behavior in tests."""
    FixedRandom()  # Ensure FixedRandom is defined or imported properly.

class TestAction:
    def test_time_action_initialization(self):
        pop_template = PopulationTemplate()
        values = {"key1": "value1", "key2": "value2"}
        action = TimeAction(action_type="TestAction", pop_template=pop_template, values=values)
        
        assert action.action_type == "TestAction"
        assert action.pop_template == pop_template
        assert action.values == values

    def test_time_action_invalid_pop_template(self):
        with pytest.raises(ValueError, match="pop_template must be of type PopulationTemplate"):
            TimeAction(action_type="TestAction", pop_template="InvalidTemplate", values={}) # type: ignore

class TestRoutine:
    def test_routine_initialization(self):
        routine = Routine(routine_label="TestRoutine")
        assert routine.label == "TestRoutine"
        assert routine.actions == {}

    def test_add_time_action(self):
        routine = Routine()
        pop_template = PopulationTemplate()
        action = TimeAction(action_type="TestAction", pop_template=pop_template, values={})
        
        routine.add_time_action(0, action)
        assert 0 in routine.actions
        assert routine.actions[0] == [action]

    def test_add_time_action_multiple(self):
        routine = Routine()
        pop_template = PopulationTemplate()
        action1 = TimeAction(action_type="TestAction1", pop_template=pop_template, values={})
        action2 = TimeAction(action_type="TestAction2", pop_template=pop_template, values={})
        action3 = TimeAction(action_type="TestAction3", pop_template=pop_template, values={})
        
        routine.add_time_action(0, action1)
        routine.add_time_action(0, action2)
        routine.add_time_action(1, action3)
        assert 0 in routine.actions
        assert routine.actions[0] == [action1, action2]
        assert routine.actions[1] == [action3]

    def test_add_time_action_invalid_time_action(self):
        routine = Routine()
        with pytest.raises(ValueError, match="time_action must be of type TimeAction"):
            routine.add_time_action(0, "InvalidAction")  # type: ignore

    def test_add_time_action_invalid_cycle_step(self):
        routine = Routine()
        pop_template = PopulationTemplate()
        action = TimeAction(action_type="TestAction", pop_template=pop_template, values={})
        
        with pytest.raises(ValueError, match="cycle_step must be a non-negative integer"):
            routine.add_time_action(-1, action)

    def test_process_routine(self):
        routine = Routine()
        pop_template = PopulationTemplate()
        action1 = TimeAction(action_type="TestAction1", pop_template=pop_template, values={})
        action2 = TimeAction(action_type="TestAction2", pop_template=pop_template, values={})
        action3 = TimeAction(action_type="TestAction3", pop_template=pop_template, values={})
        
        routine.add_time_action(0, action1)
        routine.add_time_action(0, action2)
        routine.add_time_action(1, action3)
        
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
        action = TimeAction(action_type="TestAction", pop_template=pop_template, values={})
        
        routine.add_time_action(0, action)
        routine_str = str(routine)
        assert routine_str == f'{{"name" : "TestRoutine", "actions"  : {{0: [{str(action)}]}}}}'