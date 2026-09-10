/* Figure galleries: show one group at a time and play only what is on screen.

   A <select data-gallery="ID"> switches between the .gallery-group children of #ID,
   matching the option's value against each group's data-key. */
(() => {
  "use strict";
  const galleries = Array.from(document.querySelectorAll("select[data-gallery]"))
    .map((select) => ({ select, container: document.getElementById(select.dataset.gallery) }))
    .filter(({ container }) => container);
  if (!galleries.length) return;

  for (const { select, container } of galleries) {
    const groups = Array.from(container.querySelectorAll(".gallery-group"));

    function show(key) {
      for (const group of groups) {
        const visible = group.dataset.key === key;
        group.hidden = !visible;
        if (!visible) {
          for (const video of group.querySelectorAll("video")) video.pause();
        }
      }
    }

    select.disabled = false;
    select.addEventListener("change", () => show(select.value));
    show(select.value);
  }

  // Autoplay is a convenience, so skip it when the reader asks for less motion or the
  // browser cannot tell us what is on screen. The per-video controls still work.
  const videos = galleries.flatMap(({ container }) => Array.from(container.querySelectorAll("video")));
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
