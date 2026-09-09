/* Equation rendering uses the bundled KaTeX assets, including local fonts. */
(() => {
  "use strict";
  renderMathInElement(document.querySelector("main"), {
    delimiters: [
      { left: "\\[", right: "\\]", display: true },
      { left: "\\(", right: "\\)", display: false },
    ],
    throwOnError: true,
    trust: false,
  });
})();
