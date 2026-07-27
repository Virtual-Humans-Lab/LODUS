from pathlib import Path

import pandas as pd

from core.environment import EnvNode, EnvRegion, EnvironmentGraph
from core.population import BlobFactory, CharacteristicsFactory, PopulationTemplate
from core.simulator import LodusSimulation
from plugins.loggers.dialysis_logger import DialysisLogger
from plugins.time_actions.dialysis_plugin import DialysisPlugin
from util.random_instance import FixedRandom


def _simulation(tmp_path: Path, patient_count=4, frequency=2, capacity=2):
    FixedRandom(random_seed=0, numpy_seed=0)
    graph = EnvironmentGraph()
    region = EnvRegion("Region", [0.0, 0.0])
    home = EnvNode("home", "home")
    clinic = EnvNode("dialysis_clinic", "clinic")
    home.containing_region_name = clinic.containing_region_name = "Region"
    home.long_lat = [0.0, 0.0]
    clinic.long_lat = [1.0, 0.0]
    clinic.add_attribute("clinic_name", "Test Clinic")

    for node in (home, clinic):
        region.node_list.append(node)
        region.node_dict[node.unique_name] = node
        graph.node_list.append(node)
        graph.node_dict[node.get_complete_name()] = node
        graph.node_id_dict[node.id] = node
    graph.region_list.append(region)
    graph.region_dict[region.name] = region
    graph.region_id_dict[region.id] = region

    characteristics = CharacteristicsFactory()
    characteristics.add_sampled_characteristic("age", ["adult"])
    factory = BlobFactory(characteristics)
    home.add_blob(factory.generate_blob_rand(0, home.id, 10))

    clinic_file = tmp_path / "clinics.csv"
    clinic_file.write_text(
        "clinic_name;opening_step;closing_step;treatment_capacity_per_step\n"
        f"Test Clinic;0;23;{capacity}\n",
        encoding="utf8",
    )
    simulation = LodusSimulation(graph)
    simulation.set_cycle_length(24)
    simulation.experiment_config = {
        "dialysis_plugin": {
            "patient_count": patient_count,
            "treatment_frequency_days": frequency,
            "max_patients_per_node": 10,
            "clinic_data_file": str(clinic_file),
        }
    }
    plugin = DialysisPlugin()
    simulation.load_plugin(plugin)
    return simulation, plugin, home, clinic


def test_initial_population_is_traceable_and_phased(tmp_path):
    _, plugin, home, _ = _simulation(tmp_path)
    patients = PopulationTemplate(
        traceable_characteristics={plugin.PATIENT: True}
    )
    assert home.get_population_size(patients) == 4
    assert home.get_population_size(
        PopulationTemplate(
            traceable_characteristics={plugin.NEXT_DUE: 0}
        )
    ) == 2
    assert home.get_population_size(
        PopulationTemplate(
            traceable_characteristics={plugin.NEXT_DUE: 1}
        )
    ) == 2


def test_moves_treats_next_frame_and_returns(tmp_path):
    _, plugin, home, clinic = _simulation(tmp_path)
    plugin.dialysis(PopulationTemplate(), {}, 0, 0)

    in_treatment = PopulationTemplate(
        traceable_characteristics={plugin.STATUS: "in_treatment"}
    )
    assert clinic.get_population_size(in_treatment) == 2
    assert home.get_population_size() == 8

    plugin.dialysis(PopulationTemplate(), {}, 1, 1)

    assert clinic.get_population_size(in_treatment) == 0
    assert home.get_population_size() == 10
    next_due = PopulationTemplate(
        traceable_characteristics={plugin.NEXT_DUE: 2}
    )
    assert home.get_population_size(next_due) == 2


def test_disabled_clinic_does_not_admit_patients(tmp_path):
    _, plugin, home, clinic = _simulation(tmp_path)
    clinic.disable()
    plugin.dialysis(PopulationTemplate(), {}, 0, 0)

    assert clinic.get_population_size() == 0
    assert home.get_population_size() == 10


def test_csv_schedule_overrides_defaults_and_defaults_cover_other_clinics(tmp_path):
    _, plugin, _, clinic = _simulation(tmp_path)
    second_clinic = EnvNode("dialysis_clinic", "second_clinic")
    second_clinic.containing_region_name = "Region"
    second_clinic.add_attribute("clinic_name", "Second Clinic")
    plugin.env_graph.node_list.append(second_clinic)
    plugin.env_graph.node_id_dict[second_clinic.id] = second_clinic
    plugin.default_values = {
        "opening_step": 6,
        "closing_step": 18,
        "treatment_capacity_per_step": 3,
    }

    schedules = plugin._load_clinic_schedules(
        plugin.config["clinic_data_file"]
    )

    assert schedules[clinic.id] == [(0, 23, 2)]
    assert schedules[second_clinic.id] == [(6, 18, 3)]


def test_defaults_can_be_used_without_csv(tmp_path):
    _, plugin, _, clinic = _simulation(tmp_path)
    plugin.default_values = {
        "opening_step": 7,
        "closing_step": 19,
        "treatment_capacity_per_step": 4,
    }

    assert plugin._load_clinic_schedules(None) == {
        clinic.id: [(7, 19, 4)]
    }


def test_csv_can_be_used_without_defaults(tmp_path):
    _, plugin, _, clinic = _simulation(tmp_path)
    plugin.default_values = {}

    schedules = plugin._load_clinic_schedules(
        plugin.config["clinic_data_file"]
    )

    assert schedules == {clinic.id: [(0, 23, 2)]}


def test_schedule_source_is_required(tmp_path):
    _, plugin, _, _ = _simulation(tmp_path)
    plugin.default_values = {}

    try:
        plugin._load_clinic_schedules(None)
    except ValueError as error:
        assert "clinic_data_file" in str(error)
        assert "default_values" in str(error)
    else:
        raise AssertionError("Expected missing clinic schedule sources to fail")


def _patient_selection_plugin(patient_count, max_per_node):
    FixedRandom(random_seed=0, numpy_seed=0)
    graph = EnvironmentGraph()
    characteristics = CharacteristicsFactory()
    characteristics.add_sampled_characteristic("age", ["adult"])
    factory = BlobFactory(characteristics)
    nodes = []

    for index in range(3):
        node = EnvNode("home", f"home_{index}")
        node.add_blob(factory.generate_blob_rand(0, node.id, 10))
        graph.node_list.append(node)
        nodes.append(node)

    excluded = EnvNode("work", "work")
    excluded.add_blob(factory.generate_blob_rand(0, excluded.id, 10))
    graph.node_list.append(excluded)

    plugin = DialysisPlugin()
    plugin.env_graph = graph
    plugin.patient_count = patient_count
    plugin.frequency_days = 2
    plugin.patient_node_type = "home"
    plugin.max_patients_per_node = max_per_node
    plugin._add_traceable_defaults()
    return plugin, nodes, excluded


def test_patient_selection_filters_node_type_and_caps_randomized_nodes():
    plugin, homes, excluded = _patient_selection_plugin(4, 2)

    plugin._select_patients()

    patients = PopulationTemplate(
        traceable_characteristics={plugin.PATIENT: True}
    )
    home_counts = [node.get_population_size(patients) for node in homes]
    assert sorted(home_counts) == [0, 2, 2]
    assert excluded.get_population_size(patients) == 0


def test_patient_selection_rejects_count_above_eligible_node_capacity():
    plugin, _, _ = _patient_selection_plugin(7, 2)

    try:
        plugin._select_patients()
    except ValueError as error:
        assert "selection capacity (6)" in str(error)
        assert "max_patients_per_node=2" in str(error)
    else:
        raise AssertionError("Expected patient selection capacity to fail")


def test_dialysis_logger_records_events_snapshots_and_outputs(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    simulation, plugin, home, clinic = _simulation(tmp_path)
    logger = DialysisLogger(export_png=False)
    simulation.load_plugin(logger)
    simulation.setup_logging()

    logger.update_time_step(0, 0)
    plugin.dialysis(PopulationTemplate(), {}, 0, 0)
    logger.log_simulation_step()
    logger.update_time_step(1, 1)
    plugin.dialysis(PopulationTemplate(), {}, 1, 1)
    logger.log_simulation_step()
    logger.stop_logger()

    events = logger._events_dataframe()
    admitted = events[events["Event"] == "admitted"]
    completed = events[events["Event"] == "completed"]
    assert admitted["Population"].sum() == 2
    assert completed["Population"].sum() == 2
    assert set(events["Origin"]) == {home.get_complete_name()}
    assert set(events["Clinic"]) == {clinic.get_complete_name()}
    assert completed.iloc[0]["Treatment Frame"] == 1

    step = pd.DataFrame(logger.step_rows)
    assert step["Admitted"].tolist() == [2, 0]
    assert step["Completed"].tolist() == [0, 2]
    clinic_step = pd.DataFrame(logger.clinic_rows)
    assert clinic_step["Occupancy"].tolist() == [2, 0]

    data_path = (
        tmp_path / "output_logs" / simulation.experiment_name / "data_frames"
    )
    for filename in [
        "dialysis_events.csv",
        "dialysis_step.csv",
        "dialysis_clinic_step.csv",
        "dialysis_cycle.csv",
        "dialysis_origin_clinic.csv",
    ]:
        assert (data_path / filename).is_file()

    html_path = (
        tmp_path
        / "output_logs"
        / simulation.experiment_name
        / "html_plots"
        / "dialysis"
    )
    assert (html_path / "dashboard.html").is_file()
    assert (html_path / "origin_clinic_sankey.html").is_file()


def test_dialysis_logger_handles_empty_simulation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    simulation, _, _, _ = _simulation(tmp_path, patient_count=0)
    logger = DialysisLogger(export_png=False)
    simulation.load_plugin(logger)
    simulation.setup_logging()

    logger.update_time_step(0, 0)
    logger.log_simulation_step()
    logger.stop_logger()

    events_path = (
        tmp_path
        / "output_logs"
        / simulation.experiment_name
        / "data_frames"
        / "dialysis_events.csv"
    )
    events = pd.read_csv(events_path, sep=";")
    assert list(events.columns) == DialysisLogger.EVENT_COLUMNS
    assert events.empty


def test_dialysis_logger_does_not_consume_randomness(tmp_path):
    simulation, _, _, _ = _simulation(tmp_path)
    state_before = FixedRandom.instance.getstate()
    logger = DialysisLogger(export_png=False)

    simulation.load_plugin(logger)
    logger.setup_logger()
    logger.update_time_step(0, 0)
    logger.log_simulation_step()

    assert FixedRandom.instance.getstate() == state_before
