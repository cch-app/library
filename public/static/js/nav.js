// Collapsible site menu on small screens.
(() => {
  document.querySelectorAll("[data-menu]").forEach((header) => {
    const toggle = header.querySelector("[data-menu-toggle]");
    if (!toggle) return;
    const setOpen = (open) => {
      header.toggleAttribute("data-menu-open", open);
      toggle.setAttribute("aria-expanded", String(open));
      toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
      toggle.querySelector(".menu-icon-open")?.classList.toggle("hidden", open);
      toggle.querySelector(".menu-icon-close")?.classList.toggle("hidden", !open);
    };
    toggle.addEventListener("click", () => setOpen(!header.hasAttribute("data-menu-open")));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && header.hasAttribute("data-menu-open")) {
        setOpen(false);
        toggle.focus();
      }
    });
    document.addEventListener("click", (e) => {
      if (header.hasAttribute("data-menu-open") && !header.contains(e.target)) setOpen(false);
    });
  });
})();
