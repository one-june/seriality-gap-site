/* Synchronized playback for the curated guidance comparison. No dependencies. */
(() => {
  "use strict";

  const data = window.guidanceComparison;
  const byId = (id) => document.getElementById(id);
  const caseSelect = byId("case-select");
  const stepsSelect = byId("steps-select");
  const playButton = byId("play-button");
  const restartButton = byId("restart-button");
  const previousButton = byId("previous-frame");
  const nextButton = byId("next-frame");
  const slider = byId("frame-slider");
  const output = byId("frame-output");
  const status = byId("viewer-status");
  const speedSelect = byId("speed-select");
  const loopToggle = byId("loop-toggle");
  const grid = byId("video-grid");
  const controls = [playButton, restartButton, previousButton, nextButton, slider];
  const colors = {
    "ground-truth": "#8a9082", bidirectional: "#64748b", autoregressive: "#086c63",
    oracle: "#e45756", rollout1: "#9d792d",
  };
  const labels = {
    "ground-truth": "Ground truth",
    bidirectional: "Vanilla bidirectional DiT",
    autoregressive: "Autoregressive DiT",
    oracle: "Clean-latent guided bidirectional DiT",
    rollout1: "Best rollout-1 guided bidirectional DiT",
  };
  let videos = [];
  let ready = false;
  let playing = false;
  let frameRequest = null;
  let selection = 0;
  let playAttempt = 0;
  let loading = null;

  if (!data) {
    status.textContent = "Comparison data could not load. Reload this page to try again.";
    return;
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function makeCard(entry) {
    const card = element("article", "video-card");
    card.style.setProperty("--method-color", colors[entry.method]);
    card.dataset.method = entry.method;
    card.append(element("h4", "", labels[entry.method]));
    const video = element("video");
    video.muted = true;
    video.playsInline = true;
    video.preload = "auto";
    video.setAttribute("aria-label", labels[entry.method]);
    video.dataset.source = entry.src;
    card.append(video);
    const link = element("a", "clip-link", "Open video ↗");
    link.href = entry.src;
    link.target = "_blank";
    link.rel = "noopener";
    card.append(link);
    const score = element("div", "score");
    const rollout5 = entry.metrics["Rollout-5"];
    score.append(
      element("small", "", "Rollout-5 ↓"),
      element("strong", "", rollout5.original),
      element("span", "", "Original repo metric"),
    );
    card.append(score);
    const details = element("details", "metric-details");
    details.append(element("summary", "", "All metrics"));
    for (const [horizon, metric] of Object.entries(entry.metrics)) {
      details.append(element("h5", "", horizon));
      const list = element("dl");
      if (metric.original !== undefined) {
        list.append(element("dt", "", "Original"), element("dd", "", metric.original));
      }
      for (const [label, key] of [["Valid error", "valid"], ["Penalized", "penalized"],
        ["Scored", "scored"], ["Source available", "sourceAvailable"]]) {
        list.append(element("dt", "", label), element("dd", "", metric[key]));
      }
      details.append(list);
    }
    details.append(element("p", "validity", entry.validity));
    card.append(details);
    if (entry.method === "oracle") {
      const methodLink = element("a", "method-link", "How the oracle is calculated →");
      methodLink.href = "clean-latent-oracle.html";
      card.append(methodLink);
    }
    return card;
  }

  function pause() {
    playing = false;
    playAttempt += 1;
    cancelAnimationFrame(frameRequest);
    videos.forEach((video) => video.pause());
    playButton.textContent = "Play all";
    playButton.setAttribute("aria-pressed", "false");
  }

  function updateFrame(frame) {
    const bounded = Math.max(0, Math.min(data.frames - 1, frame));
    slider.value = bounded;
    output.textContent = `Frame ${bounded + 1} / ${data.frames}`;
    slider.setAttribute("aria-valuetext", output.textContent);
  }

  function seek(frame) {
    if (!ready) return;
    const bounded = Math.max(0, Math.min(data.frames - 1, frame));
    // Seek to the middle of each frame's interval to avoid boundary rounding.
    const fraction = bounded === 0 ? 0 : (bounded + 0.1) / data.frames;
    videos.forEach((video) => { video.currentTime = fraction * video.duration; });
    updateFrame(bounded);
  }

  function setRates() {
    const longest = Math.max(...videos.map((video) => video.duration));
    const speed = Number(speedSelect.value);
    videos.forEach((video) => { video.playbackRate = speed * video.duration / longest; });
  }

  function tick() {
    if (!playing) return;
    const master = videos[0];
    const fraction = master.currentTime / master.duration;
    updateFrame(Math.floor(fraction * data.frames));
    for (const video of videos.slice(1)) {
      const drift = Math.abs(video.currentTime / video.duration - fraction);
      if (!video.seeking && drift > 1 / data.frames) {
        video.currentTime = Math.min(fraction, (data.frames - 0.1) / data.frames) * video.duration;
      }
    }
    frameRequest = requestAnimationFrame(tick);
  }

  async function play() {
    if (!ready || playing) return;
    if (videos[0].ended) seek(0);
    const attempt = ++playAttempt;
    const currentVideos = [...videos];
    playing = true;
    playButton.textContent = "Pause all";
    playButton.setAttribute("aria-pressed", "true");
    status.textContent = "";
    setRates();
    try {
      await Promise.all(currentVideos.map((video) => video.play()));
      if (attempt !== playAttempt) return;
      frameRequest = requestAnimationFrame(tick);
    } catch (error) {
      if (attempt !== playAttempt) return;
      pause();
      status.textContent = "Playback could not start. Press Play all to retry, or use the individual video links.";
    }
  }

  function waitForMetadata(video, signal) {
    return new Promise((resolve, reject) => {
      const cleanup = () => {
        clearTimeout(timer);
        video.removeEventListener("loadedmetadata", loaded);
        video.removeEventListener("error", failed);
        signal.removeEventListener("abort", failed);
      };
      const loaded = () => {
        cleanup();
        if (Number.isFinite(video.duration) && video.duration > 0) resolve();
        else reject(new Error("Invalid video duration"));
      };
      const failed = () => { cleanup(); reject(new Error("Video unavailable")); };
      const timer = setTimeout(failed, 30000);
      video.addEventListener("loadedmetadata", loaded);
      video.addEventListener("error", failed);
      signal.addEventListener("abort", failed, { once: true });
      if (signal.aborted || video.error) failed();
      else if (video.readyState >= 1) loaded();
    });
  }

  async function loadVideo(video, signal) {
    if (window.location.protocol === "file:") {
      video.src = video.dataset.source;
    } else {
      // Buffer only the selected clips. Blob URLs support accurate seeking even
      // on simple preview servers that do not implement HTTP range requests.
      const response = await fetch(video.dataset.source, { signal });
      if (!response.ok) throw new Error(`Video request failed: ${response.status}`);
      const blob = await response.blob();
      if (signal.aborted) throw new Error("Selection changed");
      video.dataset.blobUrl = URL.createObjectURL(blob);
      video.src = video.dataset.blobUrl;
    }
    await waitForMetadata(video, signal);
  }

  async function selectComparison() {
    pause();
    ready = false;
    const currentSelection = ++selection;
    if (loading) loading.abort();
    const controller = new AbortController();
    loading = controller;
    videos.forEach((video) => {
      if (video.dataset.blobUrl) URL.revokeObjectURL(video.dataset.blobUrl);
      video.removeAttribute("src");
      video.load();
    });
    controls.forEach((control) => { control.disabled = true; });
    status.textContent = "Loading the five videos…";
    const caseId = caseSelect.value;
    const steps = stepsSelect.value;
    const selectedCase = data.cases.find((item) => item.id === caseId);
    const cards = data.panels[`${caseId}/${steps}`].map(makeCard);
    grid.replaceChildren(...cards);
    videos = cards.map((card) => card.querySelector("video"));
    updateFrame(0);
    byId("sample-info").textContent = `${selectedCase.source} · seed ${data.seed} · ${data.frames} frames`;
    byId("example-note").hidden = !(caseId === "2" && steps === "50");
    // Preserve the current section anchor while making the selection shareable.
    const url = new URL(window.location.href);
    url.searchParams.set("case", caseId);
    url.searchParams.set("steps", steps);
    try { window.history.replaceState(null, "", url); } catch (_) { /* file:// */ }
    videos[0].addEventListener("ended", () => {
      if (currentSelection !== selection || !playing) return;
      pause();
      if (loopToggle.checked) { seek(0); play(); }
      else { seek(data.frames - 1); }
    });
    const timeout = setTimeout(() => controller.abort(), 30000);
    try {
      await Promise.all(videos.map((video) => loadVideo(video, controller.signal)));
      if (currentSelection !== selection) return;
      ready = true;
      controls.forEach((control) => { control.disabled = false; });
      status.textContent = "";
      seek(0);
    } catch (error) {
      if (currentSelection !== selection) return;
      controller.abort();
      status.textContent = "A clip could not load. Select the sample again to retry, or use its Open video link.";
    } finally {
      clearTimeout(timeout);
    }
  }

  for (const item of data.cases) {
    caseSelect.add(new Option(`Case ${item.id} · ${item.source.split("/").pop().replace(".mp4", "")}`, item.id));
  }
  data.steps.forEach((step) => stepsSelect.add(new Option(step, step)));
  const params = new URLSearchParams(window.location.search);
  caseSelect.value = data.cases.some((item) => item.id === params.get("case")) ? params.get("case") : "2";
  stepsSelect.value = data.steps.includes(Number(params.get("steps"))) ? params.get("steps") : "50";
  caseSelect.addEventListener("change", selectComparison);
  stepsSelect.addEventListener("change", selectComparison);
  playButton.addEventListener("click", () => { if (playing) pause(); else play(); });
  restartButton.addEventListener("click", () => {
    const resume = playing;
    pause(); seek(0);
    if (resume) play();
  });
  previousButton.addEventListener("click", () => { pause(); seek(Number(slider.value) - 1); });
  nextButton.addEventListener("click", () => { pause(); seek(Number(slider.value) + 1); });
  slider.addEventListener("input", () => { pause(); seek(Number(slider.value)); });
  speedSelect.addEventListener("change", () => { if (ready) setRates(); });
  document.addEventListener("visibilitychange", () => { if (document.hidden) pause(); });
  selectComparison();
})();
