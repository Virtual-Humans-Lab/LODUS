"""Build an interactive neighborhood travel-time explorer from the OSRM table."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

from pyproj import CRS, Transformer

from validate_region_points import normalized_name, read_dbf, read_polygon_shapefile


ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT = ROOT / "data_input" / "Environment-PortoAlegre94RegionsDefault.json"
TABLE_JSON = ROOT / "data_input" / "spatial" / "region_table_distances.json"
SHAPE_DIR = ROOT / "data_input" / "spatial" / "bairros_vigentes"
OUTPUT_DIR = ROOT / "docs" / "results" / "spatial_validation"
LEAFLET_CSS = OUTPUT_DIR / "leaflet-1.9.4.css"
OUTPUT_HTML = OUTPUT_DIR / "region-travel-time-explorer.html"

GEOMETRY_ALIASES = {
    "passodareia": "passodaareia",
    "saojose": "vilasaojose",
}


def point_line_distance(point, start, end):
    px, py = point
    ax, ay = start
    bx, by = end
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    fraction = max(
        0.0,
        min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)),
    )
    return math.hypot(px - (ax + fraction * dx), py - (ay + fraction * dy))


def rdp(points, tolerance):
    if len(points) <= 2:
        return points
    start, end = points[0], points[-1]
    distances = [point_line_distance(point, start, end) for point in points[1:-1]]
    if not distances or max(distances) <= tolerance:
        return [start, end]
    split = distances.index(max(distances)) + 1
    return rdp(points[: split + 1], tolerance)[:-1] + rdp(points[split:], tolerance)


def simplify_closed_ring(ring, tolerance=8.0):
    points = ring[:-1] if ring and ring[0] == ring[-1] else ring[:]
    if len(points) <= 4:
        return ring
    opposite = max(
        range(1, len(points)),
        key=lambda index: math.dist(points[0], points[index]),
    )
    first_half = rdp(points[: opposite + 1], tolerance)
    second_half = rdp(points[opposite:] + [points[0]], tolerance)
    simplified = first_half[:-1] + second_half
    if simplified[0] != simplified[-1]:
        simplified.append(simplified[0])
    return simplified if len(simplified) >= 4 else ring


def main() -> None:
    with ENVIRONMENT.open(encoding="utf-8") as handle:
        regions = json.load(handle)["regions"]
    with TABLE_JSON.open(encoding="utf-8") as handle:
        table = json.load(handle)

    attributes = read_dbf(SHAPE_DIR / "bairros_vigentes.dbf")
    shapes = read_polygon_shapefile(SHAPE_DIR / "bairros_vigentes.shp")
    shapes_by_name = defaultdict(list)
    for row, rings in zip(attributes, shapes):
        shapes_by_name[normalized_name(row["NOME"])].extend(rings)

    source_crs = CRS.from_wkt((SHAPE_DIR / "bairros_vigentes.prj").read_text())
    to_wgs84 = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
    geometry_features = []
    original_point_count = 0
    simplified_point_count = 0
    for region in regions:
        source_key = normalized_name(region["name"])
        geometry_key = GEOMETRY_ALIASES.get(source_key, source_key)
        rings = shapes_by_name.get(geometry_key)
        if not rings:
            raise ValueError(f"No neighborhood geometry for {region['name']!r}")
        polygons = []
        for ring in rings:
            original_point_count += len(ring)
            simplified = simplify_closed_ring(ring)
            simplified_point_count += len(simplified)
            polygons.append(
                [
                    [
                        [round(lon, 6), round(lat, 6)]
                        for lon, lat in (
                            to_wgs84.transform(x, y) for x, y in simplified
                        )
                    ]
                ]
            )
        geometry_features.append(
            {
                "type": "Feature",
                "id": region["name"],
                "properties": {
                    "name": region["name"],
                    "has_table_data": region["name"] in table,
                },
                "geometry": {"type": "MultiPolygon", "coordinates": polygons},
            }
        )

    routes = {
        origin: {
            entry["go_to"]: {
                "distance": entry["transport"][0]["distance"],
                "duration": entry["transport"][0]["duration"],
            }
            for entry in entries
        }
        for origin, entries in table.items()
    }
    payload = {
        "geometries": {
            "type": "FeatureCollection",
            "features": geometry_features,
        },
        "routes": routes,
    }
    html = TEMPLATE.replace(
        "__LEAFLET_CSS__", LEAFLET_CSS.read_text(encoding="utf-8")
    ).replace(
        "__DATA__", json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Neighborhoods embedded: {len(geometry_features)}")
    print(f"Origins with table data: {len(routes)}")
    print(f"Directed pairs embedded: {sum(len(values) for values in routes.values())}")
    print(f"Geometry points: {original_point_count} -> {simplified_point_count}")
    print(f"HTML: {OUTPUT_HTML}")


TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Porto Alegre Region Travel Explorer</title>
  <style>__LEAFLET_CSS__</style>
  <style>
    :root {
      --bg: #f5f7f9; --surface: #ffffff; --text: #17212b; --muted: #607080;
      --border: #d7dee5; --neutral: #dce4ea; --neutral-edge: #657482;
      --selected: #17212b; --no-data: #9aa5ae; --bar: #327aae; --grid: #e5e9ee;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--text); font: 14px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; }
    header { display: flex; align-items: end; justify-content: space-between; gap: 18px; padding: 17px 20px 10px; }
    h1 { margin: 0 0 3px; font-size: 23px; font-weight: 600; }
    header p { margin: 0; color: var(--muted); }
    #status { max-width: 48%; text-align: right; color: var(--muted); }
    #status strong { color: var(--text); font-weight: 600; }
    main {
      display: grid;
      grid-template-columns: minmax(0, 1.8fr) minmax(340px, 0.7fr);
      gap: 18px;
      align-items: start;
      padding: 8px 18px 22px;
    }
    #map { height: 680px; width: 100%; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; background: #dce5eb; }
    .charts { display: flex; flex-direction: column; gap: 18px; min-width: 0; }
    .chart-panel h2 { margin: 0 0 2px; font-size: 16px; font-weight: 600; }
    .chart-subtitle { color: var(--muted); margin-bottom: 4px; }
    .chart { height: 285px; width: 100%; }
    .chart svg { width: 100%; height: 100%; display: block; overflow: visible; }
    .chart text { fill: var(--text); font-size: 11px; }
    .chart .axis path, .chart .axis line { stroke: var(--border); }
    .chart .grid line { stroke: var(--grid); }
    .chart .grid path { display: none; }
    .chart .axis-label { fill: var(--muted); font-size: 12px; }
    .chart .frame { fill: var(--surface); stroke: var(--border); }
    .chart rect.bar { fill: var(--bar); opacity: .88; }
    .color-legend { min-width: 230px; padding: 9px 11px; background: var(--surface); border-radius: 7px; box-shadow: 0 1px 5px rgba(0,0,0,.18); }
    .color-legend strong { display: block; margin-bottom: 5px; font-weight: 600; }
    .gradient { height: 11px; border-radius: 2px; }
    .legend-labels { display: flex; justify-content: space-between; margin-top: 3px; font-size: 12px; }
    .no-data-key { display: flex; align-items: center; gap: 6px; margin-top: 5px; color: var(--muted); font-size: 12px; }
    .no-data-swatch { width: 13px; height: 11px; background: var(--no-data); }
    .leaflet-tooltip { font: 13px/1.45 system-ui, sans-serif; }
    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; }
      #map { height: 540px; }
      .charts { display: grid; grid-template-columns: 1fr 1fr; }
      .chart { height: 240px; }
    }
    @media (max-width: 620px) {
      header { align-items: start; flex-direction: column; }
      #status { max-width: none; text-align: left; }
      main { padding-inline: 8px; }
      #map { height: 500px; }
      .charts { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Porto Alegre regional travel</h1>
      <p>Click a neighborhood to color destinations by driving time. Click the map or press Esc to clear.</p>
    </div>
    <div id="status" aria-live="polite"><strong>All 8,556 directed pairs</strong><br>Histograms combine every available origin and destination.</div>
  </header>
  <main>
    <section id="map" aria-label="Interactive Porto Alegre neighborhood travel-time map"></section>
    <section class="charts">
      <div class="chart-panel">
        <h2>Driving distance</h2>
        <div id="distance-subtitle" class="chart-subtitle">All available region pairs</div>
        <div id="distance-chart" class="chart" role="img" aria-label="Histogram of driving distances"></div>
      </div>
      <div class="chart-panel">
        <h2>Travel time</h2>
        <div id="duration-subtitle" class="chart-subtitle">All available region pairs</div>
        <div id="duration-chart" class="chart" role="img" aria-label="Histogram of travel times"></div>
      </div>
    </section>
  </main>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
  <script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
  <script>
    const data = __DATA__;
    const allPairs = Object.entries(data.routes).flatMap(([origin, destinations]) =>
      Object.entries(destinations).map(([destination, values]) => ({origin, destination, ...values}))
    );
    const maxDurationMinutes = d3.max(allPairs, d => d.duration) / 60;
    const color = d3.scaleSequential(d3.interpolateYlOrRd).domain([0, maxDurationMinutes]);
    const map = L.map('map', {preferCanvas: false, zoomControl: true});
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    const status = document.getElementById('status');
    const neutral = getComputedStyle(document.documentElement).getPropertyValue('--neutral').trim();
    const neutralEdge = getComputedStyle(document.documentElement).getPropertyValue('--neutral-edge').trim();
    const selectedColor = getComputedStyle(document.documentElement).getPropertyValue('--selected').trim();
    const noData = getComputedStyle(document.documentElement).getPropertyValue('--no-data').trim();
    let selectedOrigin = null;
    let layerByName = new Map();

    function valuesFor(origin, destination) {
      return data.routes[origin]?.[destination] || null;
    }
    function formatDistance(meters) {
      return meters >= 1000 ? `${(meters / 1000).toFixed(1)} km` : `${meters.toFixed(0)} m`;
    }
    function formatDuration(seconds) {
      const minutes = Math.round(seconds / 60);
      return minutes >= 60 ? `${Math.floor(minutes / 60)}h ${minutes % 60}m` : `${minutes} min`;
    }
    function styleRegion(feature) {
      const name = feature.properties.name;
      if (!selectedOrigin) {
        return {color: neutralEdge, weight: 1, fillColor: neutral, fillOpacity: .52};
      }
      if (name === selectedOrigin) {
        return {color: selectedColor, weight: 3, fillColor: color(0), fillOpacity: .82};
      }
      const values = valuesFor(selectedOrigin, name);
      if (!values) {
        return {color: neutralEdge, weight: 1, fillColor: noData, fillOpacity: .58};
      }
      return {color: neutralEdge, weight: 1, fillColor: color(values.duration / 60), fillOpacity: .82};
    }
    function tooltipContent(name) {
      if (!selectedOrigin) {
        return `<strong>${name}</strong><br>${data.routes[name] ? 'Click to select origin' : 'No stored table data'}`;
      }
      if (name === selectedOrigin) return `<strong>${name}</strong><br>Selected origin`;
      const values = valuesFor(selectedOrigin, name);
      if (!values) return `<strong>${name}</strong><br>No stored route from ${selectedOrigin}`;
      return `<strong>${selectedOrigin} → ${name}</strong><br>${formatDuration(values.duration)} · ${formatDistance(values.distance)}`;
    }
    function removeTooltips() {
      document.querySelectorAll('.leaflet-tooltip').forEach(node => node.remove());
    }
    function refreshMapStyles() {
      regionLayer.eachLayer(layer => layer.setStyle(styleRegion(layer.feature)));
    }
    function selectRegion(name) {
      if (!data.routes[name]) {
        clearSelection();
        status.innerHTML = `<strong>${name} has no table data</strong><br>Anchieta is missing as both origin and destination.`;
        return;
      }
      selectedOrigin = name;
      refreshMapStyles();
      const pairs = Object.entries(data.routes[name]).map(([destination, values]) => ({origin: name, destination, ...values}));
      status.innerHTML = `<strong>${name} selected</strong><br>${pairs.length} outbound destinations · colors show driving time`;
      document.getElementById('distance-subtitle').textContent = `${name} → all available destinations`;
      document.getElementById('duration-subtitle').textContent = `${name} → all available destinations`;
      drawHistograms(pairs);
    }
    function clearSelection() {
      selectedOrigin = null;
      refreshMapStyles();
      removeTooltips();
      status.innerHTML = `<strong>All ${allPairs.length.toLocaleString()} directed pairs</strong><br>Histograms combine every available origin and destination.`;
      document.getElementById('distance-subtitle').textContent = 'All available region pairs';
      document.getElementById('duration-subtitle').textContent = 'All available region pairs';
      drawHistograms(allPairs);
    }

    const regionLayer = L.geoJSON(data.geometries, {
      style: styleRegion,
      onEachFeature(feature, layer) {
        const name = feature.properties.name;
        layerByName.set(name, layer);
        layer.on('mouseover', event => {
          layer.setTooltipContent?.(tooltipContent(name));
          if (!layer.getTooltip()) {
            layer.bindTooltip(tooltipContent(name), {sticky: false, interactive: false, direction: 'top'});
          } else {
            layer.setTooltipContent(tooltipContent(name));
          }
          layer.openTooltip(event.latlng);
          layer.setStyle({...styleRegion(feature), weight: name === selectedOrigin ? 3.5 : 2.3});
          layer.bringToFront();
        });
        layer.on('mouseout', () => {
          if (layer.getTooltip()) layer.unbindTooltip();
          removeTooltips();
          layer.setStyle(styleRegion(feature));
        });
        layer.on('click', event => {
          L.DomEvent.stopPropagation(event);
          selectedOrigin === name ? clearSelection() : selectRegion(name);
        });
      }
    }).addTo(map);
    map.fitBounds(regionLayer.getBounds(), {padding: [16, 16]});
    map.on('click', clearSelection);
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') clearSelection();
    });

    const legend = L.control({position: 'bottomright'});
    legend.onAdd = function () {
      const div = L.DomUtil.create('div', 'color-legend');
      const stops = d3.range(0, 1.01, .1).map(t => color(t * maxDurationMinutes));
      div.innerHTML = `<strong>Driving time</strong>
        <div class="gradient" style="background:linear-gradient(90deg,${stops.join(',')})"></div>
        <div class="legend-labels"><span>0 min</span><span>${Math.ceil(maxDurationMinutes)} min</span></div>
        <div class="no-data-key"><i class="no-data-swatch"></i>No route data</div>`;
      L.DomEvent.disableClickPropagation(div);
      return div;
    };
    legend.addTo(map);

    function drawHistogram(containerId, pairs, accessor, unit, axisLabel) {
      const container = document.getElementById(containerId);
      const width = Math.max(320, container.clientWidth);
      const height = container.clientHeight;
      const margin = {top: 10, right: 14, bottom: 47, left: 58};
      const values = pairs.map(accessor);
      const extent = d3.extent(values);
      const upper = extent[1] || 1;
      const x = d3.scaleLinear().domain([0, upper * 1.03]).nice().range([margin.left, width - margin.right]);
      const bins = d3.bin().domain(x.domain()).thresholds(18)(values);
      const y = d3.scaleLinear().domain([0, d3.max(bins, d => d.length) || 1]).nice().range([height - margin.bottom, margin.top]);
      container.replaceChildren();
      const svg = d3.select(container).append('svg').attr('viewBox', `0 0 ${width} ${height}`);
      svg.append('title').text(`${axisLabel} distribution for ${pairs.length} directed region pairs`);
      svg.append('rect').attr('class', 'frame').attr('x', margin.left).attr('y', margin.top)
        .attr('width', width - margin.left - margin.right).attr('height', height - margin.top - margin.bottom);
      svg.append('g').attr('class', 'grid').attr('transform', `translate(${margin.left},0)`)
        .call(d3.axisLeft(y).ticks(5).tickSize(-(width - margin.left - margin.right)).tickFormat(''));
      svg.selectAll('rect.bar').data(bins).join('rect').attr('class', 'bar')
        .attr('x', d => x(d.x0) + 1).attr('y', d => y(d.length))
        .attr('width', d => Math.max(0, x(d.x1) - x(d.x0) - 2)).attr('height', d => y(0) - y(d.length))
        .append('title').text(d => `${d.x0.toFixed(1)}–${d.x1.toFixed(1)} ${unit}: ${d.length} pairs`);
      svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${height - margin.bottom})`)
        .call(d3.axisBottom(x).ticks(width < 500 ? 5 : 7));
      svg.append('g').attr('class', 'axis').attr('transform', `translate(${margin.left},0)`)
        .call(d3.axisLeft(y).ticks(5).tickFormat(d3.format('d')));
      svg.append('text').attr('class', 'axis-label').attr('x', (margin.left + width - margin.right) / 2)
        .attr('y', height - 8).attr('text-anchor', 'middle').text(`${axisLabel} (${unit})`);
      svg.append('text').attr('class', 'axis-label').attr('transform', 'rotate(-90)')
        .attr('x', -(margin.top + height - margin.bottom) / 2).attr('y', 15)
        .attr('text-anchor', 'middle').text('Directed region pairs');
    }
    let currentPairs = allPairs;
    function drawHistograms(pairs) {
      currentPairs = pairs;
      drawHistogram('distance-chart', pairs, d => d.distance / 1000, 'km', 'Driving distance');
      drawHistogram('duration-chart', pairs, d => d.duration / 60, 'min', 'Travel time');
    }
    drawHistograms(allPairs);
    new ResizeObserver(() => drawHistograms(currentPairs)).observe(document.querySelector('.charts'));
  </script>
</body>
</html>
'''


if __name__ == "__main__":
    main()
