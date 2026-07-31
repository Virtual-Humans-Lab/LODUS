# Popular Times V2

`PopularTimesV2Plugin` models one-hour visits to pharmacies, marketplaces,
and restaurants. It is separate from the compatibility action `popular_times`.

## Experiment configuration

```json
{
  "popular_times_v2_plugin": {
    "data_path": "data_input/popular_times",
    "profile_files": {
      "marketplace": "marketplace.csv",
      "restaurant": "restaurant.csv",
      "pharmacy": "pharmacy.csv"
    },
    "weekly_visit_rates": {
      "marketplace": 1.0,
      "restaurant": 1.0,
      "pharmacy": 0.25
    },
    "demand_basis": "initial_population",
    "return_mode": "prior_node",
    "distance_type": 3
  }
}
```

`demand_basis` may instead be `multiplier_csv`. In that mode,
`multiplier_file` defaults to `Setores-13Bairros-Dia.csv`, and each multiplier
is converted to an effective population using `multiplier_population_scale`
(default `700`).

## Weekly profiles

Each profile is a CSV with `ciclo,hora,quantidade` columns. `ciclo` is the
weekday index from 0 through 6. Missing coordinates and zero weights are closed
hours. Positive weights are normalized across the entire week, independently
for each POI type.

For a home population of 400 and a marketplace weekly rate of 1.0, the
marketplace requests exactly 400 visits over the week. Integer demand is
assigned with largest-remainder rounding so the weekly total is preserved.

## Action and lifecycle

The `popular_times_v2` action requires `region` and either `node` or
`node_unique_name`. POI names must pair with a home suffix; for example,
`Azenha//marketplace_0` uses `Azenha//home_0` to calculate demand.

Visitors are selected from enabled home nodes using inverse distance multiplied
by available matching population. They are tagged with their source and expiry,
occupy the POI for one simulation step, and return before regular movement on
the next step. `return_mode` can be `prior_node` (default) or `paired_home`.
When the selected return node is disabled, permanent home and then the nearest
enabled home are used as fallbacks.

Schedule this action as an end-of-step routine when Levy Walk must have first
access to home population. Water-level action plugins must be loaded before V2
so node availability is updated before visit release.

## Flood-aware Levy Walk

Levy Walk accepts two backward-compatible, opt-in settings:

```json
{
  "levy_walk_plugin": {
    "acting_enabled_only": true,
    "target_enabled_only": true
  }
}
```

The plural `target_node_types` action value is supported along with the
historical `target_node_type` alias.
