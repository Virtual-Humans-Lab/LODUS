import environment
from population import PopTemplate
import numpy as np
import csv
import pandas as pd
from uuid import uuid4


class HospitalPlugin(environment.TimeActionPlugin):
    '''
    This Plugin implements ..... 

    '''

    def __init__(self, env_graph: environment.EnvironmentGraph, config_file_path, simulation_steps: int, day_duration: int):

        super().__init__()

        # Global configuration
        self.df = pd.read_csv(config_file_path, encoding='ISO-8859-1')
        
        # Set the time/frame variables
        self.day_duration = day_duration
        self.simulation_steps = simulation_steps
        self.hour = 0
        self.time = 0
        self.current_day = 0

        #, default_beta = 0.25, default_gamma = 0.08
        self.graph = env_graph

        self.set_pair('patient_call', self.patient_call)
        self.set_pair('generate_patient_data', self.generate_patient_data)
        self.graph.base_actions.add('generate_patient_data')

        # Sets a traceable properties for all blobs in the simulation
        self.graph.add_blobs_traceable_property("patient_id", 0)
        self.graph.add_blobs_traceable_property("treatment", 0)
        self.graph.add_blobs_traceable_property("CID", 0)
        self.graph.add_blobs_traceable_property("description", '')
        self.graph.add_blobs_traceable_property("time", -1)

        # print(self.df.head())
        # self.current_id = 0
        # JSON file containing the configuration of the Hospital Plugin
        # with open(config_file_path, newline='', encoding='ISO-8859-1') as csvfile:
        #     count_by_region = csv.reader(csvfile, delimiter=',', quotechar='|')
        #     next(count_by_region)
        #     for row in count_by_region:
        #         region, month, cid, count = row

        #         self.region_count[region+'|'+month] = count
        
    def update_time_step(self, hour, time):
        # Updates time step data
        self.hour = hour
        self.time = time
        self.day = (time // self.day_duration) 
        # print(self.time, self.hour, self.day)


    def patient_call(self, values, hour, time):

        assert 'region' in values and isinstance(values['region'], str), "No 'region' value defined"
        assert 'node' in values and isinstance(values['node'], str), "No 'node' value defined"
        #assert ('frames' in values or 'cycle_length' in values)
        
        # print("\nTimeAction de um Plugin", hour, time, values)
        
        # Gets the target region and node
        region = self.graph.get_region_by_name(values['region'])
        node = region.get_node_by_name(values['node'])
        
        get_action_values = {}
        get_action_type = 'gather_population'
        get_action_values['region'] = region.name
        get_action_values['node'] = node.name
        get_action_values['different_node_name'] = True

        pop_template = PopTemplate()
        pop_template.set_traceable_property('patient_id', 0)
        get_action_values['population_template'] = pop_template
        
        num_cases_by_region = self.df.loc[(self.df['REGIAO_HOSPITAL'] == region.name) & (self.df['MES_INTER'] == time+1)]
        # num_cases_by_region = self.region_count[values['region']]]
        # num_cases_by_region = int(self.region_count[values['region']])
        quantity_by_frame = num_cases_by_region['QUANTIDADE'].sum()
        # print(time, region.name, quantity_by_frame)
        # # get_action_values['quantity'] = quantity_by_frame
        get_action_values['quantity'] = quantity_by_frame
        get_action = environment.TimeAction(_type = get_action_type, _values = get_action_values)
        
        return [get_action]
    
    
    def generate_patient_data(self, values, hour, time):

        assert 'region' in values and isinstance(values['region'], str), "No 'region' value defined"
        assert 'node' in values and isinstance(values['node'], str), "No 'node' value defined"
        #assert ('frames' in values or 'cycle_length' in values)
        
        # Gets the target region and node
        region = self.graph.get_region_by_name(values['region'])
        node = region.get_node_by_name(values['node'])

        pt_first_rec = PopTemplate()
        pt_first_rec.set_traceable_property("patient_id", 0)

        pt_return = PopTemplate()
        pt_return.set_traceable_property("patient_id", lambda x: x != 0)
        # pt.set_traceable_property("days_since_last_consultaiton", lambda n: n > 7)

        # first_rec_pop_size = node.get_population_size(pt_first_rec)
        g_pop = []

        num_cases_by_region = self.df.loc[(self.df['REGIAO_HOSPITAL'] == region.name) & (self.df['MES_INTER'] == time+1)]
  
        for _, row in num_cases_by_region.iterrows():
            for i in range(0, row['QUANTIDADE']):
                grabbed_pop = node.grab_population(1, pt_first_rec)
                g_pop.extend(grabbed_pop)

                for g_blob in grabbed_pop:
                    g_blob.traceable_properties['patient_id'] = str(uuid4())
                    g_blob.traceable_properties['treatment'] = 1
                    g_blob.traceable_properties['CID'] = row['DIAG_PRINC']
                    g_blob.traceable_properties['description'] = self._treatment_text_generator()
                    g_blob.traceable_properties['time'] = time



        # for i in range(0, first_rec_pop_size):
        #     grabbed_pop = node.grab_population(1, pt_first_rec)
        #     g_pop.extend(grabbed_pop)

        #     for g_blob in grabbed_pop:
        #         g_blob.traceable_properties['patient_id'] = str(uuid4())
        #         g_blob.traceable_properties['treatment'] = 1
        #         g_blob.traceable_properties['CID'] = 'J11'
        #         g_blob.traceable_properties['description'] = self._treatment_text_generator()
        #         g_blob.traceable_properties['time'] = time

        node.add_blobs(g_pop)

        # for blob in node.contained_blobs:
        #     print(blob.verbose_str())


    def _treatment_text_generator(num_visits):
        generated_text = '** RESIDÊNCIA MULTIPROFISSIONAL - CARDIOLOGIA - R2 ENFERMAGEM **-> ADMISSÃO UTI ADULTO ***'
        return generated_text