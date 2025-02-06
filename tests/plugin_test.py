import pytest
from core.plugin import ActionPlugin, BasePlugin, LoggerPlugin, RoutinePlugin
from core.routine import Action
from core.simulator import LodusSimulation

class TestBasePlugin:
    def test_load_plugin_not_implemented(self):
        class IncompletePlugin(BasePlugin):
            def update_time_step(self, cycle_step, simulation_step):
                pass

            def unload_plugin(self):
                pass

        with pytest.raises(TypeError):
            IncompletePlugin() # type: ignore

    def test_update_time_step_not_implemented(self):
        class IncompletePlugin(BasePlugin):
            def load_plugin(self, simulation: LodusSimulation):
                pass

            def unload_plugin(self):
                pass

        with pytest.raises(TypeError):
            IncompletePlugin() # type: ignore

    def test_unload_plugin_not_implemented(self):
        class IncompletePlugin(BasePlugin):
            def load_plugin(self, simulation: LodusSimulation):
                pass

            def update_time_step(self, cycle_step, simulation_step):
                pass

        with pytest.raises(TypeError):
            IncompletePlugin() # type: ignore

    def test_mock_plugin(self):
        class MockPlugin(BasePlugin):
            def load_plugin(self, simulation: LodusSimulation):
                pass

            def update_time_step(self, cycle_step: int, simulation_step: int):
                pass

            def unload_plugin(self):
                pass

        plugin = MockPlugin()
        assert plugin.load_plugin(None) is None # type: ignore
        assert plugin.update_time_step(None, None) is None # type: ignore
        assert plugin.unload_plugin() is None

class MockActionPlugin(ActionPlugin):
        def load_plugin(self, simulation: LodusSimulation):
            return super().load_plugin(simulation)
        def update_time_step(self, cycle_step, simulation_step):
            return super().update_time_step(cycle_step, simulation_step)
        def unload_plugin(self):
            return super().unload_plugin()

class TestActionPlugin:
    class TestActionPlugin:
        def test_add_execution_time(self):
            plugin = MockActionPlugin()
            plugin.add_execution_time("mock_action_type", 1.0)
            plugin.add_execution_time("mock_action_type", 2.0)
            assert plugin.execution_times["mock_action_type"] == [1.0, 2.0]

        def test_add_execution_time_invalid_time(self):
            plugin = MockActionPlugin()
            with pytest.raises(ValueError, match="time must be of type int or float"):
                plugin.add_execution_time("mock_action_type", "invalid_time") # type: ignore

        def test_add_execution_time_invalid_action_type(self):
            plugin = MockActionPlugin()
            with pytest.raises(ValueError, match="action_type must be of type str"):
                plugin.add_execution_time(123, 1.0) # type: ignore

        def test_print_execution_time_data(self, capsys):
            plugin = MockActionPlugin()
            plugin.add_execution_time("mock_action_type", 1.0)
            plugin.add_execution_time("mock_action_type", 2.0)
            output = plugin.print_execution_time_data() + '\n'
            captured = capsys.readouterr()
            assert "Number of executions: 2" in captured.out
            assert "Total execution time: 3.0" in captured.out
            assert "Average execution time: 1.5" in captured.out
            assert output == captured.out

        def test_print_execution_time_data_empty(self, capsys):
            plugin = MockActionPlugin()
            output = plugin.print_execution_time_data() + '\n'
            captured = capsys.readouterr()
            assert "Execution Time Data:" in captured.out
            assert "Number of executions: 0" not in captured.out
            assert output == captured.out

class TestRoutinePlugin:
    def test_routine_plugin_initialization(self):
        class MockRoutinePlugin(RoutinePlugin):
            def process_start_of_step_actions(self, cycle_step, simulation_step) -> list[Action]:
                return []

            def process_end_of_step_actions(self, cycle_step, simulation_step) -> list[Action]:
                return []

            def load_plugin(self, simulation: LodusSimulation):
                raise NotImplementedError

            def update_time_step(self, cycle_step: int, simulation_step: int):
                raise NotImplementedError

            def unload_plugin(self):
                raise NotImplementedError


        plugin = MockRoutinePlugin()
        assert plugin.start_of_step_global_actions == []
        assert plugin.start_of_step_actions == []
        assert plugin.end_of_step_global_actions == []
        assert plugin.end_of_step_actions == []

    def test_process_start_of_step_actions_not_implemented(self):
        class IncompleteRoutinePlugin(RoutinePlugin):
            def process_end_of_step_actions(self, cycle_step, simulation_step) -> list[Action]:
                return []

        with pytest.raises(TypeError):
            IncompleteRoutinePlugin() # type: ignore

    def test_process_end_of_step_actions_not_implemented(self):
        class IncompleteRoutinePlugin(RoutinePlugin):
            def process_start_of_step_actions(self, cycle_step, simulation_step) -> list[Action]:
                return []

        with pytest.raises(TypeError):
            IncompleteRoutinePlugin() # type: ignore

    def test_mock_routine_plugin(self):
        class MockRoutinePlugin(RoutinePlugin):
            def process_start_of_step_actions(self, cycle_step, simulation_step) -> list[Action]:
                return []

            def process_end_of_step_actions(self, cycle_step, simulation_step) -> list[Action]:
                return []

            def load_plugin(self, simulation: LodusSimulation):
                raise NotImplementedError

            def update_time_step(self, cycle_step: int, simulation_step: int):
                raise NotImplementedError

            def unload_plugin(self):
                raise NotImplementedError


        plugin = MockRoutinePlugin()
        assert plugin.process_start_of_step_actions(0, 0) == []
        assert plugin.process_end_of_step_actions(0, 0) == []


class TestLoggerPlugin:
    def test_setup_logger_not_implemented(self):
        class IncompleteLoggerPlugin(LoggerPlugin):
            def log_simulation_step(self):
                pass

            def stop_logger(self):
                pass

        with pytest.raises(TypeError):
            IncompleteLoggerPlugin() # type: ignore

    def test_log_simulation_step_not_implemented(self):
        class IncompleteLoggerPlugin(LoggerPlugin):
            def setup_logger(self):
                pass

            def stop_logger(self):
                pass

        with pytest.raises(TypeError):
            IncompleteLoggerPlugin() # type: ignore

    def test_stop_logger_not_implemented(self):
        class IncompleteLoggerPlugin(LoggerPlugin):
            def setup_logger(self):
                pass

            def log_simulation_step(self):
                pass

        with pytest.raises(TypeError):
            IncompleteLoggerPlugin() # type: ignore

    def test_mock_logger_plugin(self):
        class MockLoggerPlugin(LoggerPlugin):
            def setup_logger(self):
                pass

            def log_simulation_step(self):
                pass

            def stop_logger(self):
                pass

            def load_plugin(self, simulation: LodusSimulation):
                raise NotImplementedError

            def update_time_step(self, cycle_step: int, simulation_step: int):
                raise NotImplementedError

            def unload_plugin(self):
                raise NotImplementedError


        plugin = MockLoggerPlugin()
        assert plugin.setup_logger() is None
        assert plugin.log_simulation_step() is None
        assert plugin.stop_logger() is None