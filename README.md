# Project page

This directory is the complete static website **Mind the Seriality Gap**. It opens with the argument about perfect scores, score error, state Jacobians, and SSH's constant-step assumptions. The experiments include the findings from `out/guidance/KEY_FINDINGS.md`, the 10-case × 5-step × 5-method video viewer, and rollout-1 guidance results: a synchronized tuned example, two results plots, and a full experiment report. A Rollout-5 section adds a matched Case 2 comparison, five-video results, the broad oracle comparison, and its full report.

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
- Copy the figures, clips, and summaries into `assets/your-result/`. Reference those copies with relative paths; do not link outside `docs/`.
- Add an entry to the header navigation for the new section. Reuse `reading-width`, `plot`, and `data-links` for consistent formatting.
- Edit the page's text in `index.html`. The current guidance prose was adapted from `out/guidance/KEY_FINDINGS.md`; changes to that Markdown file are not automatically applied to the page.
- Write inline equations as `\( ... \)` and display equations as `\[ ... \]`. Wrap display equations in `<div class="equation" tabindex="0" role="region" aria-label="Describe the equation">` so wide equations can scroll on small screens. Use HTML escapes such as `&amp;` for alignment markers and `&lt;` for less-than signs. Bundled KaTeX renders equations inside `<main>` automatically.

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
| `assets/video-group.js` | Independent synchronized playback for each fixed three-clip comparison |
| `assets/style.css` | Shared layout and responsive styles |
| `assets/math.js` | Render the page's LaTeX equations |
| `assets/vendor/katex/` | KaTeX 0.18.7, fonts, and MIT license; no external requests |
| `assets/comparison.js` | Video selection, synchronized playback, frame stepping, and metrics |
| `assets/guidance/plots/` | The two original SVG plots |
| `assets/guidance/videos/` | The 210 unique clips used by the comparison |
| `assets/guidance/comparison-data.js` | Sample choices, video paths, and per-sample metrics |
| `assets/guidance/summaries/` | The three original holdout summary files |
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
