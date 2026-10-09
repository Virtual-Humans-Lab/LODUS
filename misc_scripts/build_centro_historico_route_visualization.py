"""Build the standalone Centro Historico interactive route visualization."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from pyproj import CRS, Transformer

from validate_region_points import read_dbf, read_polygon_shapefile


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "docs" / "results" / "spatial_validation"
TABLE_CSV = DATA_DIR / "centro_historico_home_region_osrm_table.csv"
ROUTES_GEOJSON = DATA_DIR / "centro_historico_routes.geojson"
LEAFLET_CSS = DATA_DIR / "leaflet-1.9.4.css"
SECTORS_DIR = ROOT / "data_input" / "spatial" / "setores_2022"
OUTPUT_HTML = DATA_DIR / "centro-historico-route-explorer.html"


def main() -> None:
    with TABLE_CSV.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    routes = json.loads(ROUTES_GEOJSON.read_text(encoding="utf-8"))

    wanted_ids = {row["enumeration_area"] for row in rows}
    attributes = read_dbf(SECTORS_DIR / "setores_2022_poa.dbf")
    shapes = read_polygon_shapefile(SECTORS_DIR / "setores_2022_poa.shp")
    source_crs = CRS.from_wkt((SECTORS_DIR / "setores_2022_poa.prj").read_text())
    to_wgs84 = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)

    records_by_id = {row["enumeration_area"]: row for row in rows}
    sector_features = []
    for attributes_row, rings in zip(attributes, shapes):
        sector_id = attributes_row["CD_SETOR"]
        if sector_id not in wanted_ids:
            continue
        if len(rings) != 1:
            raise ValueError(f"Unexpected multipart sector {sector_id}: {len(rings)} rings")
        coordinates = [
            [round(lon, 6), round(lat, 6)]
            for lon, lat in (to_wgs84.transform(x, y) for x, y in rings[0])
        ]
        row = records_by_id[sector_id]
        sector_features.append(
            {
                "type": "Feature",
                "id": sector_id,
                "properties": {
                    "enumeration_area": sector_id,
                    "home_unique_name": row["home_unique_name"],
                    "home_to_region_distance_m": float(row["home_to_region_distance_m"]),
                    "home_to_region_duration_s": float(row["home_to_region_duration_s"]),
                    "region_to_home_distance_m": float(row["region_to_home_distance_m"]),
                    "region_to_home_duration_s": float(row["region_to_home_duration_s"]),
                    "home_to_region_route_id": row["home_to_region_route_id"],
                    "region_to_home_route_id": row["region_to_home_route_id"],
                },
                "geometry": {"type": "Polygon", "coordinates": [coordinates]},
            }
        )

    if len(sector_features) != len(rows):
        raise ValueError(
            f"Expected {len(rows)} sector features, found {len(sector_features)}"
        )

    compact_records = [
        {
            "id": row["enumeration_area"],
            "inDistance": float(row["home_to_region_distance_m"]),
            "outDistance": float(row["region_to_home_distance_m"]),
            "inDuration": float(row["home_to_region_duration_s"]),
            "outDuration": float(row["region_to_home_duration_s"]),
            "homeLon": float(row["home_longitude"]),
            "homeLat": float(row["home_latitude"]),
            "regionLon": float(row["region_longitude"]),
            "regionLat": float(row["region_latitude"]),
        }
        for row in rows
    ]
    sectors = {"type": "FeatureCollection", "features": sector_features}

    html = TEMPLATE.replace("__LEAFLET_CSS__", LEAFLET_CSS.read_text(encoding="utf-8")).replace(
        "__SECTORS_DATA__", json.dumps(sectors, ensure_ascii=False, separators=(",", ":"))
    ).replace(
        "__ROUTES_DATA__", json.dumps(routes, ensure_ascii=False, separators=(",", ":"))
    ).replace(
        "__RECORDS_DATA__",
        json.dumps(compact_records, ensure_ascii=False, separators=(",", ":")),
    )
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Sectors embedded: {len(sector_features)}")
    print(f"Routes embedded: {len(routes['features'])}")
    print(f"HTML: {OUTPUT_HTML}")


TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Centro Histórico Route Explorer</title>
  <style>__LEAFLET_CSS__</style>
  <style>
    :root {
      --bg: #f6f7f9; --surface: #ffffff; --text: #17212b; --muted: #607080;
      --border: #d8dee5; --sector: #3976a8; --sector-hover: #6ba6cf;
      --inbound: #1769aa; --outbound: #df6c21; --grid: #e5e9ee;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--text); font: 14px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; }
    header { padding: 18px 22px 10px; }
    h1 { margin: 0 0 4px; font-size: 23px; font-weight: 600; }
    header p { margin: 0; color: var(--muted); }
    main { display: grid; grid-template-columns: minmax(0, 1.7fr) minmax(320px, .8fr); gap: 16px; padding: 10px 18px 20px; }
    .map-wrap, .chart-panel { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
    #map { height: 720px; width: 100%; }
    .side { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
    #selection { padding: 13px 15px; min-height: 76px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; }
    #selection strong { display: block; margin-bottom: 5px; font-weight: 600; }
    #selection .metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 5px 14px; color: var(--muted); }
    #selection .metrics span { color: var(--text); font-variant-numeric: tabular-nums; }
    .chart-panel { padding: 12px 12px 8px; }
    .chart-panel h2 { margin: 0 0 4px; font-size: 15px; font-weight: 600; }
    .chart { height: 220px; width: 100%; }
    .chart-tabs { display: flex; gap: 4px; padding: 4px; background: var(--surface); border: 1px solid var(--border); border-radius: 9px; }
    .chart-tab { flex: 1; border: 0; border-radius: 6px; padding: 8px 10px; background: transparent; color: var(--muted); font: inherit; cursor: pointer; }
    .chart-tab[aria-selected="true"] { background: var(--text); color: var(--surface); }
    .chart-group { display: flex; flex-direction: column; gap: 16px; }
    .chart-group[hidden] { display: none; }
    .legend { display: flex; flex-wrap: wrap; gap: 12px; padding: 8px 12px; background: color-mix(in srgb, var(--surface) 92%, transparent); border-radius: 7px; }
    .legend-item { display: inline-flex; align-items: center; gap: 6px; }
    .line { width: 24px; height: 3px; display: inline-block; }
    .line.inbound { background: var(--inbound); }
    .line.outbound { background: var(--outbound); }
    .sector-swatch { width: 16px; height: 12px; background: color-mix(in srgb, var(--sector) 20%, transparent); border: 1px solid var(--sector); }
    .point-swatch { display: inline-block; border-radius: 50%; background: var(--text); border: 2px solid var(--surface); box-shadow: 0 0 0 1px var(--text); }
    .point-swatch.home { width: 10px; height: 10px; }
    .point-swatch.center { width: 15px; height: 15px; background: var(--outbound); box-shadow: 0 0 0 1px var(--outbound); }
    .leaflet-tooltip { font: 13px/1.4 system-ui, sans-serif; }
    .leaflet-container { background: #dce5eb; }
    .chart svg { width: 100%; height: 100%; display: block; overflow: visible; }
    .chart text { fill: var(--text); font-size: 11px; }
    .chart .axis path, .chart .axis line { stroke: var(--border); }
    .chart .grid line { stroke: var(--grid); }
    .chart .grid path { display: none; }
    .chart .axis-label { fill: var(--muted); font-size: 12px; }
    .chart rect.bar { opacity: .88; }
    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; }
      #map { height: 580px; }
      .side { display: flex; }
    }
    @media (max-width: 620px) {
      header { padding-inline: 12px; }
      main { padding-inline: 8px; }
      #map { height: 500px; }
      .side { display: flex; }
      #selection .metrics { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Centro Histórico home–region routes</h1>
    <p>Hover over a census sector to compare both directions. Click to keep a route pair visible.</p>
  </header>
  <main>
    <section class="map-wrap" aria-label="Interactive route map">
      <div id="map"></div>
    </section>
    <aside class="side">
      <section id="selection" aria-live="polite">
        <strong>95 enumeration areas</strong>
        <div class="metrics">Hover or click a sector to inspect its routes.</div>
      </section>
      <div class="chart-tabs" role="tablist" aria-label="Histogram measure">
        <button id="distance-tab" class="chart-tab" type="button" role="tab" aria-selected="true" aria-controls="distance-panel">Distance</button>
        <button id="time-tab" class="chart-tab" type="button" role="tab" aria-selected="false" aria-controls="time-panel">Travel time</button>
      </div>
      <div id="distance-panel" class="chart-group" role="tabpanel" aria-labelledby="distance-tab">
        <section class="chart-panel">
          <h2>Home → region distance</h2>
          <div id="hist-in" class="chart" role="img" aria-label="Histogram of home to region route distances"></div>
        </section>
        <section class="chart-panel">
          <h2>Region → home distance</h2>
          <div id="hist-out" class="chart" role="img" aria-label="Histogram of region to home route distances"></div>
        </section>
      </div>
      <div id="time-panel" class="chart-group" role="tabpanel" aria-labelledby="time-tab" hidden>
        <section class="chart-panel">
          <h2>Home → region travel time</h2>
          <div id="hist-time-in" class="chart" role="img" aria-label="Histogram of home to region travel times"></div>
        </section>
        <section class="chart-panel">
          <h2>Region → home travel time</h2>
          <div id="hist-time-out" class="chart" role="img" aria-label="Histogram of region to home travel times"></div>
        </section>
      </div>
    </aside>
  </main>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
  <script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
  <script>
    const sectors = __SECTORS_DATA__;
    const routes = __ROUTES_DATA__;
    const records = __RECORDS_DATA__;

    const css = getComputedStyle(document.documentElement);
    const colors = {
      sector: css.getPropertyValue('--sector').trim(),
      sectorHover: css.getPropertyValue('--sector-hover').trim(),
      inbound: css.getPropertyValue('--inbound').trim(),
      outbound: css.getPropertyValue('--outbound').trim(),
      text: css.getPropertyValue('--text').trim(),
      surface: css.getPropertyValue('--surface').trim()
    };
    const routeById = new Map(routes.features.map(feature => [feature.properties.route_id, feature]));
    const map = L.map('map', { preferCanvas: false, zoomControl: true });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);
    map.createPane('routes');
    map.getPane('routes').style.zIndex = 450;
    map.getPane('routes').style.pointerEvents = 'none';
    map.createPane('markers');
    map.getPane('markers').style.zIndex = 460;
    map.getPane('markers').style.pointerEvents = 'none';

    const selection = document.getElementById('selection');
    let activeRoutes = [];
    let pinnedLayer = null;

    function formatDistance(value) {
      return value >= 1000 ? `${(value / 1000).toFixed(2)} km` : `${value.toFixed(0)} m`;
    }
    function formatDuration(value) {
      const minutes = Math.floor(value / 60);
      const seconds = Math.round(value % 60);
      return `${minutes}m ${seconds.toString().padStart(2, '0')}s`;
    }
    function resetStyle(layer) {
      layer.setStyle({ color: colors.sector, weight: 1, fillColor: colors.sector, fillOpacity: .13 });
    }
    function clearRoutes() {
      activeRoutes.forEach(layer => map.removeLayer(layer));
      activeRoutes = [];
    }
    function closeSectorTooltip(layer) {
      if (layer.getTooltip()) layer.unbindTooltip();
      document.querySelectorAll('.leaflet-tooltip').forEach(node => node.remove());
    }
    function showFeature(feature, layer) {
      clearRoutes();
      layer.setStyle({ color: colors.sectorHover, weight: 2.5, fillColor: colors.sectorHover, fillOpacity: .32 });
      layer.bringToFront();
      const p = feature.properties;
      const inbound = L.geoJSON(routeById.get(p.home_to_region_route_id), {
        pane: 'routes', style: { color: colors.inbound, weight: 4, opacity: .92 }
      }).addTo(map);
      const outbound = L.geoJSON(routeById.get(p.region_to_home_route_id), {
        pane: 'routes', style: { color: colors.outbound, weight: 4, opacity: .88 }
      }).addTo(map);
      activeRoutes = [inbound, outbound];
      selection.innerHTML = `
        <strong>Enumeration area ${p.enumeration_area}</strong>
        <div class="metrics">
          <div>Home → region: <span>${formatDistance(p.home_to_region_distance_m)} · ${formatDuration(p.home_to_region_duration_s)}</span></div>
          <div>Region → home: <span>${formatDistance(p.region_to_home_distance_m)} · ${formatDuration(p.region_to_home_duration_s)}</span></div>
        </div>`;
    }

    const sectorLayer = L.geoJSON(sectors, {
      style: { color: colors.sector, weight: 1, fillColor: colors.sector, fillOpacity: .13 },
      onEachFeature(feature, layer) {
        const p = feature.properties;
        const tooltipContent =
          `<strong>${p.enumeration_area}</strong><br>` +
          `Home → region: ${formatDistance(p.home_to_region_distance_m)}<br>` +
          `Region → home: ${formatDistance(p.region_to_home_distance_m)}`;
        layer.on('mouseover', event => {
          if (pinnedLayer && pinnedLayer !== layer) return;
          if (!layer.getTooltip()) {
            layer.bindTooltip(tooltipContent, {
              sticky: false, interactive: false, direction: 'top', offset: [0, -6]
            });
          }
          layer.openTooltip(event.latlng);
          showFeature(feature, layer);
        });
        layer.on('mouseout', () => {
          closeSectorTooltip(layer);
          if (pinnedLayer) return;
          resetStyle(layer);
          clearRoutes();
        });
        layer.on('click', () => {
          if (pinnedLayer === layer) {
            pinnedLayer = null;
            resetStyle(layer);
            clearRoutes();
          } else {
            if (pinnedLayer) resetStyle(pinnedLayer);
            pinnedLayer = layer;
            showFeature(feature, layer);
          }
        });
      }
    }).addTo(map);
    map.fitBounds(sectorLayer.getBounds(), { padding: [18, 18] });

    records.forEach(record => {
      L.circleMarker([record.homeLat, record.homeLon], {
        pane: 'markers', interactive: false, radius: 4.6,
        color: colors.surface, weight: 1.5, fillColor: colors.text, fillOpacity: .95
      }).addTo(map);
    });
    const regionCenter = records[0];
    L.circleMarker([regionCenter.regionLat, regionCenter.regionLon], {
      pane: 'markers', interactive: false, radius: 9,
      color: colors.surface, weight: 2.4, fillColor: colors.outbound, fillOpacity: 1
    }).addTo(map);

    map.on('mouseout', () => {
      sectorLayer.eachLayer(closeSectorTooltip);
    });

    const legend = L.control({ position: 'bottomleft' });
    legend.onAdd = function () {
      const div = L.DomUtil.create('div', 'legend');
      div.innerHTML = `
        <span class="legend-item"><i class="sector-swatch"></i>Sector</span>
        <span class="legend-item"><i class="point-swatch home"></i>Home POI</span>
        <span class="legend-item"><i class="point-swatch center"></i>Region center</span>
        <span class="legend-item"><i class="line inbound"></i>Home → region</span>
        <span class="legend-item"><i class="line outbound"></i>Region → home</span>`;
      return div;
    };
    legend.addTo(map);

    const allDistances = records.flatMap(d => [d.inDistance, d.outDistance]).map(d => d / 1000);
    const maxDistance = d3.max(allDistances);
    const distanceThresholds = d3.range(0, maxDistance + .5, .5);
    const allDurations = records.flatMap(d => [d.inDuration, d.outDuration]).map(d => d / 60);
    const maxDuration = d3.max(allDurations);
    const durationThresholds = d3.range(0, Math.ceil(maxDuration) + 1, 1);

    function drawHistogram(containerId, accessor, color, maximum, thresholds, axisLabel, unit) {
      const container = document.getElementById(containerId);
      const width = Math.max(320, container.clientWidth);
      const height = container.clientHeight;
      const margin = { top: 10, right: 14, bottom: 46, left: 48 };
      const values = records.map(accessor);
      const bins = d3.bin().domain([0, maximum]).thresholds(thresholds)(values);
      const x = d3.scaleLinear().domain([0, maximum]).range([margin.left, width - margin.right]);
      const y = d3.scaleLinear().domain([0, d3.max(bins, d => d.length)]).nice().range([height - margin.bottom, margin.top]);
      container.replaceChildren();
      const svg = d3.select(container).append('svg').attr('viewBox', `0 0 ${width} ${height}`);
      svg.append('g').attr('class', 'grid').attr('transform', `translate(${margin.left},0)`)
        .call(d3.axisLeft(y).ticks(5).tickSize(-(width - margin.left - margin.right)).tickFormat(''));
      svg.selectAll('rect.bar').data(bins).join('rect')
        .attr('class', 'bar').attr('x', d => x(d.x0) + 1).attr('y', d => y(d.length))
        .attr('width', d => Math.max(0, x(d.x1) - x(d.x0) - 2))
        .attr('height', d => y(0) - y(d.length)).attr('fill', color)
        .append('title').text(d => `${d.x0.toFixed(1)}–${d.x1.toFixed(1)} ${unit}: ${d.length} sectors`);
      svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${height - margin.bottom})`)
        .call(d3.axisBottom(x).ticks(width < 380 ? 4 : 6));
      svg.append('g').attr('class', 'axis').attr('transform', `translate(${margin.left},0)`)
        .call(d3.axisLeft(y).ticks(5).tickFormat(d3.format('d')));
      svg.append('text').attr('class', 'axis-label').attr('x', (margin.left + width - margin.right) / 2)
        .attr('y', height - 8).attr('text-anchor', 'middle').text(axisLabel);
      svg.append('text').attr('class', 'axis-label').attr('transform', 'rotate(-90)')
        .attr('x', -(margin.top + height - margin.bottom) / 2).attr('y', 14)
        .attr('text-anchor', 'middle').text('Enumeration areas');
    }

    function drawAllHistograms() {
      drawHistogram('hist-in', d => d.inDistance / 1000, colors.inbound, maxDistance, distanceThresholds, 'Route distance (km)', 'km');
      drawHistogram('hist-out', d => d.outDistance / 1000, colors.outbound, maxDistance, distanceThresholds, 'Route distance (km)', 'km');
      drawHistogram('hist-time-in', d => d.inDuration / 60, colors.inbound, maxDuration, durationThresholds, 'Travel time (minutes)', 'min');
      drawHistogram('hist-time-out', d => d.outDuration / 60, colors.outbound, maxDuration, durationThresholds, 'Travel time (minutes)', 'min');
    }
    const distanceTab = document.getElementById('distance-tab');
    const timeTab = document.getElementById('time-tab');
    const distancePanel = document.getElementById('distance-panel');
    const timePanel = document.getElementById('time-panel');
    function selectChartTab(selected) {
      const showDistance = selected === 'distance';
      distanceTab.setAttribute('aria-selected', String(showDistance));
      timeTab.setAttribute('aria-selected', String(!showDistance));
      distancePanel.hidden = !showDistance;
      timePanel.hidden = showDistance;
      requestAnimationFrame(drawAllHistograms);
    }
    distanceTab.addEventListener('click', () => selectChartTab('distance'));
    timeTab.addEventListener('click', () => selectChartTab('time'));
    drawAllHistograms();
    new ResizeObserver(drawAllHistograms).observe(document.querySelector('.side'));
  </script>
</body>
</html>
'''


if __name__ == "__main__":
    main()
