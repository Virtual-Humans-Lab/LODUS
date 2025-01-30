import pytest
from core.plugin import ActionPlugin, BasePlugin

class TestBasePlugin:
    def test_setup_logger_not_implemented(self):
        class IncompletePlugin(BasePlugin):
            def update_time_step(self, cycle_step, simulation_step):
                pass

            def log_data(self, logger):
                pass

            def stop_logger(self, logger):
                pass

            def unload_plugin(self):
                pass

        with pytest.raises(TypeError):
            IncompletePlugin()

    def test_update_time_step_not_implemented(self):
        class IncompletePlugin(BasePlugin):
            def setup_logger(self, logger):
                pass

            def log_data(self, logger):
                pass

            def stop_logger(self, logger):
                pass

            def unload_plugin(self):
                pass

        with pytest.raises(TypeError):
            IncompletePlugin()

    def test_log_data_not_implemented(self):
        class IncompletePlugin(BasePlugin):
            def setup_logger(self, logger):
                pass

            def update_time_step(self, cycle_step, simulation_step):
                pass

            def stop_logger(self, logger):
                pass

            def unload_plugin(self):
                pass

        with pytest.raises(TypeError):
            IncompletePlugin()

    def test_stop_logger_not_implemented(self):
        class IncompletePlugin(BasePlugin):
            def setup_logger(self, logger):
                pass

            def update_time_step(self, cycle_step, simulation_step):
                pass

            def log_data(self, logger):
                pass

            def unload_plugin(self):
                pass

        with pytest.raises(TypeError):
            IncompletePlugin()

    def test_unload_plugin_not_implemented(self):
        class IncompletePlugin(BasePlugin):
            def setup_logger(self, logger):
                pass

            def update_time_step(self, cycle_step, simulation_step):
                pass

            def log_data(self, logger):
                pass

            def stop_logger(self, logger):
                pass

        with pytest.raises(TypeError):
            IncompletePlugin()

    def test_mock_plugin(self):
        class MockPlugin(BasePlugin):
            def setup_logger(self, logger):
                pass

            def update_time_step(self, cycle_step, simulation_step):
                pass

            def log_data(self, logger):
                pass

            def stop_logger(self, logger):
                pass

            def unload_plugin(self):
                pass

        plugin = MockPlugin()
        assert plugin.setup_logger(None) is None
        assert plugin.update_time_step(None, None) is None
        assert plugin.log_data(None) is None
        assert plugin.stop_logger(None) is None
        assert plugin.unload_plugin() is None

class MockActionPlugin(ActionPlugin):
        def setup_logger(self, logger):
            return super().setup_logger(logger)
        def update_time_step(self, cycle_step, simulation_step):
            return super().update_time_step(cycle_step, simulation_step)
        def log_data(self, logger):
            return super().log_data(logger)
        def stop_logger(self, logger):
            return super().stop_logger(logger)
        def unload_plugin(self):
            return super().unload_plugin()

class TestActionPlugin:
    def test_add_execution_time(self):
        plugin = MockActionPlugin()
        plugin.add_execution_time(1.0)
        plugin.add_execution_time(2.0)
        assert plugin.execution_times == [1.0, 2.0]

    def test_print_execution_time_data(self, capsys):
        plugin = MockActionPlugin()
        plugin.add_execution_time(1.0)
        plugin.add_execution_time(2.0)
        output = plugin.print_execution_time_data() + '\n'
        captured = capsys.readouterr()
        assert "Number of executions: 2" in captured.out
        assert "Total execution time: 3.0" in captured.out
        assert "Average execution time: 1.5" in captured.out
        assert output == captured.out

    def test_add_action_type_to_function(self):
        plugin = MockActionPlugin()
        def dummy_action():
            pass
        plugin.add_action_type_to_function("dummy", dummy_action)
        assert plugin.action_type_to_function["dummy"] == dummy_action

    def test_add_action_type_to_function_invalid_type(self):
        plugin = MockActionPlugin()
        with pytest.raises(ValueError):
            plugin.add_action_type_to_function(123, lambda: None)

    def test_add_action_type_to_function_invalid_callable(self):
        plugin = MockActionPlugin()
        with pytest.raises(ValueError):
            plugin.add_action_type_to_function("dummy", "not_callable")

    def test_get_action_type_to_function(self):
        plugin = MockActionPlugin()
        def dummy_action():
            pass
        plugin.add_action_type_to_function("dummy", dummy_action)
        action_dict = plugin.get_action_type_to_function()
        assert action_dict == {"dummy": dummy_action}