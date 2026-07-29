import json

from core.population import PopulationTemplate
from plugins.data.custom_dependency_data_plugin import (
    CustomDependencyDataPlugin,
)
from plugins.data.node_dependency_data_plugin import (
    NodeDependencyDataPlugin,
)
from plugins.data.water_level_data_plugin import WaterLevelDataPlugin
from plugins.routines.off_cycle_routine_plugin import OffCycleRoutinePlugin
from plugins.time_actions.change_enabled_state_plugin import (
    ChangeEnabledStatePlugin,
)
from plugins.time_actions.dialysis_plugin import DialysisPlugin
from util.data_parse import generate_lodus_simulation
from util.random_instance import FixedRandom


def _reduced_simulation(name="dialysis_core/K00_ReducedReference"):
    FixedRandom(0, 0)
    simulation = generate_lodus_simulation(name)
    dependency = NodeDependencyDataPlugin()
    simulation.load_plugin(dependency)
    simulation.load_plugin(CustomDependencyDataPlugin())
    return simulation


def test_eta_failure_cascades_to_clinics_and_limits_dialysis():
    simulation = _reduced_simulation()
    dialysis = DialysisPlugin()
    simulation.load_plugin(dialysis)
    graph = simulation.env_graph

    graph.set_node_enabled(
        "Moinhos de Vento//water_source_0",
        False,
        cause="off_cycle",
    )

    clinics = graph.get_nodes_by_type("dialysis_clinic")
    assert sum(clinic.is_enabled() for clinic in clinics) == 2
    assert {
        clinic.containing_region_name
        for clinic in clinics
        if clinic.is_enabled()
    } == {"Azenha", "Praia de Belas"}

    dialysis.dialysis(PopulationTemplate(), {}, 6, 6)
    in_treatment = PopulationTemplate(
        traceable_characteristics={dialysis.STATUS: "in_treatment"}
    )
    assert graph.get_population_size(in_treatment) == 4

    graph.set_node_enabled(
        "Menino Deus//water_source_0",
        False,
        cause="off_cycle",
    )
    assert not any(clinic.is_enabled() for clinic in clinics)


def test_independent_blockers_must_all_clear():
    simulation = _reduced_simulation()
    graph = simulation.env_graph
    eta = graph.get_node_by_complete_name(
        "Moinhos de Vento//water_source_0"
    )

    graph.set_node_enabled(eta.get_complete_name(), False, cause="off_cycle")
    graph.set_node_enabled(eta.get_complete_name(), False, cause="flood")
    graph.set_node_enabled(eta.get_complete_name(), True, cause="off_cycle")

    assert not eta.is_enabled()
    assert eta.get_disable_reasons() == ("flood",)

    graph.set_node_enabled(eta.get_complete_name(), True, cause="flood")
    assert eta.is_enabled()
    assert eta.get_disable_reasons() == ()


def test_falling_water_recovers_only_nodes_without_other_blockers(tmp_path):
    levels = tmp_path / "levels.csv"
    levels.write_text(
        "cycle;cycle_step;water_level\n"
        "0;0;2.0\n"
        "0;1;10.1\n"
        "0;2;2.0\n",
        encoding="utf8",
    )
    simulation = _reduced_simulation()
    simulation.experiment_config["water_level_data_plugin"] = {
        "data_file": str(levels),
        "target_node_types": ["water_source"],
    }
    water = WaterLevelDataPlugin()
    simulation.load_plugin(water)
    graph = simulation.env_graph
    moinhos = graph.get_node_by_complete_name(
        "Moinhos de Vento//water_source_0"
    )
    menino = graph.get_node_by_complete_name(
        "Menino Deus//water_source_0"
    )

    water.update_time_step(0, 0)
    water.update_time_step(1, 1)
    assert not moinhos.is_enabled()
    assert not menino.is_enabled()

    graph.set_node_enabled(
        moinhos.get_complete_name(), False, cause="off_cycle"
    )
    water.update_time_step(2, 2)

    assert not moinhos.is_enabled()
    assert moinhos.get_disable_reasons() == ("off_cycle",)
    assert menino.is_enabled()
    assert sum(
        clinic.is_enabled()
        for clinic in graph.get_nodes_by_type("dialysis_clinic")
    ) == 2


def test_start_of_step_outage_precedes_dialysis_admission():
    simulation = _reduced_simulation(
        "dialysis_core/K02_MoinhosNoRecovery"
    )
    simulation.load_plugin(ChangeEnabledStatePlugin())
    dialysis = DialysisPlugin()
    simulation.load_plugin(dialysis)
    simulation.load_plugin(OffCycleRoutinePlugin())
    events = []
    dialysis.add_event_listener("test", events.append)

    for _ in range(79):
        simulation.update_time_step()

    admissions = [
        event
        for event in events
        if event["simulation_step"] == 78
        and event["event_type"] == "admitted"
    ]
    assert sum(event["population"] for event in admissions) == 4
    assert {
        event["clinic_region"] for event in admissions
    } <= {"Azenha", "Praia de Belas"}


def test_complete_environment_ignores_missing_water_thresholds(tmp_path):
    levels = tmp_path / "levels.csv"
    levels.write_text(
        "cycle;cycle_step;water_level\n0;0;2.0\n",
        encoding="utf8",
    )
    FixedRandom(0, 0)
    simulation = generate_lodus_simulation(
        "dialysis_core/K10_CompleteModerate"
    )
    simulation.experiment_config["water_level_data_plugin"] = {
        "data_file": str(levels)
    }
    water = WaterLevelDataPlugin()
    simulation.load_plugin(water)

    water.update_time_step(0, 0)

    assert water.current_water_level == 2.0


def test_same_seed_reproduces_selected_patient_origins():
    def selected_origins(seed):
        FixedRandom(seed, seed)
        simulation = generate_lodus_simulation(
            "dialysis_core/K00_ReducedReference"
        )
        dialysis = DialysisPlugin()
        simulation.load_plugin(dialysis)
        patient = PopulationTemplate(
            traceable_characteristics={dialysis.PATIENT: True}
        )
        return {
            node.get_complete_name(): node.get_population_size(patient)
            for node in simulation.env_graph.node_list
            if node.get_population_size(patient)
        }

    assert selected_origins(4) == selected_origins(4)
    assert selected_origins(4) != selected_origins(5)
