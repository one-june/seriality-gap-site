# Stopped rollout-1 experiment batch

Experiment execution stopped on 3 September 2026 at the user's request. No run in this archive passes the complete rollout-1 gate.

This archive contains 21 full Case 2 generations:

- Six random tie-break seeds: `h1-selection-seed-1` through `h1-selection-seed-6`.
- Three last-active-step tests: `h1-guide-end-step-46` through `h1-guide-end-step-48`.
- Nine step-49 strength tests: `h1-final-scale-*`.
- Three per-step update-cap tests: `h1-update-cap-48`, `h1-update-cap-49`, and `h1-update-cap-51`.

Every run directory contains:

- `config.yaml`: exact guidance configuration.
- `run.json`: generation metadata.
- `success-evaluation.json`: fixed-gate metrics.
- `guided-final.mp4`: final 49-frame video.
- `diagnostics.json.gz`: complete compressed guidance diagnostics.

The best result remains the earlier `h1-run-29-sqrt-start0p7`: 220/220 valid ball-transitions, mean 0.095764, p95 0.271324, and maximum 0.780598. It fails the fixed p95 limit of 0.25 and maximum limit of 0.75.

See `out/guidance/guidance-experiments-report/rollout-smallest-error-results-so-far.html` for the complete report and visual comparison.
