"""Dedicated runner for capacity-constrained shelter simulations."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time

from core.population import PopulationTemplate
from plugins.loggers.blob_count_logger import (
    BlobCountLogger,
    BlobCountRecordKey,
)
from plugins.loggers.movement_displacement_logger import (
    MovementDisplacementLogger,
)
from plugins.loggers.population_count_logger import (
    PopulationCountLogger,
    PopulationCountRecordKey,
)
from plugins.loggers.shelter_logger import ShelterLogger
from plugins.time_actions.gather_population_plugin import (
    GatherPopulationPlugin,
)
from plugins.time_actions.levy_walk_plugin import LevyWalkPlugin
from plugins.time_actions.move_population_plugin import MovePopulationPlugin
from plugins.time_actions.send_population_back_plugin import (
    SendPopulationBackPlugin,
)
from plugins.time_actions.shelter_plugin import ShelterPlugin
from util.data_parse import generate_lodus_simulation, load_experiment_config
from util.random_instance import FixedRandom
from util.resource_usage import get_peak_memory_kib


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a focused LODUS shelter simulation."
    )
    parser.add_argument(
        "--e", required=True, help="Experiment path relative to experiments/"
    )
    parser.add_argument("--n", help="Output run name")
    parser.add_argument(
        "--seed", type=int,
        help="Override simulation_parameters.random_seed",
    )
    parser.add_argument(
        "--no-shelter-png", action="store_true",
        help="Generate shelter HTML visualizations without PNG export",
    )
    parser.add_argument(
        "--overrides-json",
        help="Research-only JSON object or path merged into the experiment",
    )
    return parser.parse_args()


def configured_seed(experiment: str, override: int | None) -> int:
    if override is not None:
        return override
    config = load_experiment_config(experiment)
    return int(
        config.get("simulation_parameters", {}).get(
            "random_seed", config.get("random_seed", 0)
        )
    )


def git_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).parent,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def deep_merge(target: dict, source: dict):
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_merge(target[key], value)
        else:
            target[key] = value


def load_overrides(value: str | None) -> dict:
    if not value:
        return {}
    stripped = value.lstrip()
    if stripped.startswith("{"):
        loaded = json.loads(value)
    else:
        candidate = Path(value)
        loaded = json.loads(
            candidate.read_text(encoding="utf-8")
            if candidate.is_file()
            else value
        )
    if not isinstance(loaded, dict):
        raise ValueError("--overrides-json must contain a JSON object")
    return loaded


def configure_population_logger() -> PopulationCountLogger:
    logger = PopulationCountLogger()
    logger.data_to_record = {
        PopulationCountRecordKey.POPULATION_COUNT_GLOBAL,
        PopulationCountRecordKey.POPULATION_COUNT_REGION,
    }
    templates = {
        "Safe": PopulationTemplate(
            traceable_characteristics={"flooding_status": "safe"}
        ),
        "In Danger": PopulationTemplate(
            traceable_characteristics={"flooding_status": "in_danger"}
        ),
        "Sheltered": PopulationTemplate(
            traceable_characteristics={"flooding_status": "sheltered"}
        ),
    }
    logger.global_custom_templates.update(templates)
    logger.region_custom_templates.update(templates)
    logger.pop_template = PopulationTemplate()
    return logger


def run(args) -> Path:
    seed = configured_seed(args.e, args.seed)
    FixedRandom(random_seed=seed, numpy_seed=seed)
    started_at = datetime.now(timezone.utc)
    simulation = generate_lodus_simulation(args.e)
    overrides = load_overrides(getattr(args, "overrides_json", None))
    deep_merge(simulation.experiment_config, overrides)
    parameters = simulation.experiment_config.get("simulation_parameters", {})
    simulation.set_total_cycles(
        int(parameters.get("total_cycles", simulation.time_status.total_cycles))
    )
    simulation.set_cycle_length(
        int(parameters.get("cycle_length", simulation.time_status.cycle_length))
    )
    simulation.experiment_config.setdefault(
        "simulation_parameters", {}
    )["random_seed"] = seed
    simulation.experiment_name = (
        args.n
        if args.n
        else f"{Path(args.e).name}-seed{seed}"
    )

    action_plugins = [
        MovePopulationPlugin(),
        GatherPopulationPlugin(),
        LevyWalkPlugin(),
        ShelterPlugin(),
    ]
    if "send_population_back_plugin" in simulation.experiment_config:
        action_plugins.insert(3, SendPopulationBackPlugin())
    for plugin in action_plugins:
        simulation.load_plugin(plugin)

    population_logger = configure_population_logger()
    blob_logger = BlobCountLogger()
    blob_logger.data_to_record = {BlobCountRecordKey.BLOB_COUNT_GLOBAL}
    loggers = [
        population_logger,
        blob_logger,
        MovementDisplacementLogger(),
        ShelterLogger(export_png=not args.no_shelter_png),
    ]
    for logger in loggers:
        simulation.load_plugin(logger)

    simulation.setup_logging()
    started = time.perf_counter()
    while not simulation.time_status.is_final_step:
        simulation.update_time_step()
        simulation.log_simulation_step()
    runtime = time.perf_counter() - started
    simulation.stop_logging()
    finished_at = datetime.now(timezone.utc)

    output_path = Path("output_logs") / simulation.experiment_name
    output_path.mkdir(parents=True, exist_ok=True)
    shelter = simulation.get_first_plugin(ShelterPlugin)
    summary = {
        "experiment": args.e,
        "run_name": simulation.experiment_name,
        "seed": seed,
        "cycles": simulation.time_status.total_cycles,
        "cycle_length": simulation.time_status.cycle_length,
        "simulation_steps": simulation.time_status.simulation_step + 1,
        "regions": len(simulation.env_graph.region_list),
        "nodes": len(simulation.env_graph.node_list),
        "shelters": len(shelter.shelters),
        "mapped_exposure": sum(shelter.exposure_by_region.values()),
        "shelter_capacity": sum(
            int(node.get_attribute("capacity")) for node in shelter.shelters
        ),
        "sheltered_final": simulation.env_graph.get_population_size(
            shelter.sheltered_template
        ),
        "unresolved_final": simulation.env_graph.get_population_size(
            shelter.in_danger_template
        ),
        "runtime_seconds": runtime,
        "peak_memory_kib": get_peak_memory_kib(),
    }
    output_text = "\n".join(
        f"{key}: {value}" for key, value in summary.items()
    ) + "\n"
    (output_path / "output.txt").write_text(output_text, encoding="utf-8")
    metadata = {
        "status": "complete",
        **summary,
        "numpy_seed": seed,
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": finished_at.isoformat(),
        "commit_sha": git_commit(),
        "input_files": simulation.experiment_config.get(
            "envgraph_inputs_files", {}
        ),
        "simulation_parameters": {
            "total_cycles": simulation.time_status.total_cycles,
            "cycle_length": simulation.time_status.cycle_length,
            "random_seed": seed,
        },
        "resolved_config": simulation.experiment_config,
    }
    (output_path / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(output_text, end="")
    return output_path


def main():
    run(parse_args())


if __name__ == "__main__":
    main()
