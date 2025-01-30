

import pytest
from core.environment import EnvNode, EnvNodeFactory, EnvNodeTemplate, EnvRegion
from core.population import BlobFactory, BlobTemplate, CharacteristicsFactory, PopulationTemplate
from core.routine import Action, RoutineFactory
from random_inst import FixedRandom

@pytest.fixture(scope="session", autouse=True)
def start_fixedrandom():
    """Initialize FixedRandom to ensure deterministic behavior in tests."""
    FixedRandom()  # Ensure FixedRandom is defined or imported properly.

@pytest.fixture
def default_action() -> Action:
    pop_template = PopulationTemplate()
    values = {"key1": "value1", "key2": "value2"}
    return Action(action_type="TestAction", pop_template=pop_template, values=values)

@pytest.fixture
def env_node_template() -> EnvNodeTemplate:
    template = EnvNodeTemplate(node_type="test_type")
    template.set_long_lat_position(10.0, 20.0)
    template.add_node_attributes("attr1", "value1")
    return template

@pytest.fixture
def blob_factory() -> BlobFactory:
    characteristics_factory = CharacteristicsFactory()
    characteristics_factory.add_sampled_characteristic('age', ['child', 'adult', 'ancient'])
    characteristics_factory.add_sampled_characteristic('economic_profile', ['unemployed', 'worker'])
    characteristics_factory.add_traceable_characteristic('vaccine_level', 0)
    characteristics_factory.add_traceable_characteristic('sir_state', 'susceptible')
    return BlobFactory(characteristics_factory)

@pytest.fixture
def env_region() -> EnvRegion:
    return EnvRegion(region_name="test_region", long_lat=[30.0, 40.0])

@pytest.fixture
def routine_factory() -> RoutineFactory:
    return RoutineFactory()

class TestEnvNodeTemplate:
    
    def test_add_node_attributes(self):
        template = EnvNodeTemplate(node_type="default")
        template.add_node_attributes("key1", "value1")
        assert template.node_attributes["key1"] == "value1"

    def test_add_action_to_routine_template(self, default_action: Action):
        template = EnvNodeTemplate(node_type="default")
        template.add_action_to_routine_template(1, default_action)
        assert template.routine_template.cycle_step_to_action_list[1] == [default_action]


    def test_add_routine_template_invalid_action(self):
        template = EnvNodeTemplate(node_type="default")
        with pytest.raises(ValueError, match="Action must be of type Action"):
            template.add_actions_to_routine_template(1, ["invalid_action"]) # type: ignore

    def test_add_routine_template_invalid_cycle_stop(self, default_action: Action):
        template = EnvNodeTemplate(node_type="default")
        with pytest.raises(ValueError, match="cycle_step must be a non-negative integer"):
            template.add_actions_to_routine_template(-1, [default_action])

    def test_add_blob_template(self):
        template = EnvNodeTemplate(node_type="default")
        traceable_characteristics = {"key1": "value1"}
        sampled_characteristics = {"key2": {"subkey": 1}}
        blob_template = BlobTemplate(100, traceable_characteristics, sampled_characteristics)
        template.add_blob_template(blob_template)
        assert len(template.blob_templates) == 1
        assert template.blob_templates[0].population == 100
        assert template.blob_templates[0].traceable_characteristics == traceable_characteristics
        assert template.blob_templates[0].sampled_characteristics == sampled_characteristics

    def test_set_long_lat_position(self):
        template = EnvNodeTemplate(node_type="default")
        template.set_long_lat_position(10.0, 20.0)
        assert template.long_lat == [10.0, 20.0]

    def test_set_long_lat_position_invalid_longitude(self):
        template = EnvNodeTemplate(node_type="default")
        with pytest.raises(ValueError, match="longitude and latitude must be of type int or float"):
            template.set_long_lat_position("invalid", 20.0) # type: ignore

    def test_set_long_lat_position_invalid_latitude(self):
        template = EnvNodeTemplate(node_type="default")
        with pytest.raises(ValueError, match="longitude and latitude must be of type int or float"):
            template.set_long_lat_position(10.0, "invalid") # type: ignore

class TestEnvNodeFactory:
    def test_generate_envnode_default_routine_factory(self, 
                                                      env_node_template: EnvNodeTemplate, 
                                                      blob_factory: BlobFactory, 
                                                      env_region: EnvRegion):
        factory = EnvNodeFactory()
        env_node = factory.generate_envnode(env_node_template, blob_factory, env_region)
        
        assert isinstance(env_node, EnvNode)
        assert env_node.node_type == "test_type"
        assert env_node.long_lat == [10.0, 20.0]
        assert env_node.attributes["attr1"] == "value1"
        assert env_node.routine is not None

    def test_generate_envnode_custom_routine_factory(self,
                                                     env_node_template: EnvNodeTemplate, 
                                                     blob_factory: BlobFactory, 
                                                     env_region: EnvRegion, 
                                                     routine_factory: RoutineFactory):
        factory = EnvNodeFactory()
        env_node = factory.generate_envnode(env_node_template, blob_factory, env_region, routine_factory)
        
        assert isinstance(env_node, EnvNode)
        assert env_node.node_type == "test_type"
        assert env_node.long_lat == [10.0, 20.0]
        assert env_node.attributes["attr1"] == "value1"
        assert env_node.routine is not None

    def test_generate_envnode_with_blob_templates(self, 
                                                  env_node_template: EnvNodeTemplate, 
                                                  blob_factory: BlobFactory, 
                                                  env_region: EnvRegion):
        traceable_characteristics = {"key1": "value1"}
        sampled_characteristics =  {"age": {'child': 30, 'adult': 50, 'ancient': 20} , 
            "economic_profile": {'unemployed': 30, 'worker': 70}}
        blob_template = BlobTemplate(100, traceable_characteristics, sampled_characteristics)
        env_node_template.add_blob_template(blob_template)
    
        factory = EnvNodeFactory()
        env_node = factory.generate_envnode(env_node_template, blob_factory, env_region)
    
        assert len(env_node.contained_blobs) == 1
        assert env_node.contained_blobs[0].get_population_size() == 100
        assert env_node.contained_blobs[0].traceable_characteristics == traceable_characteristics
        assert env_node.contained_blobs[0].sampled_characteristics.characteristics["age"].categories == {'child': 30, 'adult': 50, 'ancient': 20}
        
        assert env_node.contained_blobs[0].sampled_characteristics.characteristics["economic_profile"].categories == {'unemployed': 30, 'worker': 70}

class TestEnvNode:     
    def test_initialization(self):
        node = EnvNode(node_type="test_type")
        assert node.node_type == "test_type"
        assert node.name == "test_type"
        assert node.long_lat == [0.0, 0.0]
        assert node.attributes == {}
        assert node.contained_blobs == []
        assert node.routine is None

    def test_get_unique_name(self):
        node = EnvNode(node_type="test_type")
        node.containing_region_name = "test_region"
        assert node.get_unique_name() == f"test_region//test_type{node.type_id}"

    def test_add_attribute(self):
        node = EnvNode(node_type="test_type")
        node.add_attribute("key", "value")
        assert node.attributes["key"] == "value"

    def test_get_attribute(self):
        node = EnvNode(node_type="test_type")
        node.add_attribute("key", "value")
        assert node.get_attribute("key") == "value"

    def test_set_long_lat_position(self):
        node = EnvNode(node_type="test_type")
        node.set_long_lat_position(10.0, 20.0)
        assert node.long_lat == [10.0, 20.0]

    def test_set_long_lat_position_invalid_longitude(self):
        node = EnvNode(node_type="test_type")
        with pytest.raises(ValueError, match="longitude and latitude must be of type int or float"):
            node.set_long_lat_position("invalid", 20.0) # type: ignore

    def test_set_long_lat_position_invalid_latitude(self):
        node = EnvNode(node_type="test_type")
        with pytest.raises(ValueError, match="longitude and latitude must be of type int or float"):
            node.set_long_lat_position(10.0, "invalid") # type: ignore

    def test_add_blob(self, blob_factory: BlobFactory):
        node = EnvNode(node_type="test_type")
        blob = blob_factory.generate_blob_rand(0, 0, 100)
        node.add_blob(blob)
        assert blob in node.contained_blobs
        assert blob.get_population_size() == 100
        assert node.get_population_size() == 100

    def test_add_blob_invalid_type(self):
        node = EnvNode(node_type="test_type")
        with pytest.raises(ValueError, match="blob must be of type Blob"):
            node.add_blob("invalid_blob") # type: ignore

    def test_add_blob_already_here(self, blob_factory: BlobFactory):
        node = EnvNode(node_type="test_type")
        blob = blob_factory.generate_blob_rand(0, 0, 100)
        node.add_blob(blob)
        assert blob.get_population_size() == 100
        assert node.get_population_size() == 100
        with pytest.raises(ValueError, match="BLOB ALREADY HERE"):
            node.add_blob(blob)

    def test_remove_blob(self, blob_factory: BlobFactory):
        node = EnvNode(node_type="test_type")
        blob = blob_factory.generate_blob_rand(0, 0, 100)
        node.add_blob(blob)
        assert blob.get_population_size() == 100
        assert node.get_population_size() == 100
        node.remove_blob(blob)
        assert blob not in node.contained_blobs
        assert blob.get_population_size() == 100
        assert node.get_population_size() == 0

    def test_remove_blob_invalid_type(self):
        node = EnvNode(node_type="test_type")
        with pytest.raises(ValueError, match="blob must be of type Blob"):
            node.remove_blob("invalid_blob") # type: ignore

    def test_remove_blobs(self, blob_factory: BlobFactory):
        node = EnvNode(node_type="test_type")
        blobs = [blob_factory.generate_blob_rand(0, 0, 100) for _ in range(3)]
        node.add_blobs(blobs)
        assert node.get_population_size() == 300
        node.remove_blobs(blobs)
        assert all(blob not in node.contained_blobs for blob in blobs)
        assert node.get_population_size() == 0

    def test_get_population_size(self, blob_factory: BlobFactory):
        node = EnvNode(node_type="test_type")
        blobs = [blob_factory.generate_blob_rand(0, 0, 100) for _ in range(3)]
        for blob in blobs:
            assert blob.get_population_size() == 100
        node.add_blobs(blobs)
        assert node.get_population_size() == 300

    def test_grab_population(self, blob_factory: BlobFactory):
        node = EnvNode(node_type="test_type")
        blobs = [blob_factory.generate_blob_rand(0, 0, 100) for _ in range(3)]
        for blob in blobs:
            assert blob.get_population_size() == 100
        node.add_blobs(blobs)
        assert node.get_population_size() == 300
        grabbed_blobs = node.grab_population(15)
        assert len(grabbed_blobs) == 3
        assert node.get_population_size() == 285

    def test_change_multiple_blobs_traceable_property(self, blob_factory: BlobFactory):
        node = EnvNode(node_type="test_type")
        blobs = [blob_factory.generate_blob_rand(0, 0, 100) for _ in range(3)]
        node.add_blobs(blobs)
        modified_blobs = node.change_multiple_blobs_traceable_property("vaccine_level", 1, 3)
        assert sum(blob.get_population_size() for blob in node.contained_blobs) == 300
        assert sum(blob.get_population_size() for blob in blobs) == 297
        assert sum(blob.get_population_size() for blob in modified_blobs) == 3

    def test_change_single_blob_traceable_property(self, blob_factory: BlobFactory):
        node = EnvNode(node_type="test_type")
        blob = blob_factory.generate_blob_rand(0, 0, 100)
        node.add_blob(blob)
        modified_blob = node.change_single_blob_traceable_property(blob, "vaccine_level", 1, 1)
        assert blob.get_traceable_characteristic("vaccine_level") == 0
        assert sum(blob.get_population_size() for blob in node.contained_blobs) == 100
        assert blob.get_population_size()== 99
        assert modified_blob.get_population_size() == 1
