"""Strict CSV ingestion for current LODUS and comma-delimited exports."""
import csv
import math
import re
from pathlib import Path

POPULATION = ['Total', 'Locals', 'Outsiders', 'dTotals', 'dLocals', 'dOutsiders']
AGE = ['Children', 'Youngs', 'Adults', 'Elders']
OCCUPATION = ['Worker', 'Student', 'Other']


def read_table(path, required, optional=False):
    path = Path(path)
    if not path.exists():
        if optional:
            return []
        raise ValueError(f"Missing required file: {path}")
    with path.open(encoding='utf-8-sig', newline='') as handle:
        sample = handle.read(4096)
        handle.seek(0)
        if not sample.strip():
            if optional:
                return []
            raise ValueError(f'{path.name}: empty file')
        delimiter = ';' if sample.splitlines()[0].count(';') > sample.splitlines()[0].count(',') else ','
        reader = csv.DictReader(handle, delimiter=delimiter)
        missing = set(required)-set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
        return [{k: v.strip() for k, v in row.items() if k and v is not None}
                for row in reader if any(row.values())]


def number(row, key):
    try:
        value = float(row[key])
    except (KeyError, ValueError) as error:
        raise ValueError(f"Invalid {key}: {row.get(key)!r}") from error
    if not math.isfinite(value):
        raise ValueError(f"Non-finite {key}")
    return value


def population_frames(path, entity, day=0):
    rows = read_table(path, ['Frame', 'Hour', entity, *POPULATION])
    frames = [dict() for _ in range(24)]
    for row in rows:
        frame, hour = number(row, 'Frame'), number(row, 'Hour')
        if frame != int(frame) or hour != int(hour) or frame < 0 or not 0 <= hour < 24:
            raise ValueError("Frame/Hour must be nonnegative integers; Hour in [0,23]")
        row_day = number(row, 'Day') if 'Day' in row else int(frame)//24
        if row_day != int(row_day) or row_day != int(frame)//24 or int(hour) != int(frame)%24:
            raise ValueError("Frame, Hour and Day disagree")
        if row_day != day:
            continue
        name = row[entity]
        if not name or name in frames[int(hour)]:
            raise ValueError(f"Duplicate/empty {entity} at hour {hour}: {name}")
        values = {key: number(row, key) for key in POPULATION}
        if any(values[k] < 0 for k in ['Total', 'Locals', 'Outsiders']):
            raise ValueError("Negative population")
        if abs(values['Total']-values['Locals']-values['Outsiders']) > 1e-5:
            raise ValueError("Total != Locals + Outsiders")
        if abs(values['dTotals']-values['dLocals']-values['dOutsiders']) > 1e-5:
            raise ValueError("dTotals != dLocals + dOutsiders")
        frames[int(hour)][name] = values
    names = set(frames[0])
    if not names or any(set(f) != names for f in frames):
        raise ValueError("Run must contain the same entities in all 24 hours")
    for hour in range(1, 24):
        for name in names:
            for total, delta in [('Total','dTotals'),('Locals','dLocals'),('Outsiders','dOutsiders')]:
                if abs(frames[hour][name][total]-frames[hour-1][name][total]-frames[hour][name][delta]) > 1e-5:
                    raise ValueError(f"{name} hour {hour}: {delta} disagrees with adjacent states")
    return frames


def priors(path):
    text = Path(path).read_text(encoding='utf-8-sig') if Path(path).exists() else ''
    groups = []
    for labels in (AGE, OCCUPATION):
        counts = [re.search(rf'(?m)^\s*{name}\s*:\s*([\d,]+)\s*$', text) for name in labels]
        if all(counts):
            numbers = [int(c[1].replace(',', '')) for c in counts]
            if sum(numbers) <= 0:
                raise ValueError("Demographic prior is empty")
            groups.append(numbers)
        else:
            groups.append(None)
    if all(groups) and sum(groups[0]) != sum(groups[1]):
        raise ValueError("Age and occupation prior totals disagree")
    return {'age': groups[0], 'occupation': groups[1],
            'source': 'output.txt' if all(groups) else 'unavailable',
            'plugins': sorted(set(re.findall(r'\b(?:move_population|gather_population|send_population_back|levy_walk)\b', text)))}


def extensions(directory, day=0):
    root = Path(directory)
    result = {}
    schemas = {
        'diss': ['Frame', 'Hour', 'Neighbourhood', 'Total','Locals','Outsiders',
                 'home_total','home_locals','home_outsiders','work_total','work_locals','work_outsiders'],
        'node_positions': ['ID','RegionPosition','NodeImagePosition','Quantity'],
        'nodes_sir': ['Frame','NHLat','NHLong','InnerLat','InnerLong',
                      'Susceptible','Infected','Removed','Vaccinated','dS','dI','dR','dV'],
    }
    for name, columns in schemas.items():
        rows = read_table(root/f'{name}.csv', columns, optional=True)
        selected = []
        seen = set()
        for row in rows:
            if 'Frame' in row:
                frame = number(row, 'Frame')
                if frame != int(frame) or frame < 0:
                    raise ValueError(f'{name}: invalid frame')
                if int(frame)//24 != day:
                    continue
            numeric = [k for k in columns if k not in ['Neighbourhood','ID','RegionPosition','NodeImagePosition']]
            for key in numeric:
                row[key] = number(row, key)
            if name == 'diss':
                key = (row['Frame'],row['Neighbourhood'])
                if key in seen or row['Hour'] != row['Frame'] % 24:
                    raise ValueError('diss: duplicate or inconsistent frame')
                seen.add(key)
                for prefix in ('', 'home_', 'work_'):
                    keys = ('Total','Locals','Outsiders') if not prefix else tuple(prefix+x for x in ('total','locals','outsiders'))
                    if min(row[k] for k in keys) < 0 or abs(row[keys[0]]-row[keys[1]]-row[keys[2]]) > 1e-5:
                        raise ValueError('diss: invalid population allocation')
            if name == 'nodes_sir':
                for lat, lon in [('NHLat','NHLong'),('InnerLat','InnerLong')]:
                    if not -90 <= row[lat] <= 90 or not -180 <= row[lon] <= 180:
                        raise ValueError('SIR: invalid geographic coordinates')
                if min(row[k] for k in ['Susceptible','Infected','Removed','Vaccinated']) < 0:
                    raise ValueError('SIR: negative compartment')
            if name == 'node_positions' and row['Quantity'] < 0:
                raise ValueError('node_positions: negative quantity')
            selected.append(row)
        result[name] = selected
    return result
