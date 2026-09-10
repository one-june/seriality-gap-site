// Collapsible experiment sections: the expand/collapse-all buttons in the
// overview, and opening a section when a link points inside it.
(function () {
  const sections = () => document.querySelectorAll('.section-details');

  document.querySelectorAll('[data-sections]').forEach((button) => {
    button.addEventListener('click', () => {
      const open = button.dataset.sections === 'expand';
      sections().forEach((details) => { details.open = open; });
    });
  });

  function reveal(hash, scroll) {
    if (!hash || hash.length < 2) return;
    const target = document.getElementById(decodeURIComponent(hash.slice(1)));
    if (!target) return;
    const details = target.closest('.section-details') || target.querySelector('.section-details');
    if (!details || details.open) return;
    details.open = true;
    if (scroll) target.scrollIntoView();
  }

  window.addEventListener('hashchange', () => reveal(location.hash, true));
  reveal(location.hash, false);

  // Mark the rail node for the section the reader is in.
  const rail = document.querySelector('.rail');
  if (rail) {
    const nodes = [...rail.querySelectorAll('[data-section]')].map((node) => ({
      node, section: document.getElementById(node.dataset.section),
    })).filter((entry) => entry.section);
    let queued = false;
    const mark = () => {
      queued = false;
      let current = null;
      nodes.forEach((entry) => {
        if (entry.section.getBoundingClientRect().top <= 140) current = entry.node;
      });
      nodes.forEach((entry) => entry.node.classList.toggle('is-current', entry.node === current));
    };
    addEventListener('scroll', () => {
      if (!queued) { queued = true; requestAnimationFrame(mark); }
    }, { passive: true });
    addEventListener('resize', mark, { passive: true });
    sections().forEach((details) => details.addEventListener('toggle', mark));
    mark();
  }
})();
