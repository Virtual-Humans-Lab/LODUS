const DATA_ROOT = "./data";
const svg = document.querySelector("#network-map");
const tooltip = document.querySelector("#tooltip");
const detail = document.querySelector("#clinic-detail");
const empty = document.querySelector("#empty-state");
const clearButton = document.querySelector("#clear-button");
let currentVersion = "full";
let selectedClinic = null;
let model = null;
let mapScale = 1;
let mapX = 0;
let mapY = 0;
let dragStart = null;

const copy = {
  full: {
    kicker: "Complete environment",
    title: "The city's dialysis safety net,<br>from source to care.",
    description: "All modeled clinics, water treatment stations, and service neighborhoods across the complete Porto Alegre environment."
  },
  13: {
    kicker: "Focused environment · 13 neighborhoods",
    title: "A closer view of the<br>central care corridor.",
    description: "A compact scenario centered on 13 neighborhoods, with a reduced set of clinics and the two water sources they rely on."
  }
};

function fixText(value = "") {
  if (!/[ÃÂ]/.test(value)) return value;
  try {
    const bytes = Uint8Array.from([...value].map(char => char.charCodeAt(0)));
    return new TextDecoder("utf-8").decode(bytes);
  } catch {
    return value;
  }
}

function normalizeName(value = "") {
  return fixText(value).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

const focusedNames = new Set([
  "Azenha", "Bom Fim", "Centro Histórico", "Cidade Baixa", "Farroupilha",
  "Floresta", "Independência", "Menino Deus", "Moinhos de Vento",
  "Praia de Belas", "Rio Branco", "Santa Cecília", "Santana"
].map(normalizeName));

async function loadModel(version) {
  const suffix = version === "13" ? "-13" : "";
  const [clinicData, etaData, etaCsv, boundaryData] = await Promise.all([
    fetch(`${DATA_ROOT}/Environment-Clinics${suffix}.json`).then(r => r.json()),
    fetch(`${DATA_ROOT}/Environment-ETAs${suffix}.json`).then(r => r.json()),
    fetch(`${DATA_ROOT}/etas.csv`).then(r => r.text()),
    fetch(`${DATA_ROOT}/neighborhoods.geojson`).then(r => r.json())
  ]);

  const coverage = parseCoverage(etaCsv);
  const clinics = clinicData.regions.flatMap((region, regionIndex) =>
    (region.points_of_interest || []).map((poi, poiIndex) => ({
      id: `c-${regionIndex}-${poiIndex}`,
      name: fixText(poi.attributes.clinic_name),
      neighborhood: fixText(region.name),
      coord: poi.lng_lat,
      waterLevel: poi.attributes.water_level,
      sources: poi.attributes.water_source.map(fixText)
    }))
  );
  const waters = etaData.regions.flatMap((region, regionIndex) =>
    (region.points_of_interest || []).map((poi, poiIndex) => ({
      id: `w-${regionIndex}-${poiIndex}`,
      name: fixText(poi.attributes.eta_name),
      neighborhood: fixText(region.name),
      coord: poi.lng_lat,
      waterLevel: poi.attributes.water_level
    }))
  );
  const neighborhoods = boundaryData.features
    .map(feature => ({
      ...feature,
      properties: { ...feature.properties, name: fixText(feature.properties.name) }
    }))
    .filter(feature => version !== "13" || focusedNames.has(normalizeName(feature.properties.name)));
  return { clinics, waters, neighborhoods, coverage };
}

function parseCoverage(csv) {
  const result = {};
  csv.split(/\r?\n/).slice(1).forEach(line => {
    if (!line.trim()) return;
    const name = fixText(line.split(";")[0].trim());
    const match = line.match(/;"(\[[\s\S]*\])"\s*$/);
    if (!match) return;
    result[name] = [...match[1].matchAll(/'([^']+)'/g)].map(m => fixText(m[1].trim()));
  });
  return result;
}

function geometryPoints(geometry) {
  const points = [];
  const walk = value => {
    if (typeof value[0] === "number") points.push(value);
    else value.forEach(walk);
  };
  walk(geometry.coordinates);
  return points;
}

function projectFactory(coords, width, height) {
  const xs = coords.map(c => c[0]);
  const ys = coords.map(c => c[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const padX = 38, padY = 28;
  const scale = Math.min((width - padX * 2) / (maxX - minX || 1), (height - padY * 2) / (maxY - minY || 1));
  const drawnWidth = (maxX - minX) * scale;
  const drawnHeight = (maxY - minY) * scale;
  const offsetX = (width - drawnWidth) / 2;
  const offsetY = (height - drawnHeight) / 2;
  return ([lng, lat]) => [
    offsetX + (lng - minX) * scale,
    height - offsetY - (lat - minY) * scale
  ];
}

function polygonPath(geometry, project) {
  const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
  return polygons.flatMap(polygon => polygon).map(ring =>
    ring.map((point, index) => {
      const [x, y] = project(point);
      return `${index ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ") + " Z"
  ).join(" ");
}

function featureCenter(feature) {
  const points = geometryPoints(feature.geometry);
  return [
    points.reduce((sum, point) => sum + point[0], 0) / points.length,
    points.reduce((sum, point) => sum + point[1], 0) / points.length
  ];
}

function el(tag, attrs = {}, parent = svg) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attrs).forEach(([key, val]) => node.setAttribute(key, val));
  parent.appendChild(node);
  return node;
}

function render() {
  const width = svg.clientWidth || 900;
  const height = svg.clientHeight || 503;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.replaceChildren();
  const coords = [
    ...model.neighborhoods.flatMap(feature => geometryPoints(feature.geometry)),
    ...model.clinics.map(item => item.coord),
    ...model.waters.map(item => item.coord)
  ];
  const project = projectFactory(coords, width, height);

  const viewport = el("g", { id: "map-viewport" });
  const regions = el("g", { class: "regions" }, viewport);
  model.neighborhoods.forEach(region => {
    const name = region.properties.name;
    const path = el("path", {
      d: polygonPath(region.geometry, project),
      class: "neighborhood-shape",
      "data-region": normalizeName(name)
    }, regions);
    bindTooltip(path, `<b>${name}</b><br>Neighborhood`);
    if (currentVersion === "13") {
      const [x, y] = project(featureCenter(region));
      const label = el("text", { x, y, class: "region-label" }, regions);
      label.textContent = name;
    }
  });

  const links = el("g", { class: "links" }, viewport);
  model.clinics.forEach(clinic => {
    clinic.sources.forEach(sourceName => {
      const water = model.waters.find(item => item.name === sourceName);
      if (!water) return;
      const [x1, y1] = project(clinic.coord);
      const [x2, y2] = project(water.coord);
      el("line", { x1, y1, x2, y2, class: "connection", "data-clinic": clinic.id }, links);
    });
  });

  const waterGroup = el("g", {}, viewport);
  model.waters.forEach(water => {
    const [x, y] = project(water.coord);
    const group = el("g", {
      class: "water-node", tabindex: "0", role: "button",
      "aria-label": water.name, "data-name": water.name,
      transform: `translate(${x} ${y})`
    }, waterGroup);
    const visual = el("g", { class: "marker-visual" }, group);
    el("rect", { x: -7, y: -7, width: 14, height: 14, rx: 2, class: "water-shape", transform: "rotate(45)" }, visual);
    const label = el("text", { x: 13, y: 3, class: "water-label" }, visual);
    label.textContent = water.name.replace("ETA ", "");
    group.addEventListener("mouseenter", () => selectWater(water));
    group.addEventListener("focus", () => selectWater(water));
    group.addEventListener("click", () => selectWater(water));
    bindTooltip(group, `<b>${water.name}</b><br>${water.neighborhood}<br>Safe up to ${water.waterLevel} m`);
  });

  const clinicGroup = el("g", {}, viewport);
  model.clinics.forEach(clinic => {
    const [x, y] = project(clinic.coord);
    const group = el("g", {
      class: "clinic-node", tabindex: "0", role: "button",
      "aria-label": clinic.name, "data-id": clinic.id,
      transform: `translate(${x} ${y})`
    }, clinicGroup);
    const visual = el("g", { class: "marker-visual" }, group);
    el("circle", { r: 9, class: "clinic-ring" }, visual);
    el("circle", { r: 4, class: "clinic-dot" }, visual);
    if (currentVersion === "13") {
      const label = el("text", { x: 13, y: 3, class: "node-label" }, visual);
      label.textContent = clinic.name.length > 26 ? `${clinic.name.slice(0, 24)}…` : clinic.name;
    }
    group.addEventListener("mouseenter", () => selectClinic(clinic));
    group.addEventListener("focus", () => selectClinic(clinic));
    group.addEventListener("click", () => selectClinic(clinic));
    bindTooltip(group, `<b>${clinic.name}</b><br>${clinic.neighborhood}`);
  });
  applyMapTransform();
  updateStats();
}

function bindTooltip(node, html) {
  node.addEventListener("mousemove", event => {
    tooltip.innerHTML = html;
    tooltip.hidden = false;
    tooltip.style.left = `${event.clientX + 14}px`;
    tooltip.style.top = `${event.clientY + 14}px`;
  });
  node.addEventListener("mouseleave", () => {
    tooltip.hidden = true;
  });
}

function selectClinic(clinic) {
  selectedClinic = clinic;
  document.querySelectorAll(".neighborhood-shape").forEach(node => node.classList.remove("covered"));
  document.querySelectorAll(".clinic-node").forEach(node => {
    node.classList.toggle("active", node.dataset.id === clinic.id);
    node.classList.toggle("dimmed", node.dataset.id !== clinic.id);
  });
  document.querySelectorAll(".water-node").forEach(node => {
    node.classList.remove("active");
    node.classList.toggle("dimmed", !clinic.sources.includes(node.dataset.name));
  });
  document.querySelectorAll(".connection").forEach(node => {
    node.classList.toggle("active", node.dataset.clinic === clinic.id);
  });
  empty.hidden = true;
  detail.hidden = false;
  clearButton.hidden = false;
  document.querySelector("#detail-type").textContent = "CLINIC";
  document.querySelector("#detail-neighborhood").textContent = clinic.neighborhood;
  document.querySelector("#detail-name").textContent = clinic.name;
  document.querySelector("#detail-level").textContent =
    clinic.waterLevel == null ? "Not available" : `Safe up to ${clinic.waterLevel} m`;
  document.querySelector("#detail-meter").style.width = `${Math.min(100, (clinic.waterLevel || 0) * 10)}%`;
  document.querySelector("#detail-list-label").textContent = "DEPENDENT SOURCES";
  document.querySelector("#detail-sources").innerHTML = clinic.sources
    .map(source => `<div class="source-item"><i></i>${source}</div>`).join("");
  document.querySelector("#coverage-section").hidden = true;
}

function selectWater(water) {
  selectedClinic = null;
  const environmentNames = new Set(model.neighborhoods.map(item => normalizeName(item.properties.name)));
  const covered = [...new Set(model.coverage[water.name] || [])]
    .filter(name => environmentNames.has(normalizeName(name)))
    .sort();
  const coveredKeys = new Set(covered.map(normalizeName));
  document.querySelectorAll(".neighborhood-shape").forEach(node => {
    node.classList.toggle("covered", coveredKeys.has(node.dataset.region));
  });
  document.querySelectorAll(".clinic-node").forEach(node => node.classList.remove("active", "dimmed"));
  document.querySelectorAll(".connection").forEach(node => node.classList.remove("active"));
  document.querySelectorAll(".water-node").forEach(node => {
    node.classList.toggle("active", node.dataset.name === water.name);
    node.classList.toggle("dimmed", node.dataset.name !== water.name);
  });
  empty.hidden = true;
  detail.hidden = false;
  clearButton.hidden = false;
  document.querySelector("#detail-type").textContent = "WATER SOURCE";
  document.querySelector("#detail-neighborhood").textContent = water.neighborhood;
  document.querySelector("#detail-name").textContent = water.name;
  document.querySelector("#detail-level").textContent =
    water.waterLevel == null ? "Not available" : `Safe up to ${water.waterLevel} m`;
  document.querySelector("#detail-meter").style.width = `${Math.min(100, (water.waterLevel || 0) * 10)}%`;
  document.querySelector("#detail-list-label").textContent = "SOURCE TYPE";
  document.querySelector("#detail-sources").innerHTML = `<div class="source-item"><i></i>Water treatment station</div>`;
  document.querySelector("#coverage-section").hidden = false;
  document.querySelector("#coverage-count").textContent = covered.length;
  document.querySelector("#detail-coverage").innerHTML = covered.map(name => `<span>${name}</span>`).join("");
}

function clearSelection() {
  selectedClinic = null;
  document.querySelectorAll(".dimmed, .active, .covered").forEach(node => {
    node.classList.remove("dimmed", "active", "covered");
  });
  empty.hidden = false;
  detail.hidden = true;
  clearButton.hidden = true;
}

function applyMapTransform() {
  const viewport = document.querySelector("#map-viewport");
  if (viewport) viewport.setAttribute("transform", `translate(${mapX} ${mapY}) scale(${mapScale})`);
  document.querySelectorAll(".marker-visual").forEach(marker => {
    marker.setAttribute("transform", `scale(${1 / mapScale})`);
  });
}

function zoomMap(factor, centerX = svg.clientWidth / 2, centerY = svg.clientHeight / 2) {
  const nextScale = Math.min(8, Math.max(1, mapScale * factor));
  if (nextScale === mapScale) return;
  const ratio = nextScale / mapScale;
  mapX = centerX - (centerX - mapX) * ratio;
  mapY = centerY - (centerY - mapY) * ratio;
  mapScale = nextScale;
  applyMapTransform();
}

function resetMapView() {
  mapScale = 1;
  mapX = 0;
  mapY = 0;
  applyMapTransform();
}

function updateStats() {
  const environmentNames = new Set(model.neighborhoods.map(item => normalizeName(item.properties.name)));
  const coveredCount = new Set(
    model.waters
      .flatMap(water => model.coverage[water.name] || [])
      .map(normalizeName)
      .filter(name => environmentNames.has(name))
  ).size;
  document.querySelector("#stats").innerHTML =
    `<span><strong>${model.clinics.length}</strong> CLINICS</span>` +
    `<span><strong>${model.waters.length}</strong> SOURCES</span>` +
    `<span><strong>${coveredCount}</strong> SERVICE AREAS</span>`;
}

async function switchVersion(version) {
  currentVersion = version;
  document.querySelectorAll(".view-button").forEach(button => {
    button.classList.toggle("active", button.dataset.version === version);
  });
  document.querySelector("#view-kicker").textContent = copy[version].kicker;
  document.querySelector("#view-title").innerHTML = copy[version].title;
  document.querySelector("#view-description").textContent = copy[version].description;
  clearSelection();
  resetMapView();
  model = await loadModel(version);
  render();
}

document.querySelectorAll(".view-button").forEach(button => {
  button.addEventListener("click", () => switchVersion(button.dataset.version));
});
clearButton.addEventListener("click", clearSelection);
document.querySelector("#zoom-in").addEventListener("click", () => zoomMap(1.4));
document.querySelector("#zoom-out").addEventListener("click", () => zoomMap(1 / 1.4));
document.querySelector("#zoom-reset").addEventListener("click", resetMapView);
svg.addEventListener("wheel", event => {
  event.preventDefault();
  const rect = svg.getBoundingClientRect();
  zoomMap(event.deltaY < 0 ? 1.2 : 1 / 1.2, event.clientX - rect.left, event.clientY - rect.top);
}, { passive: false });
svg.addEventListener("pointerdown", event => {
  if (event.target.closest(".clinic-node, .water-node")) return;
  dragStart = { x: event.clientX, y: event.clientY, mapX, mapY };
  svg.setPointerCapture(event.pointerId);
  svg.classList.add("dragging");
});
svg.addEventListener("pointermove", event => {
  if (!dragStart) return;
  mapX = dragStart.mapX + event.clientX - dragStart.x;
  mapY = dragStart.mapY + event.clientY - dragStart.y;
  applyMapTransform();
});
svg.addEventListener("pointerup", () => {
  dragStart = null;
  svg.classList.remove("dragging");
});
window.addEventListener("resize", () => model && render());
switchVersion("full").catch(error => {
  svg.innerHTML = `<text x="30" y="50" fill="#c6432d">Could not load local data. Start a web server inside this folder.</text>`;
  console.error(error);
});
