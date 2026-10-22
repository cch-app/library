// The library computer: powers on (boot), searches, and switches off before leaving.
(() => {
  const stage = document.querySelector("[data-terminal]");
  if (!stage) return;

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const category = stage.querySelector("[data-category]");
  const book = stage.querySelector("[data-book]");
  let bootTimer;

  function ready() {
    if (stage.dataset.phase !== "boot") return;
    clearTimeout(bootTimer);
    stage.dataset.phase = "ready";
    category?.focus({ preventScroll: true });
  }

  if (stage.dataset.phase === "boot") {
    bootTimer = setTimeout(ready, reduced ? 300 : 3500);
    stage.querySelector("[data-skip]")?.addEventListener("click", ready);
    document.addEventListener("keydown", ready, { once: true });
  }

  // BOOK NAME only lists the books of the chosen CATEGORY. The list is rebuilt rather than
  // hidden, because browsers (iOS Safari in particular) ignore hidden options in a <select>.
  const groupsTemplate = stage.querySelector("template[data-book-groups]");
  const allBooks = book?.querySelector("[data-all-books]");
  function filterBooks() {
    const realm = category.value;
    const current = book.value;
    book.querySelectorAll("optgroup").forEach((group) => group.remove());
    groupsTemplate.content.querySelectorAll("optgroup").forEach((group) => {
      if (!realm || group.dataset.realm === realm) book.append(group.cloneNode(true));
    });
    book.value = [...book.options].some((o) => o.value === current) ? current : "";
    allBooks.textContent = realm ? `All books in ${category.selectedOptions[0].text}` : "All books";
  }
  if (category && book && groupsTemplate && allBooks) category.addEventListener("change", filterBooks);

  // Leaving the terminal (opening a result or the power button) switches it off first.
  stage.addEventListener("click", (e) => {
    const link = e.target.closest("a[data-power-link]");
    if (!link || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    e.preventDefault();
    if (stage.dataset.phase === "shutdown") return;
    clearTimeout(bootTimer);
    stage.dataset.phase = "shutdown";
    setTimeout(() => { window.location.href = link.href; }, reduced ? 150 : 1250);
  });

  // Back button from a book: show the terminal on again instead of a dark screen.
  window.addEventListener("pageshow", (e) => {
    if (e.persisted && stage.dataset.phase === "shutdown") stage.dataset.phase = "ready";
  });
})();
