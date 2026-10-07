# Porto Alegre Mobility Observatory

An offline-first, 24-hour LODUS viewer with a Python entropy OD estimator,
directed OSM routing, MapLibre and Deck.gl. The included bundle is compiled from
`WorkSchool94-StadiumPopulation`, with 94 neighborhoods and 8,499 street routes.
No simulated trip is drawn as a centroid-to-centroid line.

Particles use warm gold against teal corridors in **Contrast** mode. Choose
**Particle color → Origin neighborhood** for a stable categorical palette and
expand the neighborhood color key. Hover a particle to inspect its inferred
origin and destination. Origin colors refer to the neighborhood, including in
node mode, and stay consistent while seeking or filtering.

Independent **Neighborhood centers** and **Points of interest** heatmaps show
interpolated population stocks with demographic filtering. The bundled run has
189 non-residential simulation POIs with nonzero recorded population during
the day. Both heatmaps use fixed display color domains, so a smaller filtered
population does not automatically stretch back to the same maximum color.
POIs use a yellow → red → white ramp from lower to higher concentration,
separate from teal street corridors and purple neighborhood centers.
They refresh at 2 Hz during playback; moving particles remain independent.
These maps concentrate aggregate counts at supplied representative coordinates,
not observed individual locations. Their populations overlap, so they must
not be added. **Street flow density** remains a separate route-flow heatmap.

## Run

From `D:\LODUS\crowd_viz`:

```powershell
npm.cmd ci
npm.cmd run dev
```

Open http://127.0.0.1:5173/. All simulation data, street geometry, and route
vertices load before playback becomes available. No API key or remote basemap
is needed. This is a desktop-oriented WebGL2 application; controls also adapt
to narrow screens. The bundled dataset occupies about 80 MB uncompressed.

```powershell
npm.cmd run build
npm.cmd run preview
```

Serve the generated `dist` directory over HTTP(S), not `file://`. Serve `.bin`
as `application/octet-stream`; Brotli/gzip and versioned asset caching reduce
transfer costs. Do not publish private simulator exports without authorization.

## Rebuild from simulator exports

```powershell
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
# One-time public OSM acquisition; graph cache is ignored by Git.
..\.venv\Scripts\python.exe -m pipeline.routing
..\.venv\Scripts\python.exe -m pipeline.build
```

The defaults refer to the existing local stadium run, environment file and
municipal boundaries in this repository. To use another complete day:

```powershell
..\.venv\Scripts\python.exe -m pipeline.build --input ..\output_logs\MyRun --day 0 --environment ..\data_input\MyEnvironment.json
```

For the existing `full94` export, use `--input ..\output_logs\full94 --day 0`
with the default environment. Known legacy neighborhood names (including
`Centro`, `Coronel Aparício Borges` and `Jardim Dona Leopoldina`) resolve to
the matching polygons and environment coordinates, including POIs. Original
simulation IDs remain unchanged. Unknown names still fail validation.
After compilation, reload the dev-server page to load the new simulation.

`--level nodes` fits `nodes.csv` instead of regional totals. Each node must
resolve to an environment POI (`Region//name`, or `Region//unique_name`). Never
add node and region matrices: they describe overlapping people. The UI
aggregates node stocks into neighborhood polygons in node mode.

`--k 2` assigns two shortest simple paths with logit weights proportional to
`exp(-beta * travel_seconds)`. Default `k=1` is deterministic shortest-path
assignment. This is free-flow routing, not a calibrated congestion equilibrium.

```powershell
..\.venv\Scripts\python.exe -m pipeline.routing --mode walk --graph cache\porto-alegre-walk.graphml
..\.venv\Scripts\python.exe -m pipeline.build --mode walk --graph cache\porto-alegre-walk.graphml --output public\data-walk
```

Driving respects OSM directions and access restrictions. Walking uses a separate
pedestrian network and 4.8 km/h. It is selected at build time; one route must
never combine incompatible modal graph edges. The default acquisition envelope
is western/southern/northern/eastern Porto Alegre and nearby connections:
`(-51.32, -30.29, -51.00, -29.92)` in OSMnx `(left,bottom,right,top)` order.

`--balance strict` rejects drift; default `normalize` applies the requested
destination scaling and records every residual. The pipeline fails on unmatched
polygons, missing coordinates, invalid states, missing hours, one-sided flux,
infeasible support or route failures. It never substitutes straight lines.
Snapshots more than 2,500 m from the road graph are rejected; the included run's
maximum snap distance is 234.2 m. Snap offsets are reported, not drawn as trips.

## Outputs

| Artifact | Contents |
| --- | --- |
| `public/data/run.json` | 24 states, OD assignments, priors, venue series, extension tables, route metadata |
| `public/data/routes.bin` | Little-endian float64 `(longitude, latitude, elapsedSeconds)` triples |
| `public/data/neighborhoods.geojson` | Matched municipal polygons, with audited topology repair |
| `public/data/roads.geojson` | Local OSM street basemap |
| `public/data/od.csv` | Estimated flow assigned to each route, per hourly interval |
| `public/data/audit.json` | Mass residuals, marginal errors, hashes, source warnings and snapping distances |

The binary route metadata gives an `offset` in vertices and a `vertices` count.
Paths are hydrated and validated on startup, then the worker produces a float32
RGBA GPU atlas and per-hour typed particle buffers. Geographic input/cache
precision remains float64; the GPU display has sub-meter float32 precision at
this city's latitude. Paths retain every street bend.

## Interpretation

The repository logger computes `dTotals[h] = Total[h] - Total[h-1]`. Therefore
the interval **18 → 19 uses the deltas recorded at 19**, not at 18. Frame 0 is
the initial displayed state; its incoming delta refers to the unobserved
previous state. Frame 23 is terminal. Playback stops there, without inventing
an overnight return.

Net deltas do not identify actual OD trips. This model finds a cost-weighted
redistribution with the observed net marginals. Balanced counterflows,
within-zone trips and individual trajectories are not recoverable. Node mode
can reveal within-neighborhood movements when node deltas contain them.

The example contains a 500,000-person simulated stadium gathering at 19:00,
and discharge at 23:00. Those are scenario outputs, not a claim about actual
stadium attendance or physical capacity. The chart interpolates observed node
stocks, with no invented advance ingress schedule. Enter a **scenario capacity**
to display saturation; no authoritative capacity was supplied.

Age/occupation values are modeled, not observed joint attributes. If valid
`output.txt` distributions are available they are used; otherwise the supplied
brief's N=4,833 prior is explicitly labeled as uncalibrated for this run.
Occupation composition is biased toward positive work/school node changes or
`diss.csv` work allocation changes. This does not recover cross-attribute
correlations or preserve unobserved demographic OD marginals.

Locals/outsiders are location-relative: a traveler can leave as a local and
arrive as an outsider. The system does not fit their deltas as separate
conserved commodities. Trip samples use origin stock composition; polygon and
venue stocks use recorded local/outsider counts. Filtered counts are expected
values; displayed particles are deterministic stratified samples.

Particles represent **continuous flow streams**, capped at 50,000 weighted
samples per interval. Each traverses its exact road polyline at the road's
relative free-flow speed and recycles when it reaches the end. They are not
literal recovered agents or departure timestamps. An hourly change swaps the
preloaded cohort; positions are continuous within each interval. The heatmap
shows weighted corridor density; boundary arrows are net-zone indicators,
not measured boundary-crossing locations. Cross-boundary movement is always
represented by OSM paths, not these decorative normals.

`node_positions.csv` in the current logger contains **blob/region/node IDs**,
not latitudes or longitudes. The ingestion layer retains and validates it but
never interprets those IDs as coordinates. Coordinates come from the supplied
environment. SIR coordinates are used directly for optional infected-node
markers. The included run has empty `diss.csv`, `node_positions.csv` and
`nodes_sir.csv`; the UI exposes the missing data rather than fabricating it.

## Verification and benchmark

```powershell
..\.venv\Scripts\python.exe -m unittest discover -s tests -p test_*.py -v
npm.cmd test
npm.cmd run build
```

Use **Benchmark 50,000 entities** in a foreground desktop browser. The test
enables all demographics, origin colors, street streams, corridor paths, boundary
indicators and all three density layers; fits the active route extent;
measures idle animation cadence for 3 seconds, warms up for 3 seconds, and measures
20 seconds of Deck's completed render callbacks. It exports viewport, GPU,
browser, instance count, in-viewport count, FPS and p50/p95/p99 cadence.
Backgrounding the tab invalidates the run. The target is mean ≥58 FPS and
p95 ≤20 ms, with 60 FPS as the display target. A failed measurement remains a
failure; the viewer never reports a synthetic 60 FPS result.

See [architecture](docs/architecture.md) and [benchmark evidence](docs/benchmark.md).

## Sources

Municipal boundaries are the existing repository conversion of
`data_input/spatial/bairros_vigentes`, matched by normalized neighborhood names.
Aliases include Passo D'Areia/Passo Da Areia and São José/Vila São José. One
invalid Arquipélago topology is repaired and recorded in the audit.
Source reference: [Prefeitura's neighborhood dataset](https://dadosabertos.poa.br/dataset/bairros-lc-12-112-16).

Streets © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright),
licensed under ODbL. Routes and exported street geometry are derived from OSM;
retain attribution and satisfy ODbL obligations when redistributing derivatives.
Road graph acquisition uses [OSMnx](https://osmnx.readthedocs.io/en/stable/user-reference.html).
Rendering follows [Deck.gl MapLibre integration](https://deck.gl/docs/developer-guide/base-maps/using-with-maplibre)
and [MapLibre's Vite worker setup](https://maplibre.org/maplibre-gl-js/docs/).
