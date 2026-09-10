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
})();
