"""Compile a whole 24-hour run into a self-contained browser bundle."""
import argparse
import csv
import hashlib
import json
import math
import time
from datetime import datetime, timezone
import unicodedata
from pathlib import Path
import numpy as np
from shapely.geometry import shape, mapping, Point
from shapely.ops import unary_union
from shapely import make_valid
from .ingest import population_frames, priors, extensions, read_table
from .od import estimate_od
from .routing import Router, load_graph


def canonical(text):
    text = ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if c.isalnum())
    return {'passodareia':'passodaareia', 'saojose':'vilasaojose',
            'centro':'centrohistorico', 'coronelaparicioborges':'celaparicioborges',
            'jardimdonaleopoldina':'jardimleopoldina'}.get(text, text)


def environment_index(environments, region_names):
    """Resolve known neighborhood aliases while preserving simulation IDs."""
    by_region = {}
    for region in environments:
        key = canonical(region['name'])
        if key in by_region:
            raise ValueError(f"Ambiguous environment neighborhood: {region['name']}")
        by_region[key] = region
    env, pois = {}, {}
    for name in region_names:
        region = by_region.get(canonical(name))
        if region is None:
            continue
        env[name] = region
        for poi in region.get('points_of_interest', []):
            poi_name = poi.get('name', poi.get('poi_type'))
            pois[f'{name}//{poi_name}'] = poi['lng_lat']
            if poi.get('unique_name'):
                pois[f"{name}//{poi['unique_name']}"] = poi['lng_lat']
    return env, pois


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf8')


def compile_run(args):
    started = time.perf_counter()
    root, output = Path(args.input), Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    states = population_frames(root/('regions.csv' if args.level == 'regions' else 'nodes.csv'),
                               'Region' if args.level == 'regions' else 'Node', args.day)
    nodes = read_table(root/'nodes.csv', ['Frame','Hour','Node','Total','Locals','Outsiders','dTotals','dLocals','dOutsiders'], optional=True)
    node_states = population_frames(root/'nodes.csv', 'Node', args.day) if nodes else None
    extra = extensions(root, args.day)
    demographic = priors(root/'output.txt')
    warnings = []
    if demographic['source'] == 'unavailable':
        demographic.update(age=[275,526,2806,1226], occupation=[2646,1042,1145],
                           source='User brief prior, N=4833; not measured for this run')
        warnings.append('Age/occupation use the supplied N=4,833 prior, not observed attributes for this run.')
    if not extra['diss']:
        warnings.append('diss.csv has no rows: functional weights use node changes when available.')
    if not extra['nodes_sir']:
        warnings.append('nodes_sir.csv has no rows: epidemiological layer unavailable.')
    if extra['node_positions']:
        warnings.append('node_positions contains allocation IDs; coordinates are resolved from the environment, never interpreted as latitude/longitude.')
    names = sorted(states[0])
    environments = json.loads(Path(args.environment).read_text(encoding='utf8'))['regions']
    region_names = {n.split('//')[0] for n in names}
    if node_states:
        region_names.update(n.split('//')[0] for n in node_states[0])
    env, pois = environment_index(environments, region_names)
    raw_geo = json.loads(Path(args.boundaries).read_text(encoding='utf8'))
    geoms = {}
    for feature in raw_geo['features']:
        geometry = shape(feature['geometry'])
        if not geometry.is_valid:
            warnings.append(f"Repaired invalid polygon topology: {feature['properties']['name']}")
            geometry = make_valid(geometry)
        if geometry.geom_type == 'GeometryCollection':
            geometry = unary_union([g for g in geometry.geoms if g.geom_type in ('Polygon','MultiPolygon')])
        geoms.setdefault(canonical(feature['properties']['name']), []).append(geometry)
    features, points, zone_points, arrows = [], {}, {}, []
    for name in sorted({n.split('//')[0] for n in names}):
        if canonical(name) not in geoms:
            raise ValueError(f'No official polygon matches {name}')
        geom = unary_union(geoms[canonical(name)])
        features.append({'type':'Feature','properties':{'name':name},'geometry':mapping(geom)})
        center = env[name]['lng_lat'] if name in env else list(geom.representative_point().coords)[0]
        zone_points[name] = center
        if args.level == 'regions':
            points[name] = center
        polys = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
        ring = max(polys, key=lambda p:p.area).exterior
        # Test the normal against the polygon; handles either ring winding.
        for f in np.linspace(.05,.95,8):
            a, b = ring.interpolate(max(0,f-.001), normalized=True), ring.interpolate(min(1,f+.001), normalized=True)
            anchor = ring.interpolate(f, normalized=True)
            longitude_scale = math.cos(math.radians(anchor.y))
            nx, ny = -(b.y-a.y), (b.x-a.x)*longitude_scale
            norm = math.hypot(nx,ny)
            if not norm:
                continue
            nx, ny = nx/norm*.0008/longitude_scale, ny/norm*.0008
            if not geom.contains(Point(anchor.x+nx, anchor.y+ny)):
                nx, ny = -nx,-ny
            arrows.append({'region':name,'outer':[anchor.x-nx,anchor.y-ny],
                           'inner':[anchor.x+nx,anchor.y+ny]})
    if args.level == 'nodes':
        for name in names:
            if name not in pois:
                raise ValueError(f'No geographic coordinate for node {name}; supply its environment mapping')
            points[name] = pois[name]
    venues = []
    if node_states:
        for name in node_states[0]:
            if 'stadium' in name.lower() and max(s[name]['Total'] for s in node_states) > 0:
                if name not in pois:
                    raise ValueError(f'Venue {name} has no coordinate')
                points[name] = pois[name]
                venues.append({'id':name,'name':'Arena do Grêmio' if name.startswith('Farrapos//') else name,
                               'region':name.split('//')[0], 'position':pois[name], 'capacity':None,
                               'hours':[s[name]['Total'] for s in node_states],
                               'locals':[s[name]['Locals'] for s in node_states]})
    interest_points = []
    if node_states:
        for name in node_states[0]:
            if name.split('//')[-1].startswith('home') or max(s[name]['Total'] for s in node_states) <= 0:
                continue
            if name not in pois:
                warnings.append(f'POI density unavailable for {name}: no environment coordinate.')
                continue
            venue = next((v for v in venues if v['id']==name),None)
            interest_points.append({'id':name,'name':venue['name'] if venue else name.replace('//',' · '),
                                    'region':name.split('//')[0],'position':pois[name],
                                    'hours':[s[name]['Total'] for s in node_states],
                                    'locals':[s[name]['Locals'] for s in node_states]})
    graph = load_graph(args.graph, args.mode)
    router = Router(graph, points, args.max_snap_m)
    route_list, route_indices, frame_data, reports, colocated_rows = [], {}, [], [], []
    for hour in range(24):
        print(f'Compiling hour {hour:02d}', flush=True)
        # Rows record incoming deltas. Hour 23 is the terminal observed state.
        target = min(hour+1,23)
        current, following = states[hour], states[target]
        endpoints = {name:name for name in names}
        if args.level == 'regions' and node_states:
            for venue in venues:
                node_delta = node_states[target][venue['id']]['dTotals']
                region_delta = following[venue['region']]['dTotals']
                if node_delta*region_delta > 0 and abs(node_delta) >= abs(region_delta)*.8:
                    endpoints[venue['region']] = venue['id']
        deltas = np.array([following[n]['dTotals'] if hour < 23 else 0 for n in names])
        costs = np.full((len(names),len(names)), np.inf)
        for i in np.flatnonzero(deltas < 0):
            for j in np.flatnonzero(deltas > 0):
                costs[i,j] = router.cost(endpoints[names[i]],endpoints[names[j]])
        matrix, report = estimate_od(deltas, costs, beta=args.beta, balance=args.balance)
        report.update(hour=hour, targetHour=target)
        reports.append(report)
        if abs(report['residual']) > 1e-5:
            warnings.append(f"Hour {target}: attraction scaled by {report['attraction_scale']:.6f}; residual {report['residual']:.3f}")
        trips = []
        colocated = 0.
        for i,j in zip(*np.where(matrix > 0)):
            origin, destination, mass = names[i], names[j], float(matrix[i,j])
            paths = router.route(endpoints[origin], endpoints[destination], args.k)
            if not paths:
                if router.snaps[endpoints[origin]] == router.snaps[endpoints[destination]]:
                    colocated += mass
                    colocated_rows.append([hour,target,origin,destination,'colocated',mass])
                    continue
                raise ValueError(f'No street route for nonzero OD {origin} -> {destination}')
            shares = np.exp(-np.array([p['duration'] for p in paths])*args.beta)
            shares /= shares.sum()
            source = current[origin]
            residency = source['Locals']/source['Total'] if source['Total'] else .5
            occ = np.array(demographic['occupation'],dtype=float)
            # Heuristic composition, not recovered demographic observations.
            work_gain = school_gain = 0.
            region = destination.split('//')[0]
            if node_states:
                work_gain = max(0,node_states[target].get(region+'//work',{}).get('dTotals',0))
                school_gain = max(0,node_states[target].get(region+'//school',{}).get('dTotals',0))
            allocations = [r for r in extra['diss'] if r['Neighbourhood']==region and r['Frame']%24 in [hour,target]]
            if len(allocations)==2:
                allocations.sort(key=lambda r:r['Frame'])
                work_gain = max(0,allocations[1]['work_total']-allocations[0]['work_total'])
            if '//work' in destination:
                work_gain = max(work_gain,mass)
            if '//school' in destination:
                school_gain = max(school_gain,mass)
            denominator = max(1,work_gain+school_gain)
            occ *= [1+3*work_gain/denominator,1+3*school_gain/denominator,1]
            occ /= occ.sum()
            for path, share in zip(paths,shares):
                if path['id'] not in route_indices:
                    route_indices[path['id']] = len(route_list)
                    route_list.append(path)
                trips.append({'origin':origin,'destination':destination,'route':route_indices[path['id']],
                              'mass':mass*float(share),'localFraction':residency,'occupation':occ.tolist()})
        report['colocatedMass'] = colocated
        frame_data.append({'hour':hour, 'zones':current, 'trips':trips,'report':report})
    if any(r['colocatedMass'] for r in reports):
        warnings.append('Some endpoints snap to the same street node: colocated mass is reported without fabricated paths.')
    source_files = [root/f for f in ['regions.csv','nodes.csv','diss.csv','nodes_sir.csv','node_positions.csv','output.txt'] if (root/f).exists()]
    meta = {'version':1,'createdAt':datetime.now(timezone.utc).isoformat(),'city':'Porto Alegre','run':root.name,'day':args.day,'level':args.level,
            'mode':args.mode,'k':args.k,'betaPerSecond':args.beta,'demographics':demographic,
            'warnings':warnings,'deltaConvention':'incoming','terminalHour':23,
            'inference':'Net-redistribution estimate; counterflows and within-zone trips are unidentifiable.',
            'graph':{'nodes':len(graph),'edges':graph.number_of_edges(),'source':'OpenStreetMap / OSMnx',
                     'sha256':hashlib.sha256(Path(args.graph).read_bytes()).hexdigest(),
                     'snapMeters':router.snap_distances},
            'sources':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in source_files},
            'buildSeconds':time.perf_counter()-started}
    meta['sources']['environment'] = hashlib.sha256(Path(args.environment).read_bytes()).hexdigest()
    meta['sources']['boundaries'] = hashlib.sha256(Path(args.boundaries).read_bytes()).hexdigest()
    # Interleaved float64 preserves geographic/timing precision while removing
    # repeated decimal strings. Each record is lon, lat, elapsed seconds, LE.
    packed = np.empty((sum(len(r['path']) for r in route_list),3),dtype='<f8')
    cursor = 0
    for route in route_list:
        size = len(route['path'])
        packed[cursor:cursor+size,:2] = route.pop('path')
        packed[cursor:cursor+size,2] = route.pop('seconds')
        route['offset'],route['vertices'] = cursor,size
        cursor += size
    packed.tofile(output/'routes.bin')
    meta['routeEncoding'] = {'file':'routes.bin','dtype':'float64-le','stride':3,'vertices':cursor}
    write_json(output/'run.json', {'meta':meta,'frames':frame_data,'routes':route_list,'venues':venues,'pois':interest_points,
                                  'zonePoints':zone_points,'boundaryVectors':arrows,'extensions':extra})
    write_json(output/'neighborhoods.geojson', {'type':'FeatureCollection','features':features})
    write_json(output/'roads.geojson',router.roads_geojson())
    write_json(output/'audit.json', {'meta':meta,'frames':reports})
    with (output/'od.csv').open('w',encoding='utf8',newline='') as f:
        writer = csv.writer(f); writer.writerow(['Hour','TargetHour','Origin','Destination','Route','EstimatedPeople'])
        for frame in frame_data:
            for trip in frame['trips']:
                writer.writerow([frame['hour'],min(23,frame['hour']+1),trip['origin'],trip['destination'],trip['route'],trip['mass']])
        writer.writerows(colocated_rows)
    print(f"Built {len(route_list)} OSM routes, {len(names)} entities in {time.perf_counter()-started:.1f}s", flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', default='../output_logs/WorkSchool94-StadiumPopulation')
    p.add_argument('--environment', default='../data_input/Environment-PortoAlegre94RegionsDefault.json')
    p.add_argument('--boundaries', default='../dialysis_clinics_viz/data/neighborhoods.geojson')
    p.add_argument('--graph', default='cache/porto-alegre-drive.graphml')
    p.add_argument('--output', default='public/data')
    p.add_argument('--day', type=int, default=0)
    p.add_argument('--level', choices=['regions','nodes'], default='regions')
    p.add_argument('--mode', choices=['drive','walk'], default='drive')
    p.add_argument('--k', type=int, default=1)
    p.add_argument('--max-snap-m', type=float, default=2500)
    p.add_argument('--beta', type=float, default=1/1800)
    p.add_argument('--balance', choices=['strict','normalize'], default='normalize')
    args = p.parse_args()
    if args.k < 1 or args.day < 0:
        p.error('k must be positive and day nonnegative')
    compile_run(args)


if __name__ == '__main__':
    main()
