(function () {
  var dlg = document.getElementById("langDialog");
  var DRAFT = "inventrackDraft";
  var FIELDS = 'input[type="text"],input[type="email"],input[type="tel"],input[type="number"]';

  // Til almashganda sahifa qayta yuklanadi — kiritilgan matnlar yo'qolmasin (parollar saqlanmaydi)
  function saveDraft() {
    try {
      var data = {};
      document.querySelectorAll(FIELDS).forEach(function (el) {
        if (el.id && el.value && !dlg.contains(el)) data[el.id] = el.value;
      });
      sessionStorage.setItem(DRAFT, JSON.stringify({ path: location.pathname, data: data }));
    } catch (e) {}
  }
  function restoreDraft() {
    try {
      var raw = sessionStorage.getItem(DRAFT);
      if (!raw) return;
      sessionStorage.removeItem(DRAFT);
      var d = JSON.parse(raw);
      if (d.path !== location.pathname) return;
      Object.keys(d.data).forEach(function (id) {
        var el = document.getElementById(id);
        if (el && !el.value) el.value = d.data[id];
      });
    } catch (e) {}
  }
  restoreDraft();
  if (!dlg || typeof dlg.showModal !== "function") return;

  function countUp() {
    dlg.querySelectorAll("[data-count]").forEach(function (el) {
      var target = parseInt(el.dataset.count, 10) || 0, start = null;
      if (!target) return;
      function step(ts) {
        if (start === null) start = ts;
        var p = Math.min((ts - start) / 900, 1);
        el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
        if (p < 1) requestAnimationFrame(step);
      }
      el.textContent = "0";
      requestAnimationFrame(step);
    });
  }
  function open() {
    if (dlg.open) return;
    dlg.showModal();
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { dlg.classList.add("is-open"); countUp(); });
    });
  }
  function close() {
    dlg.classList.remove("is-open");
    setTimeout(function () { if (dlg.open) dlg.close(); }, 260);
  }
  document.querySelectorAll("[data-lang-open]").forEach(function (b) { b.addEventListener("click", open); });
  dlg.querySelectorAll("[data-lang-close]").forEach(function (b) { b.addEventListener("click", close); });
  dlg.addEventListener("cancel", function (e) { e.preventDefault(); close(); });
  dlg.addEventListener("click", function (e) { if (e.target === dlg) close(); });
  dlg.querySelectorAll("form").forEach(function (f) { f.addEventListener("submit", saveDraft); });
})();
