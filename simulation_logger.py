
from time import sleep
import environment
from population import PopTemplate
import os 
import util
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

import numpy as np
import pandas as pd
pd.options.plotting.backend = "plotly"
from pathlib import Path

import copy
from enum import Enum

class LoggerDefaultRecordKey(Enum):
    BLOB_COUNT_GLOBAL = 0
    BLOB_COUNT_REGION = 1
    BLOB_COUNT_NODE = 2
    ENV_GLOBAL_POPULATION = 3
    ENV_REGION_POPULATION = 4
    ENV_NODE_POPULATION = 5

class SimulationLogger():

    
    def __init__(self, base_filename, graph:environment.EnvironmentGraph, time_cycle=24):
        self.graph = graph
        
        # Sets paths and create folders
        self.base_filename = base_filename
        self.base_path = 'output_logs/' + base_filename + '/'
        self.data_frames_path = self.base_path + "/data_frames/"
        self.figures_path = self.base_path + "/figures/"
        self.html_plots_path = self.base_path + "/html_plots/"
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
        Path(self.data_frames_path).mkdir(parents=True, exist_ok=True)
        Path(self.figures_path).mkdir(parents=True, exist_ok=True)
        Path(self.html_plots_path).mkdir(parents=True, exist_ok=True)
        
        self.data_to_record:set[LoggerDefaultRecordKey] = set()
        self.plugins_to_record: list[environment.TimeActionPlugin] = []
        
        self.time_cycle = time_cycle

        # Data recorded in previous frame
        self.global_prev_frame = {}
        self.regions_prev_frame = {n:{} for n in self.graph.region_dict}
        self.nodes_prev_frame = {n:{} for n in self.graph.node_dict}
        self.nodes_sir_last_frames = {}

        self.logs = {}

        self.foreign_only = True

        self.node_OD_matrix = {}
        self.region_OD_matrix = {}
        self.region_travel = {}
        self.region_no_own_travel = {}
        self.region_time_outside = {}


        self.pop_template = None
        
        # Blob Count Logging
        self.blob_global_count = []
        self.blob_region_count = {r:[] for r in self.graph.region_dict}
        self.blob_node_count = {n:[] for n in self.graph.node_dict}
        
        # Custom Logging
        self.global_custom_templates: dict[str, PopTemplate] = {}
        self.region_custom_templates: dict[str, PopTemplate] = {}
        self.node_custom_templates: dict[str, PopTemplate] = {}
        self.custom_line_plots: dict = {}
        self.global_custom_line_plots: dict = {}
        self.region_custom_line_plots: dict = {}
        self.node_custom_line_plots: dict = {}

    def set_data_to_record(self, _data: LoggerDefaultRecordKey):
        self.data_to_record.add(_data)

    def set_data_list_to_record(self, _types: list[LoggerDefaultRecordKey]):
        self.data_to_record.update(_types)
        
    def set_pluggin_to_record(self, p:environment.TimeActionPlugin):
        assert isinstance(p, environment.TimeActionPlugin), "Argument should be a TimeActionPlugin"
        self.plugins_to_record.append(p)
        p.setup_logger(self)
    
    def add_custom_line_plot(self, _key:str, file, x_label:str, y_label:str, columns:list[str] = None, hours: list[str] = None, level:str = None, filter: list[str] = None):
        self.custom_line_plots[_key] = (file, x_label, y_label, columns, hours, level, filter)    
        
    def add_global_custom_line_plot(self, _key:str, x_label:str, y_label:str, columns:list[str] = None, hours: list[str] =None):
        self.global_custom_line_plots[_key] = (x_label, y_label, columns, hours)
        
    def add_region_custom_line_plot(self, _key:str, x_label:str, y_label:str, columns:list[str] = None, regions:list[str] = None, hours: list[str] =None):
        self.region_custom_line_plots[_key] = (x_label, y_label, columns, regions, hours)
        
    def add_node_custom_line_plot(self, _key:str, x_label:str, y_label:str, columns:list[str] = None, node_types:list[str] = None, hours: list[str] =None):
        self.node_custom_line_plots[_key] = (x_label, y_label, columns, node_types, hours)
        
    def start_logging(self):
        
        # Global data file
        self.global_prev_frame = {k:0 for k in self.global_custom_templates}
        header = "Frame;Hour;Day"
        if self.global_custom_templates: 
            header += ';' + ';'.join(list(self.global_custom_templates.keys()))
            header += ';d' + ';d'.join(list(self.global_custom_templates.keys()))
        self.global_f = open(self.base_path + "global.csv", 'w', encoding='utf8')
        self.global_f.write(header + '\n')
        
        # Regions data file
        for n, r in self.graph.region_dict.items():
            self.regions_prev_frame[n]['__populations'] = [r.get_population_size()] * 2
            for k in self.region_custom_templates:
                self.regions_prev_frame[n][k] = 0
        header = "Frame;Hour;Day;Region;Total;Locals;Outsiders;dTotals;dLocals;dOutsiders"
        if self.region_custom_templates: 
            header += ';' + ';'.join(list(self.region_custom_templates.keys()))
            header += ';d' + ';d'.join(list(self.region_custom_templates.keys()))
        self.regions_f = open(self.base_path +  "regions.csv", 'w', encoding='utf8')
        self.regions_f.write(header + '\n')
        
        # Nodes data file
        for _name, _node in self.graph.node_dict.items():
            self.nodes_prev_frame[_name]['__populations'] = [_node.get_population_size()] * 2
            for k in self.node_custom_templates:
                self.nodes_prev_frame[_name][k] = 0
        header = "Frame;Hour;Day;Node;Total;Locals;Outsiders;dTotals;dLocals;dOutsiders"
        if self.node_custom_templates: 
            header += ';' + ';'.join(list(self.node_custom_templates.keys()))
            header += ';d' + ';d'.join(list(self.node_custom_templates.keys()))
        self.nodes_f = open(self.base_path +  "nodes.csv", 'w', encoding='utf8')
        self.nodes_f.write(header + '\n')
                
        self.diss_f = open(self.base_path + "diss.csv", 'w', encoding='utf8')
        self.diss_f.write('Frame;Hour;Neighbourhood;Total;Locals;Outsiders;home_total;home_locals;home_outsiders;work_total;work_locals;work_outsiders;\n')

        

        self.nodes_sir_f = open(self.base_path +  "nodes_sir.csv", 'w', encoding='utf8')
        self.nodes_sir_f.write('Frame;Hour;Date;NHnode;NHLat;NHLong;InnerNHnode;InnerLat;InnerLong;Susceptible;Infected;Removed;Vaccinated;dS;dI;dR;dV;Total;Locals;Outsiders;\n')

        #"Frame;Hour;Date;NHnode;NHLat;NHLong;InnerNHnode;InnerLat;InnerLong;Susceptible;Infected;Removed;dS;dI;dR;Total;Locals;Outsiders;"

        self.positions_f = open(self.base_path + "node_positions.csv", 'w', encoding='utf8')
        self.positions_f.write('Frame;ID;RegionPosition;NodeImagePosition;Quantity;\n')

    def stop_logging(self, show_figures: bool = True, export_html: bool = False, export_figures: bool = False):
        self.global_f.close()
        self.regions_f.close()
        self.nodes_f.close()
        self.positions_f.close()
        self.diss_f.close()
        
        for p in self.plugins_to_record:
            if isinstance(p, environment.TimeActionPlugin):
                p.stop_logger()
        
        if not (show_figures or export_figures or export_html): return
        
        layout_update = {"font_size":24, "legend_font_size":18, "width": 1920, "height": 1080, "autosize":False}
        self.process_blob_count_line_plots(show_figures, export_html, export_figures, layout_update)
        self.process_env_population_line_plots(show_figures, export_html, export_figures, layout_update)
        self.process_custom_line_plots(show_figures, export_html, export_figures, layout_update)
            
    
    def record_frame(self, _graph:environment.EnvironmentGraph, _frame:int):
        if LoggerDefaultRecordKey.BLOB_COUNT_GLOBAL in self.data_to_record:
            self.blob_global_count.append(_graph.get_blob_count())
        if LoggerDefaultRecordKey.BLOB_COUNT_REGION in self.data_to_record:
            for r,v in self.graph.region_dict.items():
                self.blob_region_count[r].append(v.get_blob_count())
        if LoggerDefaultRecordKey.BLOB_COUNT_NODE in self.data_to_record:
            for n,v in self.graph.node_dict.items():
                self.blob_node_count[n].append(len(v.contained_blobs))
                
        if LoggerDefaultRecordKey.ENV_GLOBAL_POPULATION in self.data_to_record:
            self.global_frame(_graph, _frame)
        if LoggerDefaultRecordKey.ENV_REGION_POPULATION in self.data_to_record:
            self.region_frame(_graph, _frame)
        if LoggerDefaultRecordKey.ENV_NODE_POPULATION in self.data_to_record:
            self.node_frame(_graph, _frame)
            
            
        if 'graph' in self.data_to_record:
            self.graph_frame(_graph, _frame)
        if 'metrics' in self.data_to_record:
            self.record_metrics(_graph, _frame)
        if 'nodes_sir' in self.data_to_record:
            self.node_sir_frame(_graph, _frame)
        if 'positions' in self.data_to_record:
            self.positions_frame(_graph, _frame)
        if 'neighbourhood_disserta' in self.data_to_record:
            self.disserta_frame(_graph, _frame)
        
        for p in self.plugins_to_record:
            if isinstance(p,environment.TimeActionPlugin):
                p.log_data(graph=_graph, frame=_frame)
    
    
    
    def global_frame(self, graph: environment.EnvironmentGraph, frame:int):
        
        # Sets the default row
        _row = f"{frame};{frame % self.time_cycle};{frame // self.time_cycle}"
        
        # Adds any custom template data
        _current_frame = {}
        for h,pt in self.global_custom_templates.items():
            _current_frame[h] = graph.get_population_size(pt)
            _row += ";" + str(_current_frame[h])

        # Adds deltas of any custom template data
        for h in self.global_custom_templates:
            _row += ";" + str(_current_frame[h] - self.global_prev_frame[h])
        
        # Updates last frame and writes the data
        self.global_prev_frame = {k:v for k,v in _current_frame.items()}
        self.global_f.write(_row + '\n')

    def region_frame(self, graph: environment.EnvironmentGraph, frame:int):
        
        for _name, _rg in graph.region_dict.items():
            # Gets populations from this frame
            total_pop = _rg.get_population_size()
            pop_template = PopTemplate()
            pop_template.mother_blob_id = _rg.id
            local_pop = _rg.get_population_size(pop_template)
            outside_pop = total_pop - local_pop
            
            # Gets populations from last frame
            last_total, last_local = self.regions_prev_frame[_name]['__populations']
            last_ouside = last_total - last_local
            
            # Sets the default row
            _row = f"{frame};{frame % self.time_cycle};{frame // self.time_cycle};{_name};{total_pop};{local_pop};{outside_pop};{total_pop-last_total};{local_pop-last_local};{outside_pop-last_ouside}"
            
            
            # Adds any custom data
            _current_frame = {}
            for h,pt in self.region_custom_templates.items():
                _current_frame[h] = _rg.get_population_size(pt)
                _row += ";" + str(_current_frame[h])
             # Adds deltas of any custom template data
            for h in self.region_custom_templates:
                _row += ";" + str(_current_frame[h] - self.regions_prev_frame[_name][h])

            # Updates last frame and writes the data
            self.regions_prev_frame[_name] = {k:v for k,v in _current_frame.items()}
            self.regions_prev_frame[_name]['__populations'] = [total_pop, local_pop]
            self.regions_f.write(_row + '\n')
            
    def node_frame(self, graph:environment.EnvironmentGraph, frame:int):
        
        for _name, _nd in graph.node_dict.items():
            # Gets populations from this frame
            total_pop = _nd.get_population_size()
            pop_template = PopTemplate()
            pop_template.mother_blob_id = graph.get_region_by_name(_nd.containing_region_name).id
            local_pop = _nd.get_population_size(pop_template)
            outside_pop = total_pop - local_pop
            
            # Gets populations from last frame
            last_total, last_local = self.nodes_prev_frame[_name]['__populations']
            last_ouside = last_total - last_local
            
            # Sets the default row
            _row = f"{frame};{frame % self.time_cycle};{frame // self.time_cycle};{_name};{total_pop};{local_pop};{outside_pop};{total_pop-last_total};{local_pop-last_local};{outside_pop-last_ouside}"
                        
            # Adds any custom data
            _current_frame = {}
            for h,pt in self.node_custom_templates.items():
                _current_frame[h] = _nd.get_population_size(pt)
                _row += ";" + str(_current_frame[h])
            # Adds deltas of any custom template data
            for h in self.node_custom_templates:
                _row += ";" + str(_current_frame[h] - self.nodes_prev_frame[_name][h])

            # Updates last frame and writes the data
            self.nodes_prev_frame[_name] = {k:v for k,v in _current_frame.items()}
            self.nodes_prev_frame[_name]['__populations'] = [total_pop, local_pop]
            self.nodes_f.write(_row + '\n')


    def node_region_id2position(self, graph: environment.EnvironmentGraph):
        region_f =  open('output_logs/' + self.base_filename + "//" + "region_ids.csv", 'w', encoding='utf8')
        region_f.write('ID;ImagePosition;Name;\n')
        node_f =  open('output_logs/' + self.base_filename + "//" +  "node_ids.csv", 'w', encoding='utf8')
        node_f.write('ID;ImagePosition;Name;\n')
        for region in graph.region_list:
            region_f.write(f'{region.id};{region.position};{region.name};\n')
            for node in region.node_list:
                node_f.write(f'{node.id};{node.get_characteristic("long_lat_position")};{node.get_unique_name()};\n')
        region_f.close()
        node_f.close()

    def positions_frame(self, graph, frame):

        for region in graph.region_list:
            for node in region.node_list:
                for blob in node.contained_blobs:
                    n_pos = f'{frame};{blob.blob_id};{region.id};{node.id};{blob.get_population_size(self.pop_template)};\n'
                    self.positions_f.write(n_pos)




    def graph_frame(self, graph, frame):
        log_path = 'Logs/' + self.base_filename + '/'
        if not os.path.exists(log_path):
            os.makedirs(log_path)
        f = open('{0}/log{1:0=5d}'.format(log_path, frame) + '.json', 'w', encoding='utf-8')
        f.write(str(graph).replace('\'', '\"'))
        #f.write(str(graph))
        f.close()
        

    

    def disserta_frame(self, graph, frame):
        
        for region_name, region in graph.region_dict.items():
            

            totals = region.get_population_size()

            tmp = PopTemplate()

            tmp.mother_blob_id = region.id
            local_people = region.get_population_size(tmp)

            home_t = region.get_node_by_name('home').get_population_size()
            work_t = region.get_node_by_name('work').get_population_size()

            home_l = region.get_node_by_name('home').get_population_size(tmp)
            work_l = region.get_node_by_name('work').get_population_size(tmp)

            s = f"{frame};{frame % self.time_cycle};{region.name};{totals};{local_people};{totals - local_people};{home_t};{home_l};{home_t - home_l};{work_t};{work_l};{work_t - work_l};\n"


            self.diss_f.write(s)


    

    def node_sir_frame(self, graph, frame):
        
        #susc_tmp, inft_tmp, remv_tmp, vacc_tmp = PopTemplate()

        susc_tmp = PopTemplate()
        susc_tmp.add_block('susceptible')

        inft_tmp = PopTemplate()
        inft_tmp.add_block('infected')

        remv_tmp = PopTemplate()
        remv_tmp.add_block('removed')

        vacc_tmp = PopTemplate()
        vacc_tmp.add_block('vaccinated')

        


        for node in graph.node_list:
            #print (node.get_unique_name())
            _node_name = str(node.get_unique_name())
            _region = graph.get_region_by_name(node.containing_region_name)
            #print(_region.name)
            #print(_region.position)
            if _node_name not in self.nodes_sir_last_frames:
                self.nodes_sir_last_frames[_node_name] = (0,0,0,0)

            _last_frame = self.nodes_sir_last_frames[_node_name]

            
            susceptible = 0
            infected = 0
            removed = 0
            vaccinated = 0

            tmp = copy.deepcopy(self.pop_template)

            total = node.get_population_size(tmp)

            tmp.mother_blob_id = graph.get_region_by_name(node.containing_region_name).id

            local_people = node.get_population_size(tmp)


            _s = node.get_population_size(susc_tmp)
            _i = node.get_population_size(inft_tmp)
            _r = node.get_population_size(remv_tmp)
            _v = node.get_population_size(vacc_tmp)

            #s = f"{frame};{frame % self.time_cycle};{node.get_unique_name()};{total};{local_people};{total - local_people};\n"
            s = "{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};\n".format(
                frame, frame % self.time_cycle, 0, 
                node.containing_region_name, _region.long_lat[0], _region.long_lat[1],
                node.name,node.characteristics["long_lat_position"][0],node.characteristics["long_lat_position"][1],
                _s, _i, _r, _v,
                _s - _last_frame[0], _i - _last_frame[1], _i - _last_frame[2], _v - _last_frame[3],
                total, local_people, total - local_people)
                #susceptible, infected, removed, vaccinated, susceptible - l_susc, infected - l_inf, removed - l_rem, vaccinated - l_vac)
        
            self.nodes_sir_f.write(s)

            self.nodes_sir_last_frames[_node_name] = _s, _i, _r, _v

        #"Frame;Hour;Date;
        # NHnode;NHLat;NHLong;
        # InnerNHnode;InnerLat;InnerLong;
        # Susceptible;Infected;Removed;Vaccinated
        # dS;dI;dR;dV
        # Total;Locals;Outsiders;"

    


    def node_od_matrix_frame(self, graph, frame, foreign_only = False):
        self.node_OD_matrix[frame] = {}
        for node in graph.node_list:
            for blob in node.contained_blobs:
                blob_region = graph.get_region_by_id(blob.mother_blob_id)
                blob_node = blob_region.get_node_by_name('home')
                if foreign_only and blob_node.get_unique_name() == node.get_unique_name():
                    continue
                else:
                    k = f'{blob_node.get_unique_name()}#{node.get_unique_name()}'

                if k not in self.node_OD_matrix[frame]:
                    self.node_OD_matrix[frame][k] = 0

                self.node_OD_matrix[frame][k] = self.node_OD_matrix[frame][k] + blob.get_population_size(self.pop_template)


    def region_od_matrix_frame(self, graph, frame, foreign_only = False):
        self.region_OD_matrix[frame] = {}
        for region in graph.region_list:
            region_blobs = []
            for node in region.node_list:
                region_blobs.extend(node.contained_blobs)

            for blob in region_blobs:
                blob_region = graph.get_region_by_id(blob.mother_blob_id)
                if foreign_only and blob_region.name == region.name:
                    continue
                else:
                    k = f'{blob_region.name}#{region.name}'
                if k not in self.region_OD_matrix[frame]:
                    self.region_OD_matrix[frame][k] = 0

                self.region_OD_matrix[frame][k] = self.region_OD_matrix[frame][k] + blob.get_population_size(self.pop_template)


    #stores a matrix of [distance traveled, number of travels]
    def total_region_travel_frame(self, graph, frame):
        for region in graph.region_list:
            region_blobs = []
            for node in region.node_list:
                region_blobs.extend(node.contained_blobs)

            for blob in region_blobs:
                blob_region = graph.get_region_by_id(blob.mother_blob_id)

                if blob_region.name not in self.region_travel:
                    self.region_travel[blob_region.name] = np.array([0,0])

                distance = util.distance2D(region.position, blob_region.position)
                quant = blob.get_population_size(self.pop_template)
                self.region_travel[blob_region.name] = self.region_travel[blob_region.name] + np.array([distance * quant, quant])


    def total_region_travel_no_own_region_frame(self, graph, frame):
        for region in graph.region_list:
            region_blobs = []
            for node in region.node_list:
                region_blobs.extend(node.contained_blobs)

            for blob in region_blobs:
                blob_region = graph.get_region_by_id(blob.mother_blob_id)

                if blob_region.name not in self.region_no_own_travel:
                    self.region_no_own_travel[blob_region.name] = np.array([0,0])
                if region.name == blob_region.name:
                    continue

                distance = util.distance2D(region.position, blob_region.position)
                quant = blob.get_population_size(self.pop_template)
                self.region_no_own_travel[blob_region.name] = self.region_no_own_travel[blob_region.name] + np.array([distance * quant, quant])


    # same data as quant from total_region_travel_no_own_region_frame
    def total_time_spent_outside_frame(self, graph, frame):
        pass


    def record_metrics(self, graph, frame):
        self.node_od_matrix_frame(graph, frame, foreign_only=self.foreign_only)
        self.region_od_matrix_frame(graph, frame, foreign_only=self.foreign_only)
        self.total_region_travel_frame(graph, frame)
        self.total_region_travel_no_own_region_frame(graph, frame)
        #self.total_time_spent_outside_frame(graph, frame)


    def compute_region_travel_data(self, travel_dict, output_file):
        header = f'Region;MeanTravelDistance\n'
        output_file.write(header)

        for k,v in travel_dict.items():
            travel_distance, travels = v
            if travels != 0:
                output_file.write(f'{k};{float(travel_distance) /  float(travels)}\n')
            else:
                output_file.write(f'{k};{0}\n')



    def compute_region_time_outside_data(self, total_frames, travel_dict, output_file):
        header = f'Region;AveragePopulationOutsidePerFrame\n'
        output_file.write(header)

        for k,v in travel_dict.items():
            _, travels = v
            output_file.write(f'{k};{float(travels) / float(total_frames)}\n')


    def complete_od_matrix(self, od_matrix):
        comp_matrix = {}
        total_keys = set(od_matrix.keys())
        for k in od_matrix.keys():
            total_keys = total_keys | set(od_matrix[k].keys())

        for k1 in total_keys:
            comp_matrix[k1] = {}
            for k2 in total_keys:
                if k1 not in od_matrix:
                    od_matrix[k1] = {}
                if k2 not in od_matrix[k1]:
                    comp_matrix[k1][k2] = "N/A"
                else:
                    comp_matrix[k1][k2] = od_matrix[k1][k2]
        
        return comp_matrix

    def decompose_od_matrix(self, composed_od_matrix):
        decomposed_od_matrix = {}

        for k in composed_od_matrix.keys():
            k1, k2 = k.split("#")
            val = composed_od_matrix[k]

            if k1 not in decomposed_od_matrix:
                decomposed_od_matrix[k1] = {}

            if k2 not in decomposed_od_matrix[k1]:
                decomposed_od_matrix[k1][k2] = 0

            decomposed_od_matrix[k1][k2] = decomposed_od_matrix[k1][k2] + val

        return self.complete_od_matrix(decomposed_od_matrix)


    def normalize_od_matrix(self, od_matrix):
        mean_pop_od_matrix = {}

        for k1 in od_matrix.keys():
            mean_pop_od_matrix[k1] = {}
            k1_total = 0
            for k2 in od_matrix[k1].keys():
                v = od_matrix[k1][k2]
                k1_total += float(v) if v != "N/A" else 0

            for k2 in od_matrix[k1].keys():
                v = od_matrix[k1][k2]
                mean_pop_od_matrix[k1][k2] = ((v if v != "N/A" else 0) / k1_total) if k1_total != 0 else 0

        return mean_pop_od_matrix

    def add_matrices(self, m1, m2):
        combined_matrix = {}
        total_keys = set(m1.keys()) | set(m2.keys())
        
        for k1 in total_keys:
            combined_matrix[k1] = {}
            for k2 in total_keys:
                if k1 not in m1 or k2 not in m1[k1]:
                    v1 = "N/A"
                else:
                    v1 = m1[k1][k2]
                if k1 not in m2 or k2 not in m2[k1]:
                    v2 = "N/A"
                else:
                    v2 = m2[k1][k2]

                if v1 == "N/A" and v2 == "N/A":
                    v = "N/A"
                else:
                    if v1 == "N/A" and v2 != "N/A":
                        v = v2
                    elif v2 == "N/A" and  v1 != "N/A":
                        v = v1
                    else:
                        v = v1 + v2
                
                combined_matrix[k1][k2] = v
        return combined_matrix

    def divide_od_matrix_by_scalar(self, mat, scalar):
        div_mat = {}
        for k1 in mat.keys():
            div_mat[k1] = {}
            for k2 in mat[k1].keys():
                if mat[k1][k2] != "N/A":
                    div_mat[k1][k2] = mat[k1][k2] / scalar
                else:
                    div_mat[k1][k2] = "N/A"
        return div_mat
        

    def write_od_matrix(self, od_matrix, output_file):
        region_keys = set(od_matrix.keys())
        inner_keys = set()

        for k in region_keys:
            k_inner = set(od_matrix[k])
            region_keys = region_keys | k_inner

        h_tail = ';'.join(region_keys)
        header = f'{"Regions"};{h_tail}\n'
        output_file.write(header)

        for region1 in region_keys:
            line = f"{region1};"
            for region2 in region_keys:
                if region1 in od_matrix and region2 in od_matrix[region1]:
                    line +=  f'{od_matrix[region1][region2]};'
                else:
                    line += "N/A;"
            line = line[:-1]+'\n'
            output_file.write(line)


    def compute_mean_od_matrix(self, frame_matrices, total_frames, hourly=1):
        hourly_matrices = {}
        
        for i in range(hourly):
            hourly_matrices[i] = frame_matrices[i]

        for i in range(hourly, total_frames):
            hourly_matrices[i % hourly] = self.add_matrices(hourly_matrices[i % hourly], frame_matrices[i])

        for i in range(hourly):
            hourly_matrices[i] = self.divide_od_matrix_by_scalar(hourly_matrices[i], total_frames / hourly)

        return hourly_matrices


    def compute_composite_data(self, graph, total_frames, normalize = True):
        self.node_region_id2position(graph)
        with open(f'output_logs/{self.base_filename}/mean_travel.csv', 'w', encoding='utf8') as region_travel_file:
            self.compute_region_travel_data(self.region_travel, region_travel_file)

        with open(f'output_logs/{self.base_filename}/mean_travel_foreign_only.csv', 'w', encoding='utf8') as region_travel_no_own_file:
            self.compute_region_travel_data(self.region_no_own_travel, region_travel_no_own_file)

        with open(f'output_logs/{self.base_filename}/time_outside.csv', 'w', encoding='utf8') as time_spent_outside_file:
            self.compute_region_time_outside_data(total_frames, self.region_travel, time_spent_outside_file)

        with open(f'output_logs/{self.base_filename}/time_outside_foreign_only.csv', 'w', encoding='utf8') as time_spent_outside_no_own_file:
            self.compute_region_time_outside_data(total_frames, self.region_no_own_travel, time_spent_outside_no_own_file)

        region_od_matrices = {}
        node_od_matrices = {}

        for f in self.region_OD_matrix.keys():
            region_od_matrices[f] = self.decompose_od_matrix(self.region_OD_matrix[f])
            node_od_matrices[f] = self.decompose_od_matrix(self.node_OD_matrix[f])

        total_region_od_mean = self.compute_mean_od_matrix(region_od_matrices, total_frames, hourly=1)[0]
        total_node_od_mean = self.compute_mean_od_matrix(node_od_matrices, total_frames, hourly=1)[0]

        hourly_region_od_mean = self.compute_mean_od_matrix(region_od_matrices, total_frames, hourly=self.time_cycle)
        hourly_node_od_mean = self.compute_mean_od_matrix(node_od_matrices, total_frames, hourly=self.time_cycle)

        with open(f'output_logs/{self.base_filename}/node_od_matrix_total.csv', 'w', encoding='utf8') as total_node_od_matrix_file:
            if normalize:
                self.write_od_matrix(self.normalize_od_matrix(total_node_od_mean), total_node_od_matrix_file)
            else:
                self.write_od_matrix(total_node_od_mean, total_node_od_matrix_file)
        with open(f'output_logs/{self.base_filename}/region_od_matrix_total.csv', 'w', encoding='utf8') as total_region_od_matrix_file:
            if normalize:
                self.write_od_matrix(self.normalize_od_matrix(total_region_od_mean), total_region_od_matrix_file)
            else:
                self.write_od_matrix(total_region_od_mean, total_region_od_matrix_file)

        for i in range(self.time_cycle):
            with open(f'output_logs/{self.base_filename}/region_od_matrix_hourly-mean-{i}.csv', 'w', encoding='utf8') as hourly_region_od_matrix_file:
                if normalize:
                    self.write_od_matrix(self.normalize_od_matrix(hourly_region_od_mean[i]), hourly_region_od_matrix_file)
                else:
                    self.write_od_matrix(hourly_region_od_mean[i], hourly_region_od_matrix_file)
            with open(f'output_logs/{self.base_filename}/node_od_matrix_hourly-mean-{i}.csv', 'w', encoding='utf8') as hourly_node_od_matrix_file:
                if normalize:
                    self.write_od_matrix(self.normalize_od_matrix(hourly_node_od_mean[i]), hourly_node_od_matrix_file)
                else:
                    self.write_od_matrix(hourly_node_od_mean[i], hourly_node_od_matrix_file)

        # # per frame, hourly means and total means
        # for i in range(total_frames):
        #     with open(f'output_logs/{self.base_filename}_node_od_matrix-{i}.csv', 'w', encoding='utf8') as node_od_matrix_file:
        #         self.write_od_matrix(self.node_OD_matrix[i], node_od_matrix_file)

        #     with open(f'output_logs/{self.base_filename}_region_od_matrix-{i}.csv', 'w', encoding='utf8') as region_od_matrix_file:
        #         self.write_od_matrix(self.region_OD_matrix[i], region_od_matrix_file)


    def process_blob_count_line_plots(self, show_figures: bool, export_html: bool, export_figures: bool, layout_update):
        
        figures = []
        xaxes_upt = {"tickmode": "linear", "tick0": 0, "dtick": 24}
        
        if LoggerDefaultRecordKey.BLOB_COUNT_GLOBAL in self.data_to_record:
            df = pd.DataFrame({'Blob Count': self.blob_global_count})
            df = df.rename_axis('Simulation Frame')
            df.to_csv(self.data_frames_path + 'blob_count_global.csv', sep = ';')
            fig = px.line(df, y="Blob Count", title="Blob Count - Global")
            fig.update_xaxes(xaxes_upt)
            figures.append(fig)
            
            df = pd.DataFrame({'Blob Count': self.blob_global_count})
            df = df.iloc[::24].reset_index(drop = True)
            df.index = range(1,len(df)+1)
            df.rename_axis('Simulation Day', inplace = True)
            fig = px.line(df, y="Blob Count", title="Blob Count - Global - Hour 0", markers=True)
            figures.append(fig)
            
            
        if LoggerDefaultRecordKey.BLOB_COUNT_REGION in self.data_to_record:
            df = pd.DataFrame(self.blob_region_count)
            df = df.rename_axis('Simulation Frame').rename_axis('Region', axis=1)
            df.to_csv(self.data_frames_path + 'blob_count_region.csv', sep = ';')
            fig = px.line(df, labels={'value':'Blob Count'}, 
                                            title="Blob Count - Per Region")
            fig.update_xaxes(xaxes_upt)
            figures.append(fig)
            
            df = pd.DataFrame(self.blob_region_count)
            df = df.iloc[::24].reset_index(drop = True)
            df.index = range(1,len(df)+1)
            df = df.rename_axis('Simulation Day').rename_axis('Region', axis=1)
            fig = px.line(df, labels={'value':'Blob Count'}, 
                            title="Blob Count - Per Region - Hour 0", markers=True)
            figures.append(fig)
            
        if LoggerDefaultRecordKey.BLOB_COUNT_NODE in self.data_to_record:
            df = pd.DataFrame(self.blob_node_count)
            df = df.rename_axis('Simulation Frame').rename_axis('Node', axis=1)
            df.to_csv(self.data_frames_path + 'blob_count_node.csv', sep = ';')
            fig = px.line(df, labels={'value':'Blob Count'}, 
                            title="Blob Count - Per Node")
            fig.update_xaxes(xaxes_upt)
            figures.append(fig)
            
            df = pd.DataFrame(self.blob_node_count)
            df = df.iloc[::24].reset_index(drop = True)
            df.index = range(1,len(df)+1)
            df = df.rename_axis('Simulation Day').rename_axis('Node', axis=1)
            fig = px.line(df, labels={'value':'Blob Count'}, 
                            title="Blob Count - Per Node - Hour 0", markers=True)
            figures.append(fig)
            
        self.generate_figures(show_figures,export_figures, export_html, layout_update, figures)
      
    def process_env_population_line_plots(self, show_figures: bool, export_html: bool, export_figures: bool, layout_update):
        
        figures = []
        xaxes_upt = {"tickmode": "linear", "tick0": 0, "dtick": 24}
                    
        if LoggerDefaultRecordKey.ENV_REGION_POPULATION in self.data_to_record:
            # Default Region Population Plot
            df = pd.read_csv(self.base_path +  "regions.csv", sep = ';')
            fig = px.line(df, x = 'Frame',y = 'Total',color="Region", 
                          labels={'Total':'Region Population'}, 
                          title="Total Population - Per Region")
            fig.update_xaxes(xaxes_upt)
            figures.append(fig)
            # Default Region Population Plot - Hour 0
            df = df[df['Hour'] == 0].reset_index(drop = True)
            df.index = range(1,len(df)+1)
            fig = px.line(df, x = 'Day',y = 'Total',color="Region", 
                          labels={'Total':'Region Population', 'Day':'Simulation Day'}, 
                          title="Total Population - Per Region - Hour 0", markers=True)
            figures.append(fig)
            
        if LoggerDefaultRecordKey.ENV_NODE_POPULATION in self.data_to_record:
            # Default Node Population Plot
            df = pd.read_csv(self.base_path +  "nodes.csv", sep = ';')
            fig = px.line(df, x = 'Frame',y = 'Total',color="Node", 
                          labels={'Total':'Node Population'}, 
                          title="Total Population - Per Node")
            fig.update_xaxes(xaxes_upt)
            figures.append(fig)
            
            # Default Node Population Plot - Hour 0
            df = df[df['Hour'] == 0].reset_index(drop = True)
            df.index = range(1,len(df)+1)
            fig = px.line(df, x = 'Day',y = 'Total',color="Node", 
                          labels={'Total':'Node Population', 'Day':'Simulation Day'}, 
                          title="Total Population - Per Node - Hour 0", markers=True)
            figures.append(fig)
                
        self.generate_figures(show_figures,export_figures, export_html, layout_update, figures)         
                
    def process_custom_line_plots(self, show_figures: bool, export_html: bool, export_figures: bool, layout_update):
        
        figures = []
        xaxes_upt = {"tickmode": "linear", "tick0": 0, "dtick": 24}
        print("processing custom line plots")
        # Custom Plot lines
        for name, config in self.custom_line_plots.items():
            print("Here")
            _file, _x, _y, _cols, _h, _lvl, _f = config
            
            # Skip unrecorded data
            if _lvl == 'Region' and LoggerDefaultRecordKey.ENV_REGION_POPULATION not in self.data_to_record: continue
            if _lvl == 'Node' and LoggerDefaultRecordKey.ENV_NODE_POPULATION not in self.data_to_record: continue
            
            # Read the file
            print("Reading file: ", self.base_path +  _file)
            df = pd.read_csv(self.base_path +  _file, sep = ';')
            
            # Filter columns and entries accordingly
            if _h: df = df[df['Hour'].isin(_h)].reset_index(drop = True)
            if _f and _lvl == 'Region': df = df[df['Region'].isin(_f)].reset_index(drop = True)
            if _f and _lvl == 'Node': df = df[df['Node'].str.contains('|'.join(_f))].reset_index(drop = True)
            
            # No level or filter (global) = can be plotted directly
            if _lvl is None and _f is None:
                fig = px.line(df,y = _cols,
                        labels={'index': _x, 'value': _y, 'variable': 'Legend'}, 
                        title=name)
            # Filters EnvRegions or EnvNode types as requested
            else:
                to_track = []
                df2 = pd.DataFrame()
                for r in df[_lvl].unique():
                    for c in _cols:
                        df2[r + ": " + c] =  df[df[_lvl] == r].reset_index()[c]
                        to_track.append(r + ": " + c)
                fig = px.line(df2,y = to_track,
                            labels={'index': _x, 'value': _y, 'variable': 'Legend'}, 
                            title=name)
            fig.update_xaxes(xaxes_upt)
            figures.append(fig)
        #  def add_custom_line_plot(self, _key:str, file, x_label:str, y_label:str, columns:list[str] = None, hours: list[str] = None, _level_to_filter:str = None, _to_filter: list[str] = None):
        # self.custom_line_plots[_key] = (file, x_label, y_label, columns, hours, _level_to_filter, _to_filter)    
        
        # #Custom Global Line Plots
        # if LoggerDefaultRecordKey.ENV_GLOBAL_POPULATION in self.data_to_record:
        #     for name, config in self.global_custom_line_plots.items():
        #         _x, _y, _c, _h = config
        #         df = pd.read_csv(self.base_path +  "global.csv", sep = ';')
        #         if _h: df = df[df['Hour'].isin(_h)].reset_index(drop = True)
        #         fig = px.line(df, y = _c,
        #                    labels={'index': _x, 'value': _y, 'variable': 'Legend'}, 
        #                    title=name)
        #         fig.update_xaxes(xaxes_upt)
        #         figures.append(fig)
                
        # #Custom Region Line Plots       
        # if LoggerDefaultRecordKey.ENV_REGION_POPULATION in self.data_to_record:
        #     for name, config in self.region_custom_line_plots.items():
        #         _x, _y, _c, _n, _h = config
        #         df = pd.read_csv(self.base_path +  "regions.csv", sep = ';')
        #         if _h: df = df[df['Hour'].isin(_h)].reset_index(drop = True)
        #         if _n: df = df[df['Region'].isin(_n)].reset_index(drop = True)
        #         to_track = []
        #         df2 = pd.DataFrame()
        #         for r in df['Region'].unique():
        #             for c in _c:
        #                 df2[r + ": " + c] =  df[df['Region'] == r].reset_index()[c]
        #                 to_track.append(r + ": " + c)
        #         fig = px.line(df2,y = to_track,
        #                    labels={'index': _x, 'value': _y, 'variable': 'Legend'}, 
        #                    title=name)
        #         fig.update_xaxes(xaxes_upt)
        #         figures.append(fig)
                
        # #Custom Node Line Plots
        # if LoggerDefaultRecordKey.ENV_NODE_POPULATION in self.data_to_record:
        #     for name, config in self.node_custom_line_plots.items():
        #         _x, _y, _c, _n, _h = config
        #         df = pd.read_csv(self.base_path +  "nodes.csv", sep = ';')
        #         if _h: df = df[df['Hour'].isin(_h)].reset_index(drop = True)
        #         if _n: df = df[df['Node'].str.contains('|'.join(_n))].reset_index(drop = True)
        #         to_track = []
        #         df2 = pd.DataFrame()
        #         for r in df['Node'].unique():
        #             for c in _c:
        #                 df2[r + ": " + c] =  df[df['Node'] == r].reset_index()[c]
        #                 to_track.append(r + ": " + c)
        #         fig = px.line(df2,y = to_track,
        #                    labels={'index': _x, 'value': _y, 'variable': 'Legend'}, 
        #                    title=name)
        #         fig.update_xaxes(xaxes_upt)
        #         figures.append(fig)
                
        self.generate_figures(show_figures, export_figures, export_html, layout_update, figures)
                
    def generate_figures(self, show_figures:bool, export_figures:bool, export_html:bool, layout_update:dict, figures):
        for f in figures: 
            f.update_layout(layout_update)
            if show_figures:
                sleep(0.5)
                f.show()
        for f in figures:
            if export_figures:
                f.write_image(self.figures_path + f.layout.title.text.replace(" ","") + ".png", format = 'png')
            if export_html:
                f.write_html(self.html_plots_path + f.layout.title.text.replace(" ","") + ".html")