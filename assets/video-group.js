/* Synchronized playback for fixed comparisons, independent of the sample viewer. */
(() => {
  "use strict";
  document.querySelectorAll("[data-video-group]").forEach(async (group) => {
    const videos = Array.from(group.querySelectorAll("video"));
    const find = (selector) => group.querySelector(selector);
    const playButton = find('[data-action="play"]');
    const slider = find('[data-control="frame"]');
    const speed = find('[data-control="speed"]');
    const loop = find('[data-control="loop"]');
    const output = find('[data-output="frame"]');
    const status = find('[data-output="status"]');
    const frames = Number(group.dataset.frames);
    const controls = group.querySelectorAll("button, input[type=range]");
    let ready = false;
    let playing = false;
    let request = null;
    let attempt = 0;

    function pause() {
      playing = false;
      attempt += 1;
      cancelAnimationFrame(request);
      videos.forEach((video) => video.pause());
      playButton.textContent = "Play all";
      playButton.setAttribute("aria-pressed", "false");
    }

    function showFrame(frame) {
      const bounded = Math.max(0, Math.min(frames - 1, frame));
      slider.value = bounded;
      output.textContent = `Frame ${bounded + 1} / ${frames}`;
      slider.setAttribute("aria-valuetext", output.textContent);
      return bounded;
    }

    function seek(frame) {
      if (!ready) return;
      const bounded = showFrame(frame);
      const fraction = bounded === 0 ? 0 : (bounded + 0.1) / frames;
      videos.forEach((video) => { video.currentTime = fraction * video.duration; });
    }

    function setRates() {
      const longest = Math.max(...videos.map((video) => video.duration));
      videos.forEach((video) => {
        video.playbackRate = Number(speed.value) * video.duration / longest;
      });
    }

    function tick() {
      if (!playing) return;
      const fraction = videos[0].currentTime / videos[0].duration;
      showFrame(Math.floor(fraction * frames));
      videos.slice(1).forEach((video) => {
        if (!video.seeking && Math.abs(video.currentTime / video.duration - fraction) > 1 / frames) {
          video.currentTime = Math.min(fraction, (frames - 0.1) / frames) * video.duration;
        }
      });
      request = requestAnimationFrame(tick);
    }

    async function play() {
      if (!ready || playing) return;
      if (videos[0].ended) seek(0);
      const currentAttempt = ++attempt;
      playing = true;
      playButton.textContent = "Pause";
      playButton.setAttribute("aria-pressed", "true");
      setRates();
      try {
        await Promise.all(videos.map((video) => video.play()));
        if (currentAttempt === attempt && playing) {
          status.textContent = "";
          request = requestAnimationFrame(tick);
        }
      } catch (_) {
        if (currentAttempt !== attempt) return;
        pause();
        status.textContent = "Playback could not start. Try Play all again or use the Open video links.";
      }
    }

    playButton.addEventListener("click", () => { if (playing) pause(); else play(); });
    find('[data-action="restart"]').addEventListener("click", () => {
      const resume = playing;
      pause(); seek(0);
      if (resume) play();
    });
    find('[data-action="previous"]').addEventListener("click", () => { pause(); seek(Number(slider.value) - 1); });
    find('[data-action="next"]').addEventListener("click", () => { pause(); seek(Number(slider.value) + 1); });
    slider.addEventListener("input", () => { pause(); seek(Number(slider.value)); });
    speed.addEventListener("change", () => { if (ready) setRates(); });
    document.addEventListener("visibilitychange", () => { if (document.hidden) pause(); });
    videos[0].addEventListener("ended", () => {
      if (!playing) return;
      pause();
      if (loop.checked) { seek(0); play(); }
      else seek(frames - 1);
    });

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    async function load(video) {
      if (location.protocol !== "file:") {
        const response = await fetch(video.getAttribute("src"), { signal: controller.signal });
        if (!response.ok) throw new Error("Video unavailable");
        video.src = URL.createObjectURL(await response.blob());
      }
      await new Promise((resolve, reject) => {
        const cleanup = () => {
          video.removeEventListener("loadedmetadata", loaded);
          video.removeEventListener("error", failed);
          controller.signal.removeEventListener("abort", failed);
        };
        const loaded = () => { cleanup(); resolve(); };
        const failed = () => { cleanup(); reject(new Error("Video unavailable")); };
        video.addEventListener("loadedmetadata", loaded);
        video.addEventListener("error", failed);
        controller.signal.addEventListener("abort", failed, { once: true });
        if (controller.signal.aborted || video.error) failed();
        else if (video.readyState >= 1) loaded();
      });
    }
    try {
      await Promise.all(videos.map(load));
      if (videos.some((video) => !Number.isFinite(video.duration) || video.duration <= 0)) {
        throw new Error("Invalid video duration");
      }
      ready = true;
      controls.forEach((control) => { control.disabled = false; });
      status.textContent = "";
      seek(0);
    } catch (_) {
      controller.abort();
      status.textContent = "A clip could not load. Reload this page or use the Open video links.";
    } finally {
      clearTimeout(timeout);
    }
  });
})();
