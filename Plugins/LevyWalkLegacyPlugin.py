import sys
sys.path.append('../')

import environment 
from population import PopTemplate
import util
from scipy.stats import levy
import random


class LevyWalkLegacyPlugin(environment.TimeActionPlugin):

    def __init__(self, env_graph):
        '''levy_walk
            Pushes population to nearby nodes into a requesting node.


                Requirements:
                    Nodes must have position values in their characteristic dictionaries.

                Params:
                    region: origin region.
                    node: origin node.
                    dist_location: optional levy distribution location parameter.
                    dist_scale: optional levy distribution scale parameter.
                    population_template: PopTemplate to be matched by the operation.

                    isolation_rate: the quantity to reduce movements by. simulates social isolation.
                
                iso_mode: Can be:
                    'regular'
                        Normal plugin operation
        '''
        super().__init__()
        
        self.graph = env_graph
        self.set_pair('levy_walk', self.levy_walk)

        self.mobility_scale = 50

        self.dist_dict = {}
        self.dist_buckets = {}
        self.bucket_size = 50
        self.use_buckets  = True

        self.distribution_sampler = levy
        self.distribution_scale = 50
        self.distribution_location = 30
        
        self.levy_probability = 0.05


    def get_distances(self, node, graph):
        if self.use_buckets:
            if node.get_unique_name() in self.dist_buckets:
                return self.dist_buckets[node.get_unique_name()]
        else:
            if node.get_unique_name() in self.dist_dict:
                return self.dist_dict[node.get_unique_name()]

        distance_list = []
        node_pos = node.get_characteristic('world_position')
        for n in graph.node_list:
            if node.get_unique_name() == n.get_unique_name():
                continue
            node2_pos = n.get_characteristic('world_position')
            distance_list += [(util.distance2D(node_pos, node2_pos), n.get_unique_name())]

        distance_list = sorted(distance_list)

        self.dist_dict[node.get_unique_name()] = distance_list

        max_bucket = int(distance_list[-1][0] // self.bucket_size)
        self.dist_buckets[node.get_unique_name()] = {}
        for i in range(max_bucket+1):
            self.dist_buckets[node.get_unique_name()][i] = []

        for d in distance_list:
            bucket = d[0] // self.bucket_size
            self.dist_buckets[node.get_unique_name()][bucket] += [d]

        if self.use_buckets:
            return self.dist_buckets[node.get_unique_name()]
        else:
            return self.dist_dict[node.get_unique_name()]


    def binary_search(self, _list, v):
        l = 0
        u = len(_list) - 1

        while l < u and l != (u-1):
            m = (l + u) // 2
            v2 = _list[m][0]
            if v2 > v:
                u = m
            else:
                l = m

        if l == 0:
            l =  ( -1 if _list[0][0] > v else 0)
        
        return l


    def bucket_search(self, _list, v):
        bucket = v // self.bucket_size
        if bucket not in _list:
            return None
        
        l = _list[bucket]

        if len(l) == 0:
            return None

        ix = random.randint(0, len(l)-1)

        if l[0][0] > v:
            return None

        return l[ix]

    def levy_sample(self, location = None, scale = None):
        if location is not None and scale is not None:
            self.distribution_sampler.rvs(loc=location,
                                          scale= scale,
                                          size = 1)
        else:
            return self.distribution_sampler.rvs(loc=self.distribution_location,
                                                 scale= self.distribution_scale,
                                                 size = 1)


        ## returns everyone home
    def levy_walk(self, values, hour, time):
        region = values['region']
        if isinstance(region, str):
            region = self.graph.get_region_by_name(region)

        node = values['node']
        if isinstance(node, str):
            node = region.get_node_by_name(node)


        pop_template = values['population_template']

        node_population = node.get_population_size(pop_template)

        distances = self.get_distances(node, self.graph)

        packets = node_population // self.mobility_scale

        sub_list = []
        for i in range(packets):
            
            if self.levy_probability < random.random():
                continue
            
            if 'dist_location' in values and 'dist_scale' in values:
                distance = self.levy_sample(location=float(values['dist_location']),
                                            scale=float(values['dist_scale']))[0]
            else:
                distance = self.levy_sample()[0]

            
            # ix = -1
            # for d in range(len(distances)):
            #     if distance > distances[d][0]:
            #         ix = d
            #         break

            if self.use_buckets:
                selected = self.bucket_search(distances, distance)
                if selected == None:
                    continue
                target_node_u_name = selected[1]
            else:
                ix = self.binary_search(distances, distance)
                if ix == -1:
                    continue
                
                target_node_u_name =  distances[ix][1]

            target_region, target_node = target_node_u_name.split('//')
            target_region = self.graph.get_region_by_name(target_region)
            target_node = target_region.get_node_by_name(target_node)


            new_action_values = {}
            new_action_type = 'move_population'
            
            new_action_values['origin_region'] = region.name

            new_action_values['origin_node'] = node.name
            new_action_values['destination_region'] = target_region.name

            new_action_values['destination_node'] = target_node.name
            
            new_action_values['quantity'] = self.mobility_scale
            pop_template.mother_blob_id = target_region.id
            new_action_values['population_template'] = pop_template

            new_action = environment.TimeAction(action_type = new_action_type, values = new_action_values)
            sub_list.append(new_action)
                    
        return sub_list


    def get_node_distance_matrix(self):        
        distance_matrix = {}
        for k in self.dist_dict:
            k_list = self.dist_dict[k]
            distance_matrix[k] = {}
            for i in k_list:
                distance_matrix[k][i[1]] = i[0]

        return distance_matrix

    def get_region_distance_matrix(self):        
        distance_matrix = {}

        for r1 in self.graph.region_list:
            distance_matrix[r1.name] = {}
            for r2 in self.graph.region_list:
                distance_matrix[r1.name][r2.name] = util.distance2D(r1.position, r2.position)

        return distance_matrix


if __name__ == "__main__":
    import seaborn as sns
    import matplotlib.pyplot as plt
    import numpy as np

    

    dist = np.array(levy.rvs(loc=1, scale= 1, size = 10000))
    bins = np.arange(0,10, 0.1)
    s = sns.histplot(dist, bins=bins)
    #figure = s.get_figure()
    plt.savefig('l1-s1-levy.png', dpi=400)
    print(f'scale 1, mean {sum(dist)/10000}')
    plt.clf()

    dist = np.array(levy.rvs(loc=50, scale= 50, size = 10000))
    bins = np.arange(0,600, 1)
    s = sns.histplot(dist, bins=bins)
    #figure = s.get_figure()
    plt.savefig('l50-s50-levy.png', dpi=400)
    print(f'scale 50, mean {sum(dist)/10000}')
    plt.clf()

    dist = np.array(levy.rvs(loc=100, scale= 50, size = 10000))
    bins = np.arange(0,600, 1)
    s = sns.histplot(dist, bins=bins)
   #figure = s.get_figure()
    plt.savefig('l100-s50-levy.png', dpi=400)
    print(f'scale 50, mean {sum(dist)/10000}')
    plt.clf()

    dist = np.array(levy.rvs(loc=50, scale= 100, size = 10000))
    bins = np.arange(0,600, 1)
    s = sns.histplot(dist, bins=bins)
    #figure = s.get_figure()
    plt.savefig('l50-s100-levy.png', dpi=400)
    print(f'scale 100, mean {sum(dist)/10000}')
    plt.clf()

    dist = np.array(levy.rvs(loc=75, scale= 75, size = 10000))
    bins = np.arange(0,600, 1)
    s = sns.histplot(dist, bins=bins)
    #figure = s.get_figure()
    plt.savefig('l75-s75-levy.png', dpi=400)
    print(f'scale 75, mean {sum(dist)/10000}')
    plt.clf()

    dist = np.array(levy.rvs(loc=400, scale= 100, size = 10000))
    bins = np.arange(390,1000, 1)
    s = sns.histplot(dist, bins=bins)
    #figure = s.get_figure()
    plt.savefig('l400-s100-levy.png', dpi=400)
    print(f'scale 100, mean {sum(dist)/10000}')
    plt.clf()

    dist = np.array(levy.rvs(loc=0, scale= 600, size = 10000))
    bins = np.arange(0,2500, 10)
    s = sns.histplot(dist, bins=bins)
    #figure = s.get_figure()
    plt.savefig('l0-s600-levy.png', dpi=400)
    print(f'scale 600, mean {sum(dist)/10000}')
    plt.clf()

    dist = np.array(levy.rvs(loc=0, scale= 100, size = 10000))
    bins = np.arange(0,1200, 10)
    s = sns.histplot(dist, bins=bins)
    #figure = s.get_figure()
    plt.ylim(0, 1000)
    plt.savefig('l0-s100-levy.png', dpi=400)
    print(f'scale 100, mean {sum(dist)/10000}')
    plt.clf()

    dist = np.array(levy.rvs(loc=0, scale= 200, size = 10000))
    bins = np.arange(0,1200, 10)
    s = sns.histplot(dist, bins=bins)
    #figure = s.get_figure()
    plt.savefig('l0-s200-levy.png', dpi=400)
    print(f'scale 200, mean {sum(dist)/10000}')
    plt.clf()

    dist = np.array(levy.rvs(loc=0, scale= 50, size = 10000))
    bins = np.arange(0,1200, 10)
    s = sns.histplot(dist, bins=bins)
    #figure = s.get_figure()
    plt.ylim(0, 1000)
    plt.savefig('l0-s50-levy.png', dpi=400)
    print(f'scale 50, mean {sum(dist)/10000}')