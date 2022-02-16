import environment
from population import PopTemplate
import os 
import util
import numpy as np
from pathlib import Path

import copy

class SimulationLogger():

    def __init__(self, base_filename, time_cycle=24):
        self.base_filename = base_filename

        Path('output_logs/' + base_filename).mkdir(parents=True, exist_ok=True)


        self.global_f = open('output_logs/' + base_filename + "//" + "global.csv", 'w', encoding='utf8')
        self.global_f.write('Frame;Hour;Vacc0;Vacc1;Vacc2;Vacc3;dI;dR;dV;\n')
        
        self.neigh_f = open('output_logs/' + base_filename + "//" +  "neigh.csv", 'w', encoding='utf8')
        self.neigh_f.write('Frame;Hour;Neighbourhood;Vacc0;Vacc1;Vacc2;d0;d1;d2;Total;Locals;Outsiders;\n')
                
        self.diss_f = open('output_logs/' + base_filename + "//" + "diss.csv", 'w', encoding='utf8')
        self.diss_f.write('Frame;Hour;Neighbourhood;Total;Locals;Outsiders;home_total;home_locals;home_outsiders;work_total;work_locals;work_outsiders;\n')

        self.nodes_f = open('output_logs/' + base_filename + "//" +  "nodes.csv", 'w', encoding='utf8')
        self.nodes_f.write('Frame;Hour;Node;Total;Locals;Outsiders;\n')

        self.nodes_sir_f = open('output_logs/' + base_filename + "//" +  "nodes_sir.csv", 'w', encoding='utf8')
        self.nodes_sir_f.write('Frame;Hour;Date;NHnode;NHLat;NHLong;InnerNHnode;InnerLat;InnerLong;Susceptible;Infected;Removed;Vaccinated;dS;dI;dR;dV;Total;Locals;Outsiders;\n')

        #"Frame;Hour;Date;NHnode;NHLat;NHLong;InnerNHnode;InnerLat;InnerLong;Susceptible;Infected;Removed;dS;dI;dR;Total;Locals;Outsiders;"

        self.positions_f = open('output_logs/' + base_filename + "//" + "node_positions.csv", 'w', encoding='utf8')
        self.positions_f.write('Frame;ID;RegionPosition;NodeImagePosition;Quantity;\n')

        self.data_to_record = set() #neighbourhood, global, graph, nodes, positions, metrics and neighbourhood_disserta

        self.last_frame = (0, 0, 0, 0)
        self.time_cycle = time_cycle

        self.neigh_last_frames = {}
        self.nodes_sir_last_frames = {}

        self.logs = {}

        self.foreign_only = True

        self.node_OD_matrix = {}
        self.region_OD_matrix = {}
        self.region_travel = {}
        self.region_no_own_travel = {}
        self.region_time_outside = {}


        self.pop_template = None

    def set_to_record(self, type):
        self.data_to_record.add(type)


    def node_region_id2position(self, graph):
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
        

    def neighbourhood_frame(self, graph, frame):
        
        for region_name, region in graph.region_dict.items():
            
            if region.name not in self.neigh_last_frames:
                self.neigh_last_frames[region.name] = (0,0,0)

            last_frame = self.neigh_last_frames[region.name]

            vac0_count = 0
            vac1_count = 0
            vac2_count = 0

            vac0_template = PopTemplate()
            vac0_template.set_traceable_property('vaccine_level', 0)

            vac1_template = PopTemplate()
            vac1_template.set_traceable_property('vaccine_level', 1)

            vac2_template = PopTemplate()
            vac2_template.set_traceable_property('vaccine_level', 2)

            for node in region.node_list:
                vac0_count += node.get_population_size(vac0_template)
                vac1_count += node.get_population_size(vac1_template)
                vac2_count += node.get_population_size(vac2_template)

            totals = vac0_count + vac1_count + vac2_count
            
            
            local_vac0 = 0
            local_vac1 = 0
            local_vac2 = 0

            vac0_template.mother_blob_id = region.id
            vac1_template.mother_blob_id = region.id
            vac2_template.mother_blob_id = region.id

            for node in region.node_list:
                local_vac0 += node.get_population_size(vac0_template)
                local_vac1 += node.get_population_size(vac1_template)
                local_vac2 += node.get_population_size(vac2_template)

            local_people =  local_vac0 + local_vac1 + local_vac2

            l_0, l_1, l_2 = last_frame

            s = f"{frame};{frame % self.time_cycle};{region.name};{vac0_count};{vac1_count};{vac2_count};{vac0_count - l_0};{vac1_count - l_1};{vac2_count - l_2};{totals};{local_people};{totals - local_people};\n"


            last_frame = vac0_count, vac1_count, vac2_count

            self.neigh_last_frames[region.name] = last_frame


            self.neigh_f.write(s)

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


    def node_frame(self, graph, frame):
        
        for node in graph.node_list:
            tmp = copy.deepcopy(self.pop_template)

            total = node.get_population_size(tmp)

            tmp.mother_blob_id = graph.get_region_by_name(node.containing_region_name).id

            local_people = node.get_population_size(tmp)

            s = f"{frame};{frame % self.time_cycle};{node.get_unique_name()};{total};{local_people};{total - local_people};\n"

            self.nodes_f.write(s)

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

    def global_frame(self, graph: environment.EnvironmentGraph, frame:int):
        vac0_count = 0
        vac1_count = 0
        vac2_count = 0
        vac3_count = 0

        vac0_template = PopTemplate()
        vac0_template.set_traceable_property('vaccine_level', 0)

        vac1_template = PopTemplate()
        vac1_template.set_traceable_property('vaccine_level', 1)

        vac2_template = PopTemplate()
        vac2_template.set_traceable_property('vaccine_level', 2)
        
        vac3_template = PopTemplate()
        vac3_template.set_traceable_property('vaccine_level', 3)

        for node in graph.node_list:
            vac0_count += node.get_population_size(vac0_template)
            vac1_count += node.get_population_size(vac1_template)
            vac2_count += node.get_population_size(vac2_template)
            vac3_count += node.get_population_size(vac3_template)

        last_0, last_1, last_2, last_3 = self.last_frame

        s = "{};{};{};{};{};{};{};{};\n".format(frame, frame % self.time_cycle, vac0_count, vac1_count, vac2_count, vac3_count, vac0_count - last_0, vac1_count - last_1, vac2_count - last_2)
        
        self.last_frame = vac0_count, vac1_count, vac2_count, vac3_count

        self.global_f.write(s)


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


    def record_frame(self, graph, frame):
        if 'global' in self.data_to_record:
            self.global_frame(graph, frame)
        if 'neighbourhood' in self.data_to_record:
            self.neighbourhood_frame(graph, frame)
        if 'graph' in self.data_to_record:
            self.graph_frame(graph, frame)
        if 'metrics' in self.data_to_record:
            self.record_metrics(graph, frame)
        if 'nodes' in self.data_to_record:
            self.node_frame(graph, frame)
        if 'nodes_sir' in self.data_to_record:
            self.node_sir_frame(graph, frame)
        if 'positions' in self.data_to_record:
            self.positions_frame(graph, frame)
        if 'neighbourhood_disserta' in self.data_to_record:
            self.disserta_frame(graph, frame)


    def close(self):
        self.global_f.close()
        self.neigh_f.close()
        self.nodes_f.close()
        self.positions_f.close()
        self.diss_f.close()