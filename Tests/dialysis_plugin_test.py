from pathlib import Path

from core.environment import EnvNode, EnvRegion, EnvironmentGraph
from core.population import BlobFactory, CharacteristicsFactory, PopulationTemplate
from core.simulator import LodusSimulation
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
        "clinic_name;opening_hour;closing_hour;treatment_capacity_per_hour\n"
        f"Test Clinic;0;23;{capacity}\n",
        encoding="utf8",
    )
    simulation = LodusSimulation(graph)
    simulation.set_cycle_length(24)
    simulation.experiment_config = {
        "dialysis_plugin": {
            "patient_count": patient_count,
            "treatment_frequency_days": frequency,
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
