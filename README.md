# Project page

This directory is the complete static website **Mind the Seriality Gap**. An overview section at the top (`#overview`) holds nothing but the flow diagram: the three experiments in order, 02 → 03 → 04, the score-error audit (03.5) on a side path leaving the line between 03 and 04, and the theoretical argument (01) off the path entirely. Every numbered section starts collapsed; see "Collapsible sections" below. The page opens with the argument about perfect scores, score error, state Jacobians, and SSH's constant-step assumptions. Section 02, "Something naive", holds both pixel-space experiments as two parts: Part 1 is the autoregressive-against-bidirectional comparison from `out/guidance/KEY_FINDINGS.md` with the 10-case × 5-step × 5-method video viewer, and Part 2 is the combined Rollout-1 / Rollout-5 guidance work, restricted to five balls and 49 frames, which compares tuned Case 2 clips and five-video pilots sharing identical controls, then separates tests without a matching guidance-horizon comparison. Both full experiment reports remain available as archives. A state-diffusion section ports `experiments/statebench/RETRAIN_REPORT.md`: the same billiards experiment retrained on positions and velocities, with no VAE or tracker in the loop. Its subsection 3.1 (`#physics-simulator`) explains the event-driven ground-truth simulator: the world, how it jumps from contact to contact, the two contact rules, what a recorded frame does and does not contain, and how the simulator scores a generated clip; its figures and the slow-motion clip are rendered by `experiments/statebench/scripts/sim_explainer_figures.py` into `assets/statebench/figures/sim_*.png` and `assets/statebench/videos/sim_slowmo.mp4`. A final state-guidance section ports `experiments/statebench-guidance/REPORT.md`: DPS guidance toward physics targets on those retrained models, the ten plausibility measures, the whole-trajectory distribution tests, and the two rounds of physics-law guidance.

## Preview

From the repository root:

```bash
python -m http.server 8000 --directory docs
```

Open <http://localhost:8000>. You can also open `index.html` directly in a browser. No build step, package installation, or CDN is required to view the site. Equation rendering and its fonts are bundled locally.

## Publish on GitHub Pages

Continue editing `docs/` in the research repository. A separate public repository, `one-june/seriality-gap-site`, hosts the website. No second local working directory is needed.

After committing changes to `docs/`, run this from the research repository:

```bash
bash scripts/publish_project_page.sh
```

The script extracts the committed `docs/` history and pushes it to the website repository's `main` branch, with `index.html` at the root. It checks that the exported tree exactly matches `docs/`. Research files outside `docs/` are not included. The command uses the existing Git SSH access and does not require GitHub CLI authentication for subsequent updates.

For a preview of the push, use `bash scripts/publish_project_page.sh --dry-run`. To target a different website repository, set `PROJECT_PAGE_REMOTE` to its Git URL.

One-time GitHub setup:

1. Create an empty **public** repository named `seriality-gap-site` under `one-june`.
2. Run the publishing command above.
3. In that public repository, open **Settings → Pages**.
4. Select **Deploy from a branch**, **main**, and **/(root)**, then save.

After deployment, share <https://one-june.github.io/seriality-gap-site/>. Publishing from a public repository works with GitHub Free; the research repository can remain private. See [GitHub's Pages requirements](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) and [publishing-source guide](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

For other static hosts, copy everything inside `docs/`, including `.nojekyll` and `.gitignore`, to the site's root. All site resources use relative paths within this directory.

To export an archive from the repository root:

```bash
tar -czf /tmp/seriality-gap-project-page.tar.gz -C docs .
```

## Add results

- Add a `<section class="experiment" id="your-result">` inside `<main>` in `index.html`. The guidance section provides the layout for findings, figures, videos, and data downloads.
- Wrap it the way the existing sections are wrapped so it collapses: `<details class="section-details" open>` holding a `<summary class="section-summary">` with the eyebrow and `<h2>`, then a `<div class="section-body">` with everything else. Add a node for it in both overview SVGs and a link in the header navigation.
- Copy the figures, clips, and summaries into `assets/your-result/`. Reference those copies with relative paths; do not link outside `docs/`.
- Add an entry to the header navigation for the new section. Reuse `reading-width`, `plot`, and `data-links` for consistent formatting.
- Edit the page's text in `index.html`. The current guidance prose was adapted from `out/guidance/KEY_FINDINGS.md`; changes to that Markdown file are not automatically applied to the page.
- Write inline equations as `\( ... \)` and display equations as `\[ ... \]`. Wrap display equations in `<div class="equation" tabindex="0" role="region" aria-label="Describe the equation">` so wide equations can scroll on small screens. Use HTML escapes such as `&amp;` for alignment markers and `&lt;` for less-than signs. Bundled KaTeX renders equations inside `<main>` automatically.

## Section 02, in two parts

`#guidance` holds both pixel-space experiments. Its `<summary>` carries one eyebrow and one `<h2>`; inside, each part opens with a `.part-heading` — an eyebrow plus a serif `<h3>`, above a rule — followed by that part's own intro, `.study-facts` and setup note. The ids from when these were two sections still resolve: `#rollout-guidance`, `#rollout1-results` and `#rollout5-results` are empty spans at the top of the section, and the per-result anchors `#comparison`, `#data`, `#guidance-case2`, `#guidance-five-video` and `#guidance-other-tests` are unchanged.

## Collapsible sections

Each numbered section is a `<details class="section-details">`. Its `<summary>` holds the eyebrow and the `<h2>`, so a collapsed page is a list of the five headings; everything else lives in `<div class="section-body">`. The toggle beside each heading is the summary's own control, so collapsing works with JavaScript disabled. `assets/sections.js` adds two things: the **Expand all** and **Collapse all** buttons in the overview (`[data-sections="expand"]`, `[data-sections="collapse"]`), and opening a collapsed section when a link points to an anchor inside it, so the header navigation and the overview diagram keep working. Sections start collapsed, so the loaded page is the overview diagram plus the five headings.

The same trajectory is repeated as a fixed rail on the left, `.rail`, so it stays on screen while the reader scrolls. It is a third inline SVG (viewBox `0 0 210 390`): the path with an arrowhead, one `.rail-node` link per section holding a circle, its number and its title, `.traj-theory` again for the 01 node, drawn dashed and off the path, and `.traj-branch` for the dashed branch out to the 04.5 node. `assets/sections.js` adds `is-current` to the node whose section the reader is in — the last section whose top is at or above 140px from the top of the viewport, recomputed on scroll, on resize and when a section is expanded or collapsed — and `.rail-node.is-current .rail-ring` shows a ring around it.

The rail needs a clear left gutter, so above 1180px wide and 560px tall the CSS gives `main` 228px of left padding and widens `.site-header` and `.site-footer` by the same amount (`max-width: 1508px`, `padding-left: 260px`) so their text still lines up with the sections'. Below either threshold the rail is hidden and no padding is added, which is why the diagram stays in the overview section: on a phone or a short window it is the only copy.

The overview diagram is hand-written inline SVG in `.traj`, with no library and no image file. Two versions of the same drawing sit in the markup: `.traj-wide` (viewBox `0 0 1000 300`) draws the trajectory left to right, and `.traj-tall` (viewBox `0 0 340 545`) draws it top to bottom; the CSS shows the tall one below 820px wide and the wide one above. In both, `.traj-line` is the path with an arrowhead marker at its end, each `.traj-node` is a link holding the circle, the number inside it, and the section name beside it, `.traj-theory` is the 01 node, drawn with a dashed outline and placed off the path with nothing joining it to the path, and `.traj-branch` plus `.traj-side` are the dashed branch and the smaller node for 03.5. The three main nodes sit exactly on the path because each one is an endpoint of a cubic segment; the branch starts at the midpoint of the cubic from 03 to 04, `(680, 161)` in the wide drawing, `(98, 385)` in the tall one and `(38, 258)` in the rail. Text sizes are SVG units, so they scale with the width: 16px at 1030px wide down to about 13px at the 820px breakpoint.

## Files

| Path | Purpose |
| --- | --- |
| `index.html` | Page content and section structure |
| `clean-latent-oracle.html` | Separate description of the oracle calculation, linked from the findings and oracle video card |
| `rollout-1-guidance.html` | Rollout-1 guidance procedure, settings, and saved-run provenance, linked from the rollout-1 video card |
| `rollout-1-results.html` | Full HTML version of `out/guidance/ROLLOUT1_GUIDANCE_REPORT.md` |
| `assets/rollout1/` | Saved tuning clips, report figures, original metrics, configurations, and source references |
| `rollout-5-results.html` | Full HTML version of `out/guidance/ROLLOUT5_GUIDANCE_REPORT.md` |
| `assets/rollout5/` | Saved Rollout-5 clips, figures, original metrics, and source references |
| `assets/rollout-comparison/` | Common five-video metrics and plot, matching run settings, and the 5-ball/49-frame holdout subset |
| `assets/video-group.js` | Synchronized playback for the combined three-clip Case 2 comparison |
| `assets/score-error-audit/` | Score-error audit figures, summary tables, and the dataset validation record |
| `assets/style.css` | Shared layout and responsive styles |
| `assets/sections.js` | Expand-all and collapse-all buttons, and opening a collapsed section when a link targets something inside it |
| `assets/math.js` | Render the page's LaTeX equations |
| `assets/vendor/katex/` | KaTeX 0.18.7, fonts, and MIT license; no external requests |
| `assets/comparison.js` | Video selection, synchronized playback, frame stepping, and metrics |
| `assets/guidance/plots/` | The two original SVG plots |
| `assets/guidance/videos/` | The 210 unique clips used by the comparison |
| `assets/guidance/comparison-data.js` | Sample choices, video paths, and per-sample metrics |
| `assets/guidance/summaries/` | The three original holdout summary files |
| `assets/statebench/figures/` | The 11 state-diffusion charts from `experiments/statebench/out/retrain_figures/` |
| `assets/statebench/videos/` | The 16 trajectory clips (truth, bidirectional, block 4) and their source records |
| `assets/statebench/data/` | Per-seed evaluation numbers behind those charts |
| `assets/statebench-guidance/figures/` | The 16 state-guidance figures from `experiments/statebench-guidance/out/` |
| `assets/statebench-guidance/videos/` | Five randomly drawn holdout clips, six methods side by side |
| `assets/statebench-guidance/data/` | Selected strengths, every run, and both evaluation suites |
| `assets/gallery.js` | Group selector and on-screen playback, shared by both figure galleries |
| `.nojekyll` | Publish these files directly without Jekyll processing |
| `.gitignore` | Include the curated clips despite the repository's general MP4 exclusion |

The viewer loads only the five selected clips. Its URL records the selected case and step count so a comparison can be shared directly. The default is Case 2, seed 0, at 50 reverse steps. Frame stepping pauses playback; Restart preserves whether the viewer was playing. Playback speed is adjusted for each clip's duration so all methods follow the same frame position.

Each clip shows the repository's original `rollout_h5_error`, followed by `rollout_h1_error`. The exporter reads saved scores from `REPORT_DATA.json`; for ground-truth and rollout-1-guided clips, it computes missing scores with the same video tracker, one- and five-step rollouts, and center-error calculation used by `scripts/sshv2/eval.py`, excluding the five conditioning frames. Each clip is tracked once for both horizons. The separate valid-pair and penalized metrics remain available under **All metrics**.

## Refresh the guidance assets

With the original experiment outputs present, run this from the repository root:

```bash
python scripts/export_project_page_guidance.py
```

Run the export script in the project's Python environment. It uses Beautiful Soup (`beautifulsoup4`) to read the original report and the repository's simulation dependencies to compute missing original Rollout-1 and Rollout-5 scores. This also requires the corresponding source simulation files in `data/bounce/eval_49f_5n_0c/`. It copies the two figures, three summaries, and all referenced comparison clips, then rebuilds the viewer's data file. It does not change `index.html` or assets belonging to other results.

Layout reference: [Nerfies](https://nerfies.github.io/), an example of a research project page with figures, videos, and interactive controls. This site uses its own HTML, CSS, and JavaScript.

## Refresh rollout-1 results

Run `python scripts/export_project_page_rollout1.py` with Python Markdown (`markdown`) and Beautiful Soup installed. It copies the saved videos and report assets and rebuilds `rollout-1-results.html` from `out/guidance/ROLLOUT1_GUIDANCE_REPORT.md`. It verifies the selected clips against the recorded video hashes. It performs no generation or metric evaluation.

All figures, result tables, and comparison videos linked from the full report are included in this directory. Citations to the two older interactive reports retain their research-repository paths as text. The full report includes links to exported code and run metadata for reproduction.

The summary section in `index.html` is edited separately. Its tuned example uses cap 50 and final-step strength 0.10. The update-budget plot uses final strength 0.20, and the separate ten-video experiment uses cap 75 with baseline-batch noise replay. The two viewers keep their own playback state.

## Refresh rollout-5 results

Run `python scripts/export_project_page_rollout5.py` with Python Markdown and Beautiful Soup installed. It rebuilds `rollout-5-results.html` from `out/guidance/ROLLOUT5_GUIDANCE_REPORT.md`, copies the report figures and linked data, and verifies both saved Rollout-5 clips against the recorded hashes. The vanilla and ground-truth clips reuse the identical files in `assets/rollout1/videos/`. Historical HTML reports and run directories appear as research-repository paths; their full archives are not exported.

The cap-50 viewer also shows original Rollout-1, computed from that saved clip using the same evaluator as the existing viewer. To recompute its two metrics, use `python scripts/export_project_page_rollout5.py --score-viewer` in the project environment with the simulation dependencies and source data available. Rollout-5 is checked against the report archive. Scores and the video hash are stored in `assets/rollout5/data/viewer_original_rollouts.json`. No videos are generated.

The summary in `index.html` is edited separately. Its Case 2 player compares vanilla, cap-50 Rollout-5 guidance (strength 0.20 → 0.06), and the existing tuned Rollout-1 clip. The five-video plot uses late guidance with up to 12 accepted updates per step, not this cap-50 setting. Each viewer has independent playback controls.

## Refresh the state-diffusion section

Run `python scripts/export_project_page_statebench.py` from the repository root. It copies the 11 charts from `experiments/statebench/out/retrain_figures/` into `assets/statebench/figures/`, the 16 trajectory MP4s and their four source records from `out/retrain_figures/gallery/` into `assets/statebench/videos/`, and writes two CSVs of the per-seed numbers behind the charts, read from each run's saved `eval/metrics.json` at 50 denoising steps. It runs no training, sampling, or evaluation, and it does not change `index.html`.

Build the inputs first, from `experiments/statebench/`:

```bash
python scripts/make_retrain_figures.py --out out/retrain_figures
python scripts/make_report_gifs.py --indep --mp4 --balls 1 2 3 5 --clips 0 1 2 3
```

The export fails if any of them is missing. The gallery script reads each run's saved `eval/generated_steps50.npy`, so it needs no GPU; `--indep` selects the independent-simulation runs and `--mp4` adds the H.264 copies the page uses next to the GIFs the Markdown report uses. `r1_data.png`, the still that the gallery replaced, is deliberately not exported.

The section's prose was adapted from `experiments/statebench/RETRAIN_REPORT.md`; edits to that Markdown file are not applied to the page automatically. It keeps the report's visuals-first order: each result is a figure, then its explanation. The gallery at `#state-data` shows one ball count at a time, driven by `assets/gallery.js`: a `<select data-gallery="ID">` switches between the `.gallery-group` children of `#ID` by matching its value against each group's `data-key`. Without JavaScript the selector is disabled and every group is listed, and videos autoplay only while on screen and never under `prefers-reduced-motion`. The section uses `#state-diffusion`; per-result anchors are `#state-data`, `#state-main`, `#state-steps`, `#state-horizon-profile`, `#state-training`, `#state-control`, `#state-horizon-sweep`, `#state-ballcount`, `#state-block-size`, `#state-depth-width`, `#state-shift`, and `#state-cost`.

## Refresh the score-error section

Run `python scripts/export_project_page_score_error_audit.py` from the repository root. It copies the six figures from `experiments/score-error-audit/out/figures_indep/` into `assets/score-error-audit/figures/`, and the score summary, sampling summary, held-out spread table and dataset validation record into `assets/score-error-audit/data/`. It runs no audits, sampling, or evaluation, and it does not change `index.html`.

The section's prose was adapted from `experiments/score-error-audit/REPORT.md`; edits to that Markdown file are not applied to the page automatically. It uses `#score-error`, with per-result anchors `#score-method`, `#score-frames`, `#score-noise`, `#score-per-number`, `#score-spread-frames`, `#score-spread-noise`, `#score-physics-steps`, `#score-papers`, and `#score-error-data`. Its figures are numbered 18 to 23, which shifted the state-guidance figures to 24 to 41.

## Refresh the state-guidance section

Run `python scripts/export_project_page_statebench_guidance.py` from the repository root. It copies 17 figures into `assets/statebench-guidance/figures/`, the five qualitative MP4s into `assets/statebench-guidance/videos/`, and four summary CSVs into `assets/statebench-guidance/data/`. It runs no training, sampling, or evaluation, and it does not change `index.html`.

Build the inputs first, from `experiments/statebench-guidance/`:

```bash
python scripts/aggregate.py
python scripts/make_qualitative.py --mp4                     # clip 112's frame strips and the error curve
python scripts/make_qualitative.py --mp4 --no-gif --random 5 --pick-seed 0 --drop laws,laws_only --animation-only
python scripts/shotgun_eval.py && python scripts/shotgun_figures.py
python scripts/distribution_eval.py && python scripts/distribution_figures.py
```

The export names the missing step if any figure is absent. `make_qualitative.py --mp4` writes the H.264 copies the page uses next to the GIFs the Markdown report uses, at a larger panel size so the labels are legible on screen; the GIFs themselves are unchanged by that flag. The second command writes the five clips the page's gallery shows: `--random 5 --pick-seed 0` draws five holdout clips and records them in `out/qualitative/picks_random.json`, `--drop laws,laws_only` leaves out the two physics-law panels, and `--animation-only` skips the frame strips and the error curve, which still come from clip 112 and keep all eight methods.

The section's prose was adapted from `experiments/statebench-guidance/REPORT.md`; edits to that Markdown file are not applied to the page automatically. It uses `#state-guidance`, with per-result anchors `#guidance-horizon`, `#guidance-strength`, `#guidance-qualitative`, `#guidance-frames`, `#guidance-error-by-frame`, `#guidance-dashboard`, `#guidance-energy`, `#guidance-distributions`, `#guidance-divergence`, `#guidance-rollout-horizon`, `#guidance-frechet`, `#guidance-saliency`, `#guidance-dist-length`, `#guidance-umap`, `#guidance-laws-search`, `#guidance-laws-restarts`, and `#guidance-laws-length`.

Its wide tables and the eight-panel clips sit in `wide-width` and `plot wide` containers, which span the full 1,216-pixel content column instead of the 840-pixel reading column. The clips are also wrapped in `video-scroll`, so they scroll sideways rather than shrinking below a legible size on a phone.

## Refresh the combined guidance comparison

Run `python scripts/build_project_page_rollout_comparison.py` with Matplotlib installed. It builds the common five-video plot and CSV tables from the score archives and exported cache, verifies matching controls and shared experiment settings, and extracts only the 5-ball/49-frame holdout results. `matched_setup.json` records the common settings and each run's guidance configuration.

To recalculate original Rollout-1 and Rollout-5 for the 30 saved Rollout-5 pilot clips, add `--score-pilot` in the project environment with Beautiful Soup and the simulation dependencies. The script uses the existing original evaluator and checks every Rollout-5 value against the report archive within 1e-8. It does not generate videos. The Rollout-1 pilot metrics come from its validated score archive. Detector-validity counts are excluded from this comparison because the experiments used different tracker versions.

The combined section uses `#rollout-guidance`; the previous `#rollout1-results` and `#rollout5-results` links still lead to it. `index.html` is edited separately from the plots and report archives. The large holdout table uses only the filtered `holdout_5ball49f.csv`; the full Rollout-5 archive retains the other video settings.
