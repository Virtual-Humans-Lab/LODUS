# Measured performance and validation

The final full-scene run **met the 60 FPS target on this machine**. This is a
measured result, not a guarantee across other hardware, resolutions or browsers.

| Measurement | Result |
| --- | --- |
| Time | 2026-09-25 18:38:22 UTC |
| Browser | Chromium 153, Codex in-app browser, Windows |
| GPU | NVIDIA GeForce RTX 4060, ANGLE / Direct3D11 |
| Deck drawing buffer | 974 × 648, device-pixel ratio 1 |
| Active stream instances | 50,000 |
| Instances spatially inside viewport | 50,000 |
| Scene | Origin colors; all demographic groups; boundaries; corridors; corridor, neighborhood-center and POI heatmaps |
| Sampling | 3 s idle baseline, 3 s warmup, approximately 20 s measurement |
| Rendered frame intervals | 3,300 |
| Mean cadence | **165.01 FPS** |
| p50 / p95 / p99 interval | **6.10 / 6.50 / 8.10 ms** |
| Intervals exceeding 20 ms | 0 |
| Acceptance | Mean ≥58 FPS and p95 ≤20 ms: **PASS** |

Raw evidence: [benchmark-latest.json](benchmark-latest.json).

The benchmark fits the route extent and animates the recorded 18 → 19 surge
interval. Its 50,000 deterministic samples represent estimated flow streams,
not recovered individual agent identities. The population represented by the
interval is larger than the display sample count. "Inside viewport" is a
geometric count; portions of the canvas can be covered by UI cards.

Timing uses Deck's `onAfterRender`, not a counter updated on every request to
animate. It measures render-loop cadence, not independent GPU timer queries or
display presentation timestamps. The requestAnimationFrame p50 was 6.10 ms,
matching the idle baseline. The local Vite development server was used; all
assets had loaded before the warmup. No network request is required for seeking.

An earlier run measured 0.995 FPS with approximately 1,006 ms animation-frame
intervals. It **failed** and remains in [benchmark-initial.json](benchmark-initial.json).
Its near-one-second cadence is consistent with throttling, but the cause was
not independently established. The later foreground run above demonstrates the
target on this browser/GPU; the failed run was not overwritten or relabeled.

## Reproduction

1. Start the viewer and wait for “24 / 24 frames in memory.”
2. Keep its browser tab visible, with the desktop window in the foreground.
3. Click **Benchmark 50,000 entities**. On shorter screens, scroll the right
   metrics panel to reveal the button.
4. Wait for the report dialog. Controls restore their previous state afterward.
5. Use **Download report** to retain the hardware, viewport and measured data.

The routine switches on the same full scene regardless of the user's current
filters. A hidden tab, renderer error or missing animation frames invalidates
the test. Separate foreground browser/device measurements are needed before
claiming a broader hardware performance guarantee.

## Other validation

- Python: 13 tests covering Furness marginals, normalization, one-sided drift,
  impossible sparse support, numerical underflow, full-day input validation,
  demographic metadata, one-way routing, snapping and speed-weighted bends.
- TypeScript: 4 tests covering street-segment interpolation, deterministic
  50,000-sample filtering, expected filtered masses and binary route bounds.
- Strict TypeScript compilation and Vite production build pass.
- Browser checks: origin colors and legend, both concentration heatmaps, all
  ages deselected yielding zero population/samples, instant seek to terminal
  23:00, and return to the recorded gathering interval.
- Bundled run: 94 neighborhoods, 189 occupied non-residential POIs, 8,499
  routes, 2,594,674 route vertices, 36,356 graph nodes and 89,613 directed edges.
  No mass normalization was needed; worst fitted marginal error was less than
  0.000085 people, and the largest road snap was 234.2 m.

The production bundle contains the self-hosted MapLibre worker. The optional
functional and epidemiological tables are empty in the supplied example, so
their ingestion paths are supported but no SIR visualization is claimed for
this run. A 512 × 512 heat aggregation texture balances responsive updates
against density-field resolution.
