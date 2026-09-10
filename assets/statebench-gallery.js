/* Trajectory gallery: show one ball count at a time and play only what is on screen. */
(() => {
  "use strict";
  const gallery = document.getElementById("state-gallery");
  const select = document.getElementById("gallery-balls");
  if (!gallery || !select) return;

  const groups = Array.from(gallery.querySelectorAll(".gallery-group"));
  const videos = Array.from(gallery.querySelectorAll("video"));

  function show(balls) {
    for (const group of groups) {
      const visible = group.dataset.balls === balls;
      group.hidden = !visible;
      if (!visible) {
        for (const video of group.querySelectorAll("video")) video.pause();
      }
    }
  }

  select.disabled = false;
  select.addEventListener("change", () => show(select.value));
  show(select.value);

  // Autoplay is a convenience, so skip it when the reader asks for less motion
  // or the browser cannot tell us what is on screen. The controls still work.
  const still = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (still.matches || !("IntersectionObserver" in window)) return;

  const observer = new IntersectionObserver((entries) => {
    for (const { target, isIntersecting } of entries) {
      if (isIntersecting) target.play().catch(() => {});
      else target.pause();
    }
  }, { threshold: 0.4 });
  for (const video of videos) observer.observe(video);

  still.addEventListener("change", (event) => {
    if (!event.matches) return;
    observer.disconnect();
    for (const video of videos) video.pause();
  });
})();
