# Controlled Quantitative Performance Benchmarks

Updated: 2026-08-13T18:07:12.234028+00:00

- Catalog: 48 configurations, 240 runs.
- Execution concurrency: up to 5 simulations.
- Complete runs: 240/240.
- Complete configurations: 48/48.
- Repetitions: matched seeds 0–4 for computational performance.
- Metrics: runtime, runtime per cycle, peak process working set, and maximum global blob count.
- Exclusions: inpatient care and TraceMalloc.
- Storage: completed runs retain only the artifacts required for validation, resume detection, and aggregation.

Run or resume the full matrix from the repository root:

```powershell
.\.venv\Scripts\python.exe .\misc_scripts\run_quantitative_performance.py
```
