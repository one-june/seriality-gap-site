# Project page

This directory is a complete static website for the repository's experimental findings. It starts with the contents of `out/guidance/KEY_FINDINGS.md`, both comparison plots, and the full video viewer: 10 cases × 5 step counts × 5 methods.

## Preview

From the repository root:

```bash
python -m http.server 8000 --directory docs
```

Open <http://localhost:8000>. You can also open `index.html` directly in a browser. No build step, package installation, external fonts, or CDN is required to view the site.

## Publish on GitHub Pages

1. Commit and push `docs/` to the branch you want to publish.
2. In the GitHub repository, open **Settings → Pages**.
3. Under **Source**, select **Deploy from a branch**.
4. Select that branch and **/docs**, then save.

GitHub displays the published URL in the Pages settings. This setup follows [GitHub's publishing-source guide](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

To use a separate website repository, copy everything inside `docs/`, including `.nojekyll` and `.gitignore`, to its root. Select **/(root)** as that repository's Pages source. All site resources use relative paths within this directory.

To export an archive from the repository root:

```bash
tar -czf /tmp/seriality-gap-project-page.tar.gz -C docs .
```

## Add results

- Add a `<section class="experiment" id="your-result">` inside `<main>` in `index.html`. The guidance section provides the layout for findings, figures, videos, and data downloads.
- Copy the figures, clips, and summaries into `assets/your-result/`. Reference those copies with relative paths; do not link outside `docs/`.
- Add an entry to the header navigation for the new section. Reuse `reading-width`, `plot`, and `data-links` for consistent formatting.
- Edit the page's text in `index.html`. The current guidance prose was adapted from `out/guidance/KEY_FINDINGS.md`; changes to that Markdown file are not automatically applied to the page.

## Files

| Path | Purpose |
| --- | --- |
| `index.html` | Page content and section structure |
| `assets/style.css` | Shared layout and responsive styles |
| `assets/comparison.js` | Video selection, synchronized playback, frame stepping, and metrics |
| `assets/guidance/plots/` | The two original SVG plots |
| `assets/guidance/videos/` | The 210 unique clips used by the comparison |
| `assets/guidance/comparison-data.js` | Sample choices, video paths, and per-sample metrics |
| `assets/guidance/summaries/` | The three original holdout summary files |
| `.nojekyll` | Publish these files directly without Jekyll processing |
| `.gitignore` | Include the curated clips despite the repository's general MP4 exclusion |

The viewer loads only the five selected clips. Its URL records the selected case and step count so a comparison can be shared directly. The default is Case 2, seed 0, at 50 reverse steps. Frame stepping pauses playback; Restart preserves whether the viewer was playing. Playback speed is adjusted for each clip's duration so all methods follow the same frame position.

## Refresh the guidance assets

With the original experiment outputs present, run this from the repository root:

```bash
python scripts/export_project_page_guidance.py
```

The export script uses Beautiful Soup (`beautifulsoup4`) to read the original report. It copies the two figures, three summaries, and all referenced comparison clips, then rebuilds the viewer's data file. It does not change `index.html` or assets belonging to other results.

Layout reference: [Nerfies](https://nerfies.github.io/), an example of a research project page with figures, videos, and interactive controls. This site uses its own HTML, CSS, and JavaScript.
