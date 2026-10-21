// The gate: closed → ajar (Gatekeeper asks) → entering (Yes) → navigate to the aisle.
// "No" closes the door again. Returning from the library (/?from=library) plays it in reverse.
(() => {
  const stage = document.querySelector("[data-gate]");
  if (!stage) return;

  const door = stage.querySelector("[data-door]");
  const dialog = stage.querySelector("[data-dialog]");
  const yes = stage.querySelector('[data-choice="yes"]');
  const no = stage.querySelector('[data-choice="no"]');
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const timers = new Set();

  const later = (fn, ms) => {
    const id = setTimeout(() => { timers.delete(id); fn(); }, reduced ? Math.min(ms, 300) : ms);
    timers.add(id);
  };
  const clearTimers = () => { timers.forEach(clearTimeout); timers.clear(); };
  const phase = () => stage.dataset.phase;
  const setPhase = (p, { snap = false } = {}) => {
    stage.dataset.phase = p;
    stage.toggleAttribute("data-snap", snap);
  };

  door.addEventListener("click", () => {
    if (phase() !== "closed") return;
    setPhase("ajar");
    // Move focus into the dialog once it has appeared, then onto "Yes" once the choices show.
    later(() => dialog.focus({ preventScroll: true }), 1200);
    later(() => yes.focus({ preventScroll: true }), 2600);
  });

  yes.addEventListener("click", () => {
    if (phase() !== "ajar") return;
    clearTimers();
    setPhase("entering");
    later(() => { window.location.href = stage.dataset.next; }, 2400);
  });

  const closeDoor = () => {
    if (phase() !== "ajar") return;
    clearTimers();
    setPhase("closed");
    door.focus({ preventScroll: true });
  };
  no.addEventListener("click", closeDoor);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDoor(); });

  // Back from the library: start inside the light, then pull back and close the doors.
  if (stage.hasAttribute("data-returning")) {
    history.replaceState(null, "", window.location.pathname);
    requestAnimationFrame(() => requestAnimationFrame(() => {
      setPhase("closing");
      later(() => setPhase("closed"), 3300);
    }));
  }

  // Coming back with the browser's Back button restores a frozen page; reset it.
  window.addEventListener("pageshow", (e) => {
    if (e.persisted && phase() !== "closed") {
      clearTimers();
      setPhase("closed", { snap: true });
    }
  });
})();
