// The aisle: walk forward/back between pairs of shelves, open a shelf's bookcase,
// and leave through the EXIT at the entrance.
(() => {
  const stage = document.querySelector("[data-aisle]");
  if (!stage) return;

  const stations = Number(stage.dataset.stations) || 1;
  const shelves = [...stage.querySelectorAll("[data-shelf]")];
  const cases = [...stage.querySelectorAll("[data-case]")];
  const forward = stage.querySelector("[data-forward]");
  const forwardLabel = stage.querySelector("[data-forward-label]");
  const back = stage.querySelector("[data-back]");
  const exit = stage.querySelector("[data-exit]");
  const stationLabel = stage.querySelector("[data-station-label]");
  const scene = stage.querySelector("[data-scene]");
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  let station = 0;
  let openCase = null;
  let returnFocus = null;

  function render() {
    stage.style.setProperty("--station", station);
    shelves.forEach((shelf) => {
      const dist = Number(shelf.dataset.pair) - station;
      shelf.dataset.dist = dist < 0 ? "behind" : String(Math.min(dist, 3));
      shelf.tabIndex = dist < 0 ? -1 : 0;
    });
    forward.disabled = station >= stations - 1;
    forwardLabel.textContent = forward.disabled ? "End of the aisle" : "Walk forward";
    back.hidden = station === 0;
    exit.hidden = station !== 0;
    stationLabel.textContent = `Aisle ${station + 1} of ${stations}`;
    stage.querySelectorAll("[data-pip]").forEach((pip) => pip.toggleAttribute("data-on", Number(pip.dataset.pip) === station));
    stage.querySelectorAll("[data-hud-pair]").forEach((row) => { row.hidden = Number(row.dataset.hudPair) !== station; });
  }

  function walk(step) {
    const next = Math.max(0, Math.min(stations - 1, station + step));
    if (next === station || openCase) return;
    station = next;
    render();
  }

  function openShelf(slug, { instant = false } = {}) {
    const shelf = shelves.find((s) => s.dataset.shelf === slug);
    const bookcase = cases.find((c) => c.dataset.case === slug);
    if (!shelf || !bookcase) return;
    returnFocus = document.activeElement;
    station = Number(shelf.dataset.pair);
    render();
    cases.forEach((c) => { c.hidden = c !== bookcase; });
    openCase = bookcase;
    const turn = Number(getComputedStyle(shelf).getPropertyValue("--sign")) < 0 ? "-30deg" : "30deg";
    stage.style.setProperty("--turn", turn);
    if (instant) stage.setAttribute("data-snap", "");
    stage.setAttribute("data-browsing", "");
    scene.setAttribute("aria-hidden", "true");
    setTimeout(() => {
      stage.removeAttribute("data-snap");
      (bookcase.querySelector(".is-last") || bookcase.querySelector("[data-close-case]")).focus({ preventScroll: true });
    }, instant || reduced ? 0 : 950);
  }

  function closeShelf() {
    if (!openCase) return;
    openCase = null;
    stage.removeAttribute("data-browsing");
    stage.style.setProperty("--turn", "0deg");
    scene.removeAttribute("aria-hidden");
    (returnFocus && document.contains(returnFocus) ? returnFocus : forward).focus({ preventScroll: true });
  }

  function leave() {
    if (stage.hasAttribute("data-leaving")) return;
    stage.setAttribute("data-leaving", "");
    setTimeout(() => { window.location.href = stage.dataset.exitHref; }, reduced ? 100 : 900);
  }

  forward.addEventListener("click", () => walk(1));
  back.addEventListener("click", () => walk(-1));
  exit.addEventListener("click", leave);
  shelves.forEach((s) => s.addEventListener("click", () => openShelf(s.dataset.shelf)));
  stage.querySelectorAll("[data-open-shelf]").forEach((b) => b.addEventListener("click", () => openShelf(b.dataset.openShelf)));
  stage.querySelectorAll("[data-close-case]").forEach((b) => b.addEventListener("click", closeShelf));

  document.addEventListener("keydown", (e) => {
    if (e.target.closest("input, textarea, select")) return;
    if (e.key === "Escape") closeShelf();
    else if (!openCase && e.key === "ArrowUp") { e.preventDefault(); walk(1); }
    else if (!openCase && e.key === "ArrowDown") { e.preventDefault(); station === 0 ? leave() : walk(-1); }
  });

  window.addEventListener("pageshow", (e) => {
    if (e.persisted) stage.removeAttribute("data-leaving");
  });

  // Clean ?from=gate / ?shelf=… off the address bar once handled.
  const params = new URLSearchParams(window.location.search);
  if (params.has("from") || params.has("shelf")) history.replaceState(null, "", window.location.pathname);

  render();
  if (stage.dataset.open) openShelf(stage.dataset.open, { instant: true });
})();
