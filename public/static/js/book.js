// The book: pages turn over the spine. Wide screens show a two-page spread;
// phones keep the whole open book and glide between its left and right page.
(() => {
  const root = document.querySelector("[data-book]");
  if (!root) return;

  const N = Number(root.dataset.pages);
  const leaves = [...root.querySelectorAll("[data-leaf]")];
  const leafCount = leaves.length;
  const lastSpread = Math.ceil((N - 1) / 2);
  const counter = root.querySelector("[data-counter]");
  const toc = root.querySelector('[data-face="toc"]');
  const endpaper = root.querySelector('[data-face="endpaper"]');
  const narrowQuery = window.matchMedia("(max-width: 860px)");

  let page = clamp(Number(root.dataset.start) || 0);

  function clamp(p) { return Math.max(0, Math.min(N - 1, p)); }
  const spreadOf = (p) => Math.floor(p / 2);

  function render() {
    const spread = spreadOf(page);
    leaves.forEach((leaf, k) => {
      const turned = k < spread;
      // Unturned leaves stack with the lowest k on top; turned ones with the highest k on top.
      leaf.style.transform = turned
        ? `rotateY(-180deg) translateZ(-${k + 1}px)`
        : `rotateY(0deg) translateZ(${leafCount - k}px)`;
    });

    // Only the two visible faces are reachable by keyboard and screen readers.
    const left = spread === 0 ? toc : leaves[spread - 1]?.querySelector('[data-face="back"]');
    const right = spread < leafCount ? leaves[spread].querySelector('[data-face="front"]') : endpaper;
    root.querySelectorAll("[data-face]").forEach((face) => {
      const visible = face === left || face === right;
      face.inert = !visible;
      face.setAttribute("aria-hidden", String(!visible));
    });

    const narrow = narrowQuery.matches;
    root.dataset.focus = page % 2 === 1 ? "right" : "left";
    const atFirst = narrow ? page <= 0 : spread <= 0;
    const atLast = narrow ? page >= N - 1 : spread >= lastSpread;
    root.querySelectorAll("[data-prev]").forEach((b) => { b.disabled = atFirst; });
    root.querySelectorAll("[data-next]").forEach((b) => { b.disabled = atLast; });

    const L = 2 * spread + 1;
    const R = 2 * spread + 2;
    counter.textContent = narrow
      ? `Page ${page + 1} of ${N}`
      : R <= N ? `Pages ${L}–${R} of ${N}` : `Page ${L} of ${N}`;

    const url = new URL(window.location.href);
    if (page) url.searchParams.set("page", page); else url.searchParams.delete("page");
    history.replaceState(null, "", url);
  }

  function go(p) { page = clamp(p); render(); }
  function next() {
    if (narrowQuery.matches) go(page + 1);
    else if (spreadOf(page) < lastSpread) go(2 * spreadOf(page) + 2);
  }
  function prev() {
    if (narrowQuery.matches) go(page - 1);
    else if (spreadOf(page) > 0) go(2 * spreadOf(page) - 2);
  }

  root.addEventListener("click", (e) => {
    const target = e.target.closest("[data-next], [data-prev], [data-jump]");
    if (!target || target.disabled) return;
    if (target.hasAttribute("data-next")) next();
    else if (target.hasAttribute("data-prev")) prev();
    else go(Number(target.dataset.jump));
  });
  document.addEventListener("keydown", (e) => {
    if (e.target.closest("input, textarea, select")) return;
    if (e.key === "ArrowRight") next();
    else if (e.key === "ArrowLeft") prev();
  });
  narrowQuery.addEventListener("change", render);

  render();
})();
