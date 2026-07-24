import json
from pathlib import Path
from warnings import deprecated
from core.environment import EnvironmentGraph, EnvRegionTemplate, EnvNodeTemplate
from core.population import BlobFactory, BlobTemplate, CharacteristicsFactory, PopulationTemplate
from core.routine import Action, GlobalAction, GlobalActionExecutionScope
from core.simulator import LodusSimulation

def generate_lodus_simulation(input_path: str):
    """Generate a LodusSimulation object from the given input path"""
    env_graph = EnvironmentGraph()
    simulation = LodusSimulation(env_graph)

    experiment_path = Path(__file__).parent.parent / "experiments"
    data_path =  Path(__file__).parent.parent / "data_input"

    experiment_config = load_json(experiment_path / f"{input_path}.json")
    input_files = experiment_config["envgraph_inputs_files"]

    simulation.experiment_config = experiment_config

    if "simulation_parameters" in experiment_config:
        sim_params = experiment_config["simulation_parameters"]
        simulation.set_total_cycles(sim_params.get("total_cycles", simulation.time_status.total_cycles))
        simulation.set_cycle_length(sim_params.get("cycle_length", simulation.time_status.cycle_length))

    if "environment_file" not in input_files:
        raise ValueError("Input JSON must contain 'environment_file' in 'envgraph_inputs_files'")

    env_json = load_json_inputs(
        data_path, input_files["environment_file"], concatenate_keys={"regions"}
    )
    pop_json = load_json_inputs(data_path, input_files["population_file"])
    if "routine_file" in input_files:
        rot_json = load_json(data_path / input_files["routine_file"])
    else:
        rot_json = None

    sampled_props_key = ("sampled_characteristics_categories"
                         if "sampled_characteristics_categories" in pop_json
                         else "sampled_characteristics_bins")

    population_template = {
        "traceable_properties": pop_json.get("default_traceable_characteristics", {}),
        "sampled_properties": pop_json.get(sampled_props_key, {})
    }
    
    characteristics_factory = CharacteristicsFactory()
    # Default values for traceable properties
    if 'traceable_properties' in population_template:
        tp = population_template['traceable_properties']
        for k in tp:
            characteristics_factory.add_traceable_characteristic(k, tp[k])

    # Default values for sampled properties
    if 'sampled_properties' in population_template:
        sp = population_template['sampled_properties']
        for k in sp:
            characteristics_factory.add_sampled_characteristic(k, sp[k])

    blob_factory = BlobFactory(characteristics_factory)
    simulation.original_block_template = characteristics_factory

    for reg_dict in env_json['regions']:
        create_region(env_graph, reg_dict, pop_json, rot_json, blob_factory)

    env_graph.set_spawning_nodes()
    env_graph.set_original_populations()

    add_initial_global_actions(simulation, rot_json)

    return simulation

def load_json(file_path):
    """Load a json file from the given path"""
    with open(file_path, 'r', encoding='utf8') as file:
        return json.load(file)


def load_json_inputs(data_path: Path, filenames, concatenate_keys=None):
    """Load and merge one or more JSON input files.

    ``filenames`` may be a single path string or a list of path strings. Object
    values are merged recursively in the supplied order, so later files
    override earlier scalar and list values. Lists whose keys are included in
    ``concatenate_keys`` are instead appended.
    """
    if isinstance(filenames, (str, Path)):
        filenames = [filenames]
    elif not isinstance(filenames, list) or not all(
        isinstance(filename, (str, Path)) for filename in filenames
    ):
        raise TypeError("JSON input must be a path string or a list of path strings")

    if not filenames:
        raise ValueError("JSON input file list cannot be empty")

    merged = {}
    for filename in filenames:
        loaded = load_input_json(data_path, filename)
        if not isinstance(loaded, dict):
            raise ValueError(f"JSON input must contain an object: {filename}")
        _merge_json_objects(merged, loaded, concatenate_keys or set())
    return merged


def _merge_json_objects(target, source, concatenate_keys):
    """Recursively merge a loaded JSON object into another object."""
    for key, value in source.items():
        if key in concatenate_keys and key in target:
            if not isinstance(target[key], list) or not isinstance(value, list):
                raise ValueError(f"JSON field '{key}' must be a list")
            if key == "regions":
                _merge_regions(target[key], value)
            else:
                target[key].extend(value)
        elif key in target and isinstance(target[key], dict) and isinstance(value, dict):
            _merge_json_objects(target[key], value, concatenate_keys)
        else:
            target[key] = value


def _merge_regions(target_regions, source_regions):
    """Merge regions by name, combining POIs from repeated regions."""
    regions_by_name = {}
    for region in target_regions:
        if not isinstance(region, dict) or "name" not in region:
            raise ValueError("Each region must be an object with a 'name' field")
        regions_by_name[region["name"]] = region

    for region in source_regions:
        if not isinstance(region, dict) or "name" not in region:
            raise ValueError("Each region must be an object with a 'name' field")

        existing = regions_by_name.get(region["name"])
        if existing is None:
            target_regions.append(region)
            regions_by_name[region["name"]] = region
            continue

        for key, value in region.items():
            if key == "points_of_interest" and key in existing:
                if not isinstance(existing[key], list) or not isinstance(value, list):
                    raise ValueError(
                        "Region field 'points_of_interest' must be a list"
                    )
                existing[key].extend(value)
            elif (
                key in existing
                and isinstance(existing[key], dict)
                and isinstance(value, dict)
            ):
                _merge_json_objects(existing[key], value, set())
            else:
                existing[key] = value


def load_input_json(data_path: Path, filename):
    """Load a JSON input file, with fallback to data_gwide_experiments."""
    file_path = data_path / filename
    if not file_path.exists():
        alternate_path = data_path / "data_gwide_experiments" / filename
        if alternate_path.exists():
            file_path = alternate_path
        else:
            raise FileNotFoundError(f"Input file not found: {filename}")
    return load_json(file_path)

def create_region(env_graph: EnvironmentGraph, 
                  region_description: dict, 
                  population_json: dict, 
                  routines_json: dict, 
                  blob_factory: BlobFactory):
    """Create a region from the given description and add it to the environment graph"""
    region_name = region_description['name']
    region_position = region_description['lng_lat']
    region_template = EnvRegionTemplate(region_name, region_position)
    for poi_dict in region_description['points_of_interest']:
        node_template = create_node_template(poi_dict, region_name, population_json, routines_json)
        region_template.add_envnode_template(node_template)

    env_graph.add_region(region_template, blob_factory)

def create_node_template(node_description: dict, 
                         region_name:str, 
                         population_json: dict, 
                         routines_json: dict):
    """ Create a node template from the given description"""
    node_type = node_description["poi_type"]
    node_unique_name = node_description["unique_name"]
    node_template = EnvNodeTemplate(node_type, node_unique_name)
    node_template.long_lat = node_description["lng_lat"]
    node_template.node_attributes = node_description.get("attributes", {})

    if "characteristics" in node_description:
        for a, b in node_description["characteristics"].items():
            node_template.add_node_attributes(a, b)

    poi_unique_name = f"{region_name}//{node_unique_name}"
    add_initial_populations(node_template, poi_unique_name, population_json)
    add_initial_local_routine(node_template, poi_unique_name, routines_json)

    return node_template

def add_initial_populations(node_template: EnvNodeTemplate, poi_unique_name: str, population_json):
    if poi_unique_name in population_json["initial_population"]:
        for ip in population_json["initial_population"][poi_unique_name]:
            blob_template = BlobTemplate(
                population=ip["total_population"],
                traceable_characteristics=ip['traceable_characteristics'],
                sampled_characteristics=ip['sampled_characteristics']
            )
            node_template.add_blob_template(blob_template)


def parse_envnode_routines(poi_complete_name: str, routine_json) -> list[tuple[int, Action]]:
    routines = []
    if routine_json is not None and poi_complete_name in routine_json["routines"]:
        for rt in routine_json["routines"][poi_complete_name]:
            pt = PopulationTemplate(
                sampled_characteristics=rt["action"]['population_template']["sampled_characteristics"],
                traceable_characteristics=rt["action"]['population_template']["traceable_characteristics"]
            )
            action = Action(
                action_type=rt["action"]['type'],
                values=rt["action"]['values'],
                pop_template=pt
            )
            routines.append((rt["cycle_step"], action))
    return routines


def parse_local_routines(routine_json) -> list[tuple[int, str, Action]]:
    routines:list[tuple[int, str, Action]] = []
    if routine_json is not None and "routines" in routine_json:
        for poi_complete_name in routine_json["routines"]:
            for rt in routine_json["routines"][poi_complete_name]:
                if "population_template" not in rt["action"]:
                    pt = PopulationTemplate(sampled_characteristics={}, traceable_characteristics={})
                else:
                    pt = PopulationTemplate(
                        sampled_characteristics=rt["action"]['population_template'].get("sampled_characteristics", {}),
                        traceable_characteristics=rt["action"]['population_template'].get("traceable_characteristics", {})
                    )
                action = Action(
                    action_type=rt["action"]['type'],
                    values=rt["action"].get('values', {}),
                    pop_template=pt
                )
                routines.append((rt["cycle_step"], poi_complete_name, action))
    return routines

def add_initial_local_routine(node_template: EnvNodeTemplate, poi_unique_name: str, routine_json):
    local_routines = parse_envnode_routines(poi_unique_name, routine_json)
    for lr in local_routines:
        node_template.add_action_to_routine_template(lr[0], lr[1])

def parse_global_routines(routines_json) -> list[GlobalAction]:
    global_actions:list[GlobalAction] = []

    if routines_json is not None and 'global_routine' in routines_json:
        for rga in routines_json['global_routine']:
            action_type = rga['action']['type']
            if 'population_template' not in rga['action']:
                pt = PopulationTemplate(sampled_characteristics={}, traceable_characteristics={})
            else:
                pt = PopulationTemplate(
                    sampled_characteristics=rga["action"]['population_template'].get("sampled_characteristics", {}),
                    traceable_characteristics=rga["action"]['population_template'].get("traceable_characteristics", {})
                )
            values = rga['action'].get('values', {})
            cycle_step = rga['cycle_step'] if isinstance(rga['cycle_step'], list) else int(rga['cycle_step'])
            raw_execution_scope = rga.get(
                'execution_scope', GlobalActionExecutionScope.PER_NODE.value
            )
            try:
                execution_scope = GlobalActionExecutionScope(raw_execution_scope)
            except ValueError as error:
                valid_scopes = ", ".join(
                    scope.value for scope in GlobalActionExecutionScope
                )
                raise ValueError(
                    f"Invalid global routine execution_scope "
                    f"'{raw_execution_scope}'. Expected one of: {valid_scopes}"
                ) from error
            
            global_actions.append(GlobalAction(
                action_type=action_type,
                population_template=pt,
                values=values,
                cycle_step_definition=cycle_step,
                execution_scope=execution_scope,
            ))
    return global_actions

def add_initial_global_actions(simulation: LodusSimulation, routines_json):
    """Load global actions from the routines JSON and add them to the simulation"""
    global_actions = parse_global_routines(routines_json)

    for ga in global_actions:
        simulation.add_global_action(ga)

@deprecated("Use parse_global_routines instead")
def parse_routines(data:dict):
    return
    _global_actions = []
    _actions = []
    # Global Routines
    for _ga in data.get('global_routine', {}):
        if 'cycle_length' in _ga:
            _global_actions.append((int(_ga['cycle_length']),Action(_ga['type'], _ga['values'])))
        elif 'frames' in _ga:
            _global_actions.append(_ga['frames'], Action(_ga['type'], _ga['values']))
            #env.set_repeating_action(_ga['frames'], TimeAction(_ga['type'], _ga['values']))
        elif 'cycle_step' in _ga:
            pt = PopulationTemplate(
                    sampled_characteristics=_ga["action"]['population_template']["sampled_characteristics"],
                    traceable_characteristics=_ga["action"]['population_template']["traceable_characteristics"])
            if isinstance(_ga['cycle_step'], list):
                _global_actions.append((_ga['cycle_step'], 
                                        Action(action_type=_ga['action']['type'], 
                                                    pop_template=pt,
                                                    values=_ga['action']['values'])))
            else:
                _global_actions.append((int(_ga['cycle_step']), 
                                        Action(action_type=_ga['action']['type'], 
                                                    pop_template=pt,
                                                    values=_ga['action']['values'])))
    # EnvNode Routines
    for _node in data.get('routines', []):
        for _a in data['routines'][_node]:
            pt = PopulationTemplate(
                    sampled_characteristics=_a["action"]['population_template']["sampled_characteristics"],
                    traceable_characteristics=_a["action"]['population_template']["traceable_characteristics"])
            action = Action(action_type=_a["action"]['type'], 
                                values=_a["action"]['values'], 
                                pop_template=pt) 
            _actions.append((_a["cycle_step"], action))

    return _global_actions, _actions


