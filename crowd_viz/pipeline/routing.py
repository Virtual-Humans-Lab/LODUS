"""OSMnx graph acquisition and directed, speed-weighted street path cache."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
import networkx as nx
import osmnx as ox

SPEEDS = {'motorway': 80, 'trunk': 60, 'primary': 50, 'secondary': 40,
          'tertiary': 40, 'residential': 30, 'living_street': 15, 'service': 20}


def load_graph(path, mode='drive', bbox=(-51.32, -30.29, -51.00, -29.92)):
    path = Path(path)
    if path.exists():
        graph = ox.load_graphml(path)
        if graph.graph.get('mobility_mode') != mode:
            raise ValueError('Cached graph mode mismatch; use a separate GraphML per mode')
        return graph
    path.parent.mkdir(parents=True, exist_ok=True)
    ox.settings.cache_folder = str(path.parent/'overpass')
    ox.settings.requests_timeout = 180
    ox.settings.log_console = True
    graph = ox.graph_from_bbox(bbox, network_type=mode, retain_all=True)
    if mode == 'walk':
        nx.set_edge_attributes(graph, 4.8, 'speed_kph')
    else:
        graph = ox.routing.add_edge_speeds(graph, hwy_speeds=SPEEDS, fallback=30)
    graph = ox.routing.add_edge_travel_times(graph)
    graph.graph['mobility_mode'] = mode
    ox.save_graphml(graph, path)
    return graph


def distance(a, b):
    lat = math.radians((a[1]+b[1])/2)
    return math.hypot((a[0]-b[0])*math.cos(lat), a[1]-b[1])*111195


class Router:
    def __init__(self, graph, points, max_snap_m=2500):
        self.graph, self.points = graph, points
        self.ids = list(points)
        # Local projected search avoids optional scikit-learn dependency.
        self.node_ids = list(graph.nodes)
        coordinates = np.array([[graph.nodes[n]['x'], graph.nodes[n]['y']] for n in self.node_ids])
        self.snaps, self.snap_distances = {}, {}
        self.shortest, self.routes = {}, {}
        for name, xy in points.items():
            diff = (coordinates-np.array(xy))*np.array([math.cos(math.radians(xy[1])), 1])
            idx = int(np.argmin(np.sum(diff*diff, axis=1)))
            meters = distance(xy, coordinates[idx])
            if meters > max_snap_m:
                raise ValueError(f'{name}: nearest accessible road {meters:.0f} m away (limit {max_snap_m})')
            self.snaps[name] = self.node_ids[idx]
            self.snap_distances[name] = round(meters, 1)

    def from_origin(self, name):
        if name not in self.shortest:
            costs, paths = nx.single_source_dijkstra(self.graph, self.snaps[name], weight='travel_time')
            targets = set(self.snaps.values())
            self.shortest[name] = ({node:cost for node,cost in costs.items() if node in targets},
                                   {node:path for node,path in paths.items() if node in targets})
        return self.shortest[name]

    def cost(self, origin, destination):
        return self.from_origin(origin)[0].get(self.snaps[destination], math.inf)

    def route(self, origin, destination, k=1):
        key = f'{origin}\u2192{destination}'
        if key in self.routes:
            return self.routes[key]
        if self.snaps[origin] == self.snaps[destination]:
            # Co-located endpoints do not justify inventing a trip geometry.
            return []
        if not math.isfinite(self.cost(origin, destination)):
            return []
        if k == 1:
            paths = [self.from_origin(origin)[1][self.snaps[destination]]]
        else:
            paths = list(ox.routing.k_shortest_paths(self.graph, self.snaps[origin], self.snaps[destination], k, weight='travel_time'))
        result = []
        for path in paths:
            coords, seconds = [], []
            elapsed, length = 0., 0.
            for u, v in zip(path[:-1], path[1:]):
                edge = min(self.graph[u][v].values(), key=lambda e: e['travel_time'])
                start = (self.graph.nodes[u]['x'], self.graph.nodes[u]['y'])
                end = (self.graph.nodes[v]['x'], self.graph.nodes[v]['y'])
                line = list(edge['geometry'].coords) if 'geometry' in edge else [start, end]
                if distance(line[-1], start) < distance(line[0], start):
                    line.reverse()
                lengths = [distance(a,b) for a,b in zip(line[:-1], line[1:])]
                total = sum(lengths)
                if not coords:
                    coords.append(list(line[0][:2])); seconds.append(elapsed)
                for xy, segment in zip(line[1:], lengths):
                    elapsed += max(.001, float(edge['travel_time'])*segment/max(total, .001))
                    coords.append(list(xy[:2])); seconds.append(elapsed)
                length += float(edge['length'])
            if len(coords) >= 2:
                result.append({'id': f'{key}#{len(result)}', 'origin': origin, 'destination': destination,
                               'path': coords, 'seconds': seconds, 'duration': elapsed, 'meters': length})
        self.routes[key] = result
        return result

    def roads_geojson(self):
        features, seen = [], set()
        for u, v, edge in self.graph.edges(data=True):
            key = (min(u,v), max(u,v), str(edge.get('osmid')))
            if key in seen:
                continue
            seen.add(key)
            coords = list(edge['geometry'].coords) if 'geometry' in edge else [
                [self.graph.nodes[u]['x'],self.graph.nodes[u]['y']],
                [self.graph.nodes[v]['x'],self.graph.nodes[v]['y']]]
            features.append({'type':'Feature','properties':{'name':edge.get('name',''), 'class':edge.get('highway','')},
                             'geometry':{'type':'LineString','coordinates':coords}})
        return {'type':'FeatureCollection','features':features}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--graph', default='cache/porto-alegre-drive.graphml')
    parser.add_argument('--mode', choices=['drive','walk'], default='drive')
    args = parser.parse_args()
    graph = load_graph(args.graph, args.mode)
    print(json.dumps({'nodes':len(graph),'edges':graph.number_of_edges()}))
