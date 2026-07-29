from util.simulation_time import SimulationTimeStatus
from core.environment import EnvironmentGraph
from core.simulator import LodusSimulation


def test_simulation_time_status_properties():
    time_status = SimulationTimeStatus(
        simulation_step=27,
        cycle_length=12,
        total_cycles=3,
    )

    assert time_status.cycle_step == 3
    assert time_status.simulation_step == 27
    assert time_status.cycle_length == 12
    assert time_status.cycle == 2
    assert time_status.is_cycle_start is False






def test_lodus_simulation_updates_time_status():
    simulation = LodusSimulation(EnvironmentGraph())
    simulation.set_cycle_length(4)

    simulation.update_time_step()

    assert simulation.time_status is not None
    assert simulation.time_status.cycle_step == 0
    assert simulation.time_status.simulation_step == 0
    assert simulation.time_status.cycle_length == 4
    assert simulation.time_status.cycle == 0
    assert simulation.time_status.is_cycle_start is True


def test_lodus_simulation_uses_time_status_for_cycle_length():
    simulation = LodusSimulation(EnvironmentGraph())

    assert simulation.time_status.cycle_length == 24
    assert not hasattr(simulation, "cycle_length")
