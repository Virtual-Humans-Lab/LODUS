import csv
from types import SimpleNamespace

import pytest

from plugins.time_actions.popular_times_plugin import PopularTimesPlugin
from data_pop_times_generator import generate_popular_times


def _write_csv(path, rows):
    with path.open("w", encoding="utf8", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(rows)


def _simulation(data_path, gather=None):
    actions = {}
    if gather is not None:
        actions["gather_population"] = gather
    controller = SimpleNamespace(action_type_to_function=actions)
    simulation = SimpleNamespace(
        env_graph=object(),
        experiment_config={
            "popular_times_plugin": {"data_path": str(data_path)}
        },
        cycle_lenght=24,
        routine_controller=controller,
    )
    simulation.add_action_type_to_function = (
        lambda action_type, function, is_base: actions.__setitem__(action_type, function)
    )
    return simulation


def test_quantity_uses_weekday_and_sector_multiplier(tmp_path):
    _write_csv(
        tmp_path / "restaurant.csv",
        [
            ["ciclo", "hora", "quantidade"],
            [0, 12, 100],
            [1, 12, 200],
        ],
    )
    _write_csv(
        tmp_path / "Setores-13Bairros-Dia.csv",
        [["local", "multiplicador"], ["Centro//home_3", 2.0]],
    )
    plugin = PopularTimesPlugin()
    plugin.load_plugin(_simulation(tmp_path))
    plugin._load_csv_for_node_type("restaurant")

    assert plugin.get_quantity_for_hour(0, "restaurant", 12, "Centro", "shop_3") == 20
    assert plugin.get_quantity_for_hour(24, "restaurant", 12, "Centro", "shop_3") == 40


def test_action_delegates_to_gather_population(tmp_path):
    _write_csv(
        tmp_path / "pharmacy.csv",
        [["ciclo", "hora", "quantidade"], [0, 8, 50]],
    )
    _write_csv(
        tmp_path / "Setores-13Bairros-Dia.csv",
        [["local", "multiplicador"], ["Centro//home_2", 1.0]],
    )
    calls = []

    def gather(pop_template, values, cycle_step, sim_step):
        calls.append((pop_template, values, cycle_step, sim_step))
        return ["movement"]

    plugin = PopularTimesPlugin()
    plugin.load_plugin(_simulation(tmp_path, gather))
    result = plugin.popular_times_action(
        "template",
        {"node_type": "pharmacy", "region": "Centro", "node": "pharmacy_2"},
        8,
        0,
    )

    assert result == ["movement"]
    assert calls[0][1] == {
        "region": "Centro",
        "node": "pharmacy_2",
        "quantity": 5,
        "different_node_name": False,
    }


def test_generator_is_reproducible(tmp_path):
    first = generate_popular_times("restaurant", tmp_path / "first", seed=7)
    second = generate_popular_times("restaurant", tmp_path / "second", seed=7)
    assert first.read_text(encoding="utf8") == second.read_text(encoding="utf8")


def test_action_requires_gather_population(tmp_path):
    _write_csv(
        tmp_path / "restaurant.csv",
        [["ciclo", "hora", "quantidade"], [0, 12, 100]],
    )
    _write_csv(
        tmp_path / "Setores-13Bairros-Dia.csv",
        [["local", "multiplicador"], ["Centro//home_1", 1.0]],
    )
    plugin = PopularTimesPlugin()
    plugin.load_plugin(_simulation(tmp_path))

    with pytest.raises(RuntimeError, match="GatherPopulationPlugin"):
        plugin.popular_times_action(
            None,
            {"node_type": "restaurant", "region": "Centro", "node": "shop_1"},
            12,
            0,
        )
