import json
from pathlib import Path

import pytest

from core.environment import EnvNode, EnvRegion, EnvironmentGraph
from core.population import BlobFactory, CharacteristicsFactory
from core.simulator import LodusSimulation
from plugins.time_actions.shelter_plugin import ShelterPlugin
from util.data_parse import generate_lodus_simulation
from util.random_instance import FixedRandom


@pytest.fixture(autouse=True)
def deterministic_random():
    FixedRandom(0, 0)


def add_region(graph: EnvironmentGraph, name: str) -> EnvRegion:
    region = EnvRegion(name, [-51.2, -30.1])
    graph.region_list.append(region)
    graph.region_dict[name] = region
    graph.region_id_dict[region.id] = region
    return region


def blob_factory() -> BlobFactory:
    factory = CharacteristicsFactory()
    factory.add_sampled_characteristic("age", ["adults"])
    factory.add_sampled_characteristic("occupation", ["worker"])
    factory.add_traceable_characteristic(
        ShelterPlugin.STATUS, ShelterPlugin.SAFE
    )
    return BlobFactory(factory)


def add_population(
    factory: BlobFactory,
    region: EnvRegion,
    node: EnvNode,
    population: int,
    status: str,
):
    node.add_blob(
        factory.generate_blob_rand(
            region.id,
            node.id,
            population,
            {ShelterPlugin.STATUS: status},
        )
    )


def behavior_fixture():
    graph = EnvironmentGraph()
    region = add_region(graph, "Region")
    factory = blob_factory()
    origin = graph.add_envnode("Region", EnvNode("shelter", "shelter_a"))
    origin.add_attribute("capacity", 2)
    origin.add_attribute("shelter_name", "A")
    target = graph.add_envnode("Region", EnvNode("shelter", "shelter_b"))
    target.add_attribute("capacity", 3)
    target.add_attribute("shelter_name", "B")
    add_population(factory, region, origin, 2, ShelterPlugin.SHELTERED)
    add_population(factory, region, origin, 4, ShelterPlugin.IN_DANGER)
    add_population(factory, region, target, 1, ShelterPlugin.SHELTERED)
    simulation = LodusSimulation(graph)
    plugin = ShelterPlugin()
    plugin.simulation = simulation
    plugin.env_graph = graph
    plugin.shelters = [origin, target]
    return plugin, origin, target


def test_shelter_admission_enforces_capacity_and_disabled_state():
    plugin, origin, target = behavior_fixture()
    plugin.shelter_population(
        plugin.in_danger_template,
        {"node_id": origin.id},
        8,
        8,
    )
    assert origin.get_population_size(plugin.sheltered_template) == 2
    assert origin.get_population_size(plugin.in_danger_template) == 4

    target.disable("test")
    add_population(
        blob_factory(),
        plugin.env_graph.region_dict["Region"],
        target,
        1,
        ShelterPlugin.IN_DANGER,
    )
    plugin.shelter_population(
        plugin.in_danger_template,
        {"node_id": target.id},
        8,
        8,
    )
    assert target.get_population_size(plugin.sheltered_template) == 1
    assert any(
        event["event_type"] == "admission_denied"
        and event["reason"] == "disabled"
        for event in plugin.events
    )


def test_reallocation_is_capacity_limited_and_once_per_absolute_step():
    plugin, _, target = behavior_fixture()
    actions = plugin.reallocate_shelter_waitlist(
        plugin.in_danger_template, {}, 9, 9
    )
    assert sum(action.values["quantity"] for action in actions) == 2
    assert plugin.reallocate_shelter_waitlist(
        plugin.in_danger_template, {}, 9, 9
    ) == []
    later = plugin.reallocate_shelter_waitlist(
        plugin.in_danger_template, {}, 9, 33
    )
    assert sum(action.values["quantity"] for action in later) == 2

    target.disable("test")
    assert plugin.reallocate_shelter_waitlist(
        plugin.in_danger_template, {}, 9, 57
    ) == []


def test_alias_resolution_is_explicit_and_unresolved_names_fail():
    graph = EnvironmentGraph()
    add_region(graph, "Passo D'Areia")
    add_region(graph, "Jardim Itú")
    add_region(graph, "Rio Branco")
    plugin = ShelterPlugin()
    plugin.env_graph = graph
    source = Path("test.csv")
    assert plugin._resolve_region_name("PASSO DA AREIA", source) == "Passo D'Areia"
    assert plugin._resolve_region_name("Jardim Ypu", source) == "Jardim Itú"
    assert plugin._resolve_region_name("Rio Banco", source) == "Rio Branco"
    with pytest.raises(ValueError, match="unresolved shelter region"):
        plugin._resolve_region_name("Unknown", source)


def test_zero_capacity_exclusion_and_configured_imputation(tmp_path):
    csv_path = tmp_path / "shelters.csv"
    csv_path.write_text(
        "id,Latitude,Longitude,name,region,address,abrigo,capacity,shelteredPeople\n"
        "1,-30.1,-51.2,Known,Region,,Sim,10,2\n"
        "2,-30.1,-51.2,Missing,Region,,Sim,,0\n",
        encoding="utf-8",
    )
    graph = EnvironmentGraph()
    add_region(graph, "Region")

    excluded = ShelterPlugin()
    excluded.env_graph = graph
    excluded.config = {"shelter_data": str(csv_path)}
    rows = excluded.load_initial_shelter_data()
    assert len(rows) == 1
    assert any(
        row["audit_type"] == "dropped_shelter"
        for row in excluded.input_audit
    )

    imputed = ShelterPlugin()
    imputed.env_graph = graph
    imputed.config = {
        "shelter_data": str(csv_path),
        "initial_shelter_capacity": 20,
    }
    rows = imputed.load_initial_shelter_data()
    assert len(rows) == 2
    assert sum(row["capacity"] for row in rows) == 20
    assert any(
        row["audit_type"] == "capacity_imputation"
        for row in imputed.input_audit
    )


def test_nonzero_outsider_occupancy_is_rejected():
    simulation = generate_lodus_simulation("shelter_tests/initial_test")
    simulation.experiment_config["shelter_plugin"][
        "outsiders_initially_sheltered"
    ] = 1
    with pytest.raises(ValueError, match="unsupported"):
        simulation.load_plugin(ShelterPlugin())


@pytest.mark.parametrize(
    ("experiment", "shelters", "capacity", "occupancy", "exposure", "shortfall"),
    [
        ("initial_test", 0, 0, 0, 126606, 0),
        ("load_shelters_test", 64, 10803, 8062, 126606, 0),
        ("census_areas_test", 64, 10803, 8062, 126466, 140),
        ("census_shelters_v2_test", 121, 14958, 12224, 126466, 140),
        ("census_5m30_shelters_v3_test", 104, 12519, 10963, 182936, 3586),
        (
            "census_5m30_shelters_v3_daily_1%_test",
            104, 12519, 10963, 182936, 3586,
        ),
        (
            "census_5m30_shelters_v3_daily_1%_reallocate_test",
            104, 12519, 10963, 182936, 3586,
        ),
    ],
)
def test_established_experiment_inputs(
    experiment, shelters, capacity, occupancy, exposure, shortfall
):
    simulation = generate_lodus_simulation(f"shelter_tests/{experiment}")
    plugin = ShelterPlugin()
    simulation.load_plugin(plugin)
    assert len(plugin.shelters) == shelters
    assert sum(
        node.get_attribute("capacity") for node in plugin.shelters
    ) == capacity
    assert sum(
        node.get_attribute("initial_sheltered") for node in plugin.shelters
    ) == occupancy
    assert sum(plugin.exposure_by_region.values()) == exposure
    assert sum(
        row.get("shortfall", 0)
        for row in plugin.input_audit
        if row["audit_type"] == "population_shortfall"
    ) == shortfall


def test_shelter_routines_use_ordered_global_scopes():
    data_path = Path(__file__).parents[1] / "data_input" / "shelters"
    regular = json.loads(
        (data_path / "Routine-ShelterDaily1Percent.json").read_text()
    )
    reallocate = json.loads(
        (data_path / "Routine-ShelterDaily1PercentReallocate.json").read_text()
    )
    assert [
        action["cycle_step"] for action in regular["global_routine"]
    ] == [[7], [8]]
    by_type = {
        entry["action"]["type"]: entry
        for entry in reallocate["global_routine"]
    }
    assert by_type["move_to_shelters"]["cycle_step"] == [7]
    assert by_type["shelter_population"]["cycle_step"] == [8, 10]
    assert by_type["reallocate_shelter_waitlist"]["cycle_step"] == [9]
    assert (
        by_type["reallocate_shelter_waitlist"]["execution_scope"] == "once"
    )
