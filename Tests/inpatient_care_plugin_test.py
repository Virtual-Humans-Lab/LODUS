import csv
import json
from pathlib import Path

import pandas as pd
import pytest

from core.environment import EnvNode, EnvRegion, EnvironmentGraph
from core.population import (
    BlobFactory,
    CharacteristicsFactory,
    PopulationTemplate,
)
from core.routine import Routine
from core.simulator import LodusSimulation
from plugins.loggers.inpatient_care_logger import InpatientCareLogger
from plugins.time_actions.inpatient_care_plugin import InpatientCarePlugin
from util.random_instance import FixedRandom


def _register(graph, region, node):
    node.routine = Routine()
    node.containing_region_name = region.name
    region.node_list.append(node)
    region.node_dict[node.get_complete_name()] = node
    graph.node_list.append(node)
    graph.node_dict[node.get_complete_name()] = node
    graph.node_id_dict[node.id] = node


def _write_capacity(path: Path, rows: list[dict]):
    with path.open("w", encoding="utf8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "hospital",
                "region",
                "longitude",
                "latitude",
                "specialty",
                "bed_type",
                "total_beds",
                "sus_beds",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def _simulation(
    tmp_path: Path,
    demands: list[dict],
    *,
    capacity_policy="overflow",
    allow_hospital_change=False,
    capacity_rows=None,
    population=30,
    cycles=3,
    cycle_length=1,
    seed=0,
):
    FixedRandom(random_seed=seed, numpy_seed=seed)
    graph = EnvironmentGraph()
    characteristics = CharacteristicsFactory()
    characteristics.add_sampled_characteristic("age", ["adult"])
    factory = BlobFactory(characteristics)
    definitions = [
        ("Origin", [0.0, 0.0], "H1", [1.0, 0.0]),
        ("Alternative", [3.0, 0.0], "H2", [2.0, 0.0]),
    ]
    for region_name, location, hospital_name, hospital_location in definitions:
        region = EnvRegion(region_name, location)
        graph.region_list.append(region)
        graph.region_dict[region.name] = region
        graph.region_id_dict[region.id] = region
        home = EnvNode("home", "home")
        home.long_lat = location
        home.add_blob(
            factory.generate_blob_rand(region.id, home.id, population)
        )
        hospital = EnvNode("hospital", f"hospital_{hospital_name.lower()}")
        hospital.long_lat = hospital_location
        hospital.add_attribute("hospital_name", hospital_name)
        _register(graph, region, home)
        _register(graph, region, hospital)

    capacity_rows = capacity_rows or [
        {
            "hospital": "H1",
            "region": "Origin",
            "longitude": 1,
            "latitude": 0,
            "specialty": "Psychiatry",
            "bed_type": "Other",
            "total_beds": 2,
            "sus_beds": 1,
        },
        {
            "hospital": "H2",
            "region": "Alternative",
            "longitude": 2,
            "latitude": 0,
            "specialty": "Psychiatry",
            "bed_type": "Other",
            "total_beds": 6,
            "sus_beds": 5,
        },
    ]
    capacity_file = tmp_path / "capacity.csv"
    _write_capacity(capacity_file, capacity_rows)
    simulation = LodusSimulation(graph)
    simulation.set_total_cycles(cycles)
    simulation.set_cycle_length(cycle_length)
    simulation.experiment_config = {
        "inpatient_care_plugin": {
            "capacity_file": str(capacity_file),
            "capacity_policy": capacity_policy,
            "allow_hospital_change": allow_hospital_change,
            "demand_sources": [
                {
                    "adapter": "specialty_totals",
                    "records": demands,
                }
            ],
        }
    }
    plugin = InpatientCarePlugin()
    simulation.load_plugin(plugin)
    return simulation, plugin


def _demand(
    total=4,
    sus=2,
    *,
    hospital="H1",
    start=0,
    end=0,
    los_min=1,
    los_max=1,
):
    return {
        "origin_region": "Origin",
        "preferred_hospital": hospital,
        "specialty": "Psychiatry",
        "bed_type": "Other",
        "total_admissions": total,
        "sus_admissions": sus,
        "los_min_steps": los_min,
        "los_max_steps": los_max,
        "start_step": start,
        "end_step": end,
    }


def test_capacity_partitions_total_into_sus_and_private(tmp_path):
    _, plugin = _simulation(tmp_path, [_demand(total=1, sus=1)])
    hospital = plugin.hospital_nodes["H1"]
    assert plugin.configured_capacity(
        hospital.id, "Psychiatry", "Other", "sus"
    ) == 1
    assert plugin.configured_capacity(
        hospital.id, "Psychiatry", "Other", "private"
    ) == 1


def test_overflow_admits_all_and_returns_to_origin(tmp_path):
    simulation, plugin = _simulation(tmp_path, [_demand()])
    initial_population = simulation.env_graph.get_population_size()
    events = []
    plugin.add_event_listener("test", events.append)

    simulation.update_time_step()
    hospital = plugin.hospital_nodes["H1"]
    assert hospital.get_population_size() == 4
    assert plugin.occupancy(
        hospital.id, "Psychiatry", "Other", "sus"
    ) == 2
    assert plugin.available_capacity(
        hospital.id, "Psychiatry", "Other", "sus"
    ) == 0

    simulation.update_time_step()
    assert hospital.get_population_size() == 0
    assert simulation.env_graph.get_population_size() == initial_population
    assert sum(
        event["population"]
        for event in events
        if event["event_type"] == "discharged"
    ) == 4
    assert simulation.env_graph.get_population_size(
        PopulationTemplate(
            traceable_characteristics={plugin.EVER_ADMITTED: True}
        )
    ) == 4


def test_queue_enforces_capacity_and_reuses_discharged_beds(tmp_path):
    simulation, plugin = _simulation(
        tmp_path, [_demand()], capacity_policy="queue"
    )
    events = []
    plugin.add_event_listener("test", events.append)

    simulation.update_time_step()
    assert plugin.admitted_population() == 2
    assert plugin.waiting_population() == 2

    simulation.update_time_step()
    assert plugin.admitted_population() == 2
    assert plugin.waiting_population() == 0
    delayed = [
        event
        for event in events
        if event["event_type"] == "admitted"
        and event["simulation_step"] == 1
    ]
    assert sum(event["population"] for event in delayed) == 2


def test_fallback_splits_a_cohort_across_compatible_hospitals(tmp_path):
    simulation, plugin = _simulation(
        tmp_path,
        [_demand(total=3, sus=3)],
        capacity_policy="queue",
        allow_hospital_change=True,
    )
    events = []
    plugin.add_event_listener("test", events.append)
    simulation.update_time_step()

    assert plugin.hospital_nodes["H1"].get_population_size() == 1
    assert plugin.hospital_nodes["H2"].get_population_size() == 2
    assert plugin.waiting_population() == 0
    assert sum(
        event["population"]
        for event in events
        if event["event_type"] == "rerouted"
    ) == 2


def test_no_hospital_change_keeps_excess_at_home(tmp_path):
    simulation, plugin = _simulation(
        tmp_path,
        [_demand(total=3, sus=3)],
        capacity_policy="queue",
        allow_hospital_change=False,
    )
    simulation.update_time_step()
    assert plugin.hospital_nodes["H1"].get_population_size() == 1
    assert plugin.hospital_nodes["H2"].get_population_size() == 0
    assert plugin.waiting_population() == 2


def test_seeded_distributions_preserve_exact_totals(tmp_path):
    simulation, plugin = _simulation(
        tmp_path,
        [_demand(total=19, sus=7, start=0, end=2)],
        cycles=3,
    )
    scheduled = [
        demand
        for demands in plugin.demands_by_step.values()
        for demand in demands
    ]
    assert sum(item.quantity for item in scheduled) == 19
    assert sum(item.quantity for item in scheduled if item.payer == "sus") == 7
    assert sum(
        item.quantity for item in scheduled if item.payer == "private"
    ) == 12
    assert sorted(plugin.demands_by_step) == [0, 1, 2]


def test_same_seed_produces_same_normalized_schedule(tmp_path):
    _, first = _simulation(
        tmp_path,
        [_demand(total=19, sus=7, start=0, end=2)],
        cycles=3,
    )
    first_schedule = first.demands_by_step.copy()
    _, second = _simulation(
        tmp_path,
        [_demand(total=19, sus=7, start=0, end=2)],
        cycles=3,
    )
    assert first_schedule == second.demands_by_step


def test_different_seed_changes_timing_but_not_totals(tmp_path):
    _, first = _simulation(
        tmp_path,
        [_demand(total=40, sus=16, start=0, end=2)],
        cycles=3,
        seed=0,
        population=50,
    )
    _, second = _simulation(
        tmp_path,
        [_demand(total=40, sus=16, start=0, end=2)],
        cycles=3,
        seed=1,
        population=50,
    )
    assert first.demands_by_step != second.demands_by_step
    for plugin in (first, second):
        scheduled = [
            demand
            for demands in plugin.demands_by_step.values()
            for demand in demands
        ]
        assert sum(item.quantity for item in scheduled) == 40
        assert sum(
            item.quantity for item in scheduled if item.payer == "sus"
        ) == 16


def test_multiple_demands_do_not_reselect_waiting_people(tmp_path):
    simulation, plugin = _simulation(
        tmp_path,
        [
            _demand(total=4, sus=2),
            _demand(total=5, sus=3),
        ],
    )
    events = []
    plugin.add_event_listener("test", events.append)
    simulation.update_time_step()
    assert sum(
        event["population"]
        for event in events
        if event["event_type"] == "admitted"
    ) == 9
    assert plugin.admitted_population() == 9


def test_disabled_preferred_hospital_uses_enabled_fallback(tmp_path):
    simulation, plugin = _simulation(
        tmp_path,
        [_demand(total=2, sus=2)],
        capacity_policy="queue",
        allow_hospital_change=True,
    )
    plugin.hospital_nodes["H1"].disable("test")
    simulation.update_time_step()
    assert plugin.hospital_nodes["H1"].get_population_size() == 0
    assert plugin.hospital_nodes["H2"].get_population_size() == 2


@pytest.mark.parametrize(
    "row, message",
    [
        (
            {
                "hospital": "H1",
                "region": "Origin",
                "longitude": 1,
                "latitude": 0,
                "specialty": "Psychiatry",
                "bed_type": "Other",
                "total_beds": 1,
                "sus_beds": 2,
            },
            "exceeds total_beds",
        ),
    ],
)
def test_invalid_capacity_fails_before_simulation(tmp_path, row, message):
    with pytest.raises(ValueError, match=message):
        _simulation(tmp_path, [_demand(total=1, sus=1)], capacity_rows=[row])


def test_invalid_demand_fails_before_simulation(tmp_path):
    with pytest.raises(ValueError, match="sus_admissions"):
        _simulation(tmp_path, [_demand(total=1, sus=2)])
    with pytest.raises(ValueError, match="los_max_steps"):
        _simulation(
            tmp_path,
            [_demand(total=1, sus=1, los_min=3, los_max=1)],
        )
    with pytest.raises(ValueError, match="never-admitted"):
        _simulation(
            tmp_path,
            [_demand(total=31, sus=15)],
            population=30,
        )


def test_unknown_preferred_hospital_fails_before_simulation(tmp_path):
    with pytest.raises(ValueError, match="Preferred hospital"):
        _simulation(
            tmp_path, [_demand(total=1, sus=1, hospital="Missing")]
        )


def test_historical_cid_adapter_accounts_for_all_915_cases(tmp_path):
    FixedRandom(random_seed=0, numpy_seed=0)
    graph = EnvironmentGraph()
    characteristics = CharacteristicsFactory()
    characteristics.add_sampled_characteristic("age", ["adult"])
    factory = BlobFactory(characteristics)
    regions = [
        "Independência",
        "Jardim Botânico",
        "Santana",
    ]
    capacity_rows = []
    for index, region_name in enumerate(regions):
        region = EnvRegion(region_name, [float(index), 0.0])
        graph.region_list.append(region)
        graph.region_dict[region.name] = region
        graph.region_id_dict[region.id] = region
        home = EnvNode("home", "home")
        home.long_lat = [float(index), 0.0]
        home.add_blob(factory.generate_blob_rand(region.id, home.id, 1000))
        hospital = EnvNode("hospital", f"hospital_{index}")
        hospital.long_lat = [float(index), 0.1]
        hospital.add_attribute("hospital_name", f"H{index}")
        _register(graph, region, home)
        _register(graph, region, hospital)
        capacity_rows.append(
            {
                "hospital": f"H{index}",
                "region": region_name,
                "longitude": index,
                "latitude": 0.1,
                "specialty": "Compatibility Only",
                "bed_type": "Fixture",
                "total_beds": 1000,
                "sus_beds": 1000,
            }
        )
    capacity_file = tmp_path / "capacity.csv"
    _write_capacity(capacity_file, capacity_rows)
    fixture = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "data_input"
            / "inpatient_care"
            / "legacy_cid_source.fixture.json"
        ).read_text(encoding="utf8")
    )
    simulation = LodusSimulation(graph)
    simulation.set_total_cycles(12)
    simulation.set_cycle_length(1)
    simulation.experiment_config = {
        "inpatient_care_plugin": {
            "capacity_file": str(capacity_file),
            "capacity_policy": "overflow",
            "allow_hospital_change": True,
            "demand_sources": [fixture],
        }
    }
    plugin = InpatientCarePlugin()
    simulation.load_plugin(plugin)
    scheduled = [
        demand
        for demands in plugin.demands_by_step.values()
        for demand in demands
    ]
    assert sum(item.quantity for item in scheduled) == 915
    assert {item.origin_region for item in scheduled} == set(regions)


def test_unknown_cid_mapping_fails(tmp_path):
    counts = tmp_path / "counts.csv"
    counts.write_text(
        "origin_region,request_step,cid,quantity,sus_quantity\n"
        "Origin,0,Z999,1,1\n",
        encoding="utf8",
    )
    mapping = tmp_path / "mapping.csv"
    mapping.write_text(
        "cid_pattern,specialty,bed_type\nF20*,Psychiatry,Other\n",
        encoding="utf8",
    )
    simulation, plugin = _simulation(tmp_path, [_demand(total=0, sus=0)])
    simulation.experiment_config["inpatient_care_plugin"][
        "demand_sources"
    ] = [
        {
            "adapter": "cid_counts",
            "file": str(counts),
            "cid_mapping_file": str(mapping),
            "one_based_steps": False,
        }
    ]
    replacement = InpatientCarePlugin()
    with pytest.raises(ValueError, match="No CID mapping"):
        replacement.load_plugin(simulation)


def test_logger_writes_specialized_csvs(tmp_path):
    simulation, plugin = _simulation(
        tmp_path, [_demand()], capacity_policy="queue"
    )
    simulation.experiment_name = str(tmp_path / "run")
    logger = InpatientCareLogger(export_png=False)
    simulation.load_plugin(logger)
    simulation.setup_logging()
    for _ in range(3):
        simulation.update_time_step()
        simulation.log_simulation_step()
    simulation.stop_logging()

    data_path = tmp_path / "run" / "data_frames"
    expected = {
        "inpatient_events.csv",
        "inpatient_step.csv",
        "inpatient_bed_step.csv",
        "inpatient_region_step.csv",
        "inpatient_locations.csv",
    }
    assert expected == {path.name for path in data_path.glob("*.csv")}
    events = pd.read_csv(
        data_path / "inpatient_events.csv",
        sep=";",
        encoding="utf-8-sig",
    )
    assert {
        "demanded",
        "queued",
        "admitted",
        "discharged",
    }.issubset(set(events["Event"]))


def test_imported_capacity_and_environment_totals():
    root = Path(__file__).resolve().parents[1]
    capacity_path = (
        root / "data_input" / "inpatient_care" / "inpatient_capacity.csv"
    )
    with capacity_path.open(encoding="utf8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 253
    assert len({row["hospital"] for row in rows}) == 28
    assert len({row["region"] for row in rows}) == 22
    assert sum(int(row["total_beds"]) for row in rows) == 7529
    assert sum(int(row["sus_beds"]) for row in rows) == 4689

    overlay = json.loads(
        (
            root
            / "data_input"
            / "inpatient_care"
            / "Environment-Hospitals-POA.json"
        ).read_text(encoding="utf8")
    )
    hospitals = [
        node
        for region in overlay["regions"]
        for node in region["points_of_interest"]
    ]
    assert len(hospitals) == 28
    assert len(
        {node["attributes"]["hospital_name"] for node in hospitals}
    ) == 28


@pytest.mark.parametrize(
    "filename,total,sus",
    [
        ("reference_demand.json", 550, 350),
        ("high_demand.json", 2790, 1740),
        ("two_facility_demand.json", 2640, 1590),
    ],
)
def test_reference_study_demand_fixture_totals(filename, total, sus):
    path = (
        Path(__file__).resolve().parents[1]
        / "data_input"
        / "inpatient_care"
        / filename
    )
    records = json.loads(path.read_text(encoding="utf8"))["records"]
    assert sum(row["total_admissions"] for row in records) == total
    assert sum(row["sus_admissions"] for row in records) == sus
