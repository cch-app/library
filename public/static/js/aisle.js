// The aisle: walk forward/back between pairs of shelves, open a shelf's bookcase,
// walk up to the library computer at the end, and leave through the EXIT at the entrance.
(() => {
  const stage = document.querySelector("[data-aisle]");
  if (!stage) return;

  const stations = Number(stage.dataset.stations) || 1;
  const DESK_STEP = 0.55; // how far past the last shelves the computer stands
  const shelves = [...stage.querySelectorAll("[data-shelf]")];
  const cases = [...stage.querySelectorAll("[data-case]")];
  const forward = stage.querySelector("[data-forward]");
  const forwardLabel = stage.querySelector("[data-forward-label]");
  const back = stage.querySelector("[data-back]");
  const exit = stage.querySelector("[data-exit]");
  const stationLabel = stage.querySelector("[data-station-label]");
  const scene = stage.querySelector("[data-scene]");
  const monitor = stage.querySelector("[data-desk-monitor]");
  const deskChip = stage.querySelector("[data-desk-chip]");
  const hudDesk = stage.querySelector("[data-hud-desk]");
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  let station = 0;
  let atDesk = false;
  let openCase = null;
  let returnFocus = null;

  function render() {
    stage.style.setProperty("--station", atDesk ? stations - 1 + DESK_STEP : station);
    stage.toggleAttribute("data-at-desk", atDesk);
    shelves.forEach((shelf) => {
      const dist = Number(shelf.dataset.pair) - station;
      shelf.dataset.dist = dist < 0 ? "behind" : String(Math.min(dist, 3));
      shelf.tabIndex = dist < 0 ? -1 : 0;
    });

    const last = station >= stations - 1;
    forwardLabel.textContent = atDesk ? "Search the library" : last ? "Walk to the library computer" : "Walk forward";
    forward.setAttribute("aria-label", atDesk ? "Search the library" : last ? "Walk to the library computer" : "Walk forward to the next bookshelves");
    back.hidden = station === 0 && !atDesk;
    exit.hidden = !back.hidden;
    monitor.setAttribute("aria-label", atDesk ? "Search the library" : "Walk to the library computer");
    deskChip.hidden = atDesk;

    stationLabel.textContent = atDesk ? "Library computer" : `Aisle ${station + 1} of ${stations}`;
    stage.querySelectorAll("[data-pip]").forEach((pip) => {
      pip.toggleAttribute("data-on", Number(pip.dataset.pip) === (atDesk ? stations : station));
    });
    stage.querySelectorAll("[data-hud-pair]").forEach((row) => { row.hidden = atDesk || Number(row.dataset.hudPair) !== station; });
    hudDesk.hidden = !atDesk;
  }

  function walk(step) {
    if (openCase) return;
    if (atDesk) {
      if (step < 0) { atDesk = false; render(); } else goSearch();
      return;
    }
    if (step > 0 && station >= stations - 1) return toDesk();
    const next = Math.max(0, Math.min(stations - 1, station + step));
    if (next === station) return;
    station = next;
    render();
  }

  function toDesk({ instant = false } = {}) {
    if (openCase) closeShelf();
    station = stations - 1;
    atDesk = true;
    if (instant) stage.setAttribute("data-snap", "");
    render();
    if (instant) requestAnimationFrame(() => requestAnimationFrame(() => stage.removeAttribute("data-snap")));
  }

  function goSearch() {
    if (stage.hasAttribute("data-to-search")) return;
    stage.setAttribute("data-to-search", "");
    setTimeout(() => { window.location.href = stage.dataset.searchHref; }, reduced ? 100 : 950);
  }

  function openShelf(slug, { instant = false } = {}) {
    const shelf = shelves.find((s) => s.dataset.shelf === slug);
    const bookcase = cases.find((c) => c.dataset.case === slug);
    if (!shelf || !bookcase) return;
    returnFocus = document.activeElement;
    station = Number(shelf.dataset.pair);
    atDesk = false;
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
  stage.querySelectorAll("[data-desk]").forEach((b) => b.addEventListener("click", () => (atDesk ? goSearch() : toDesk())));
  stage.querySelector("[data-search]").addEventListener("click", goSearch);

  document.addEventListener("keydown", (e) => {
    if (e.target.closest("input, textarea, select")) return;
    if (e.key === "Escape") closeShelf();
    else if (!openCase && e.key === "ArrowUp") { e.preventDefault(); walk(1); }
    else if (!openCase && e.key === "ArrowDown") { e.preventDefault(); station === 0 && !atDesk ? leave() : walk(-1); }
  });

  window.addEventListener("pageshow", (e) => {
    if (e.persisted) {
      stage.removeAttribute("data-leaving");
      stage.removeAttribute("data-to-search");
    }
  });

  // Clean ?from=gate / ?shelf=… / ?at=desk off the address bar once handled.
  const params = new URLSearchParams(window.location.search);
  if (params.has("from") || params.has("shelf") || params.has("at")) history.replaceState(null, "", window.location.pathname);

  render();
  if (stage.dataset.open) openShelf(stage.dataset.open, { instant: true });
  else if (stage.hasAttribute("data-at-desk-start")) toDesk({ instant: true });
})();
