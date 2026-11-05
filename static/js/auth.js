(function () {
  var shell = document.querySelector("[data-auth]");
  if (!shell) return;
  var tabs = shell.querySelectorAll(".auth-tab");
  var links = shell.querySelectorAll("[data-mode-tab]");
  var panels = shell.querySelectorAll("[data-panel]");

  function setMode(mode, push) {
    if (shell.dataset.mode === mode) return;
    shell.dataset.mode = mode;
    tabs.forEach(function (t) { t.setAttribute("aria-selected", t.dataset.modeTab === mode ? "true" : "false"); });
    panels.forEach(function (p) {
      if (p.dataset.panel === mode) p.removeAttribute("inert"); else p.setAttribute("inert", "");
    });
    if (push && window.history && history.replaceState) {
      history.replaceState(null, "", mode === "login" ? shell.dataset.urlLogin : shell.dataset.urlRegister);
    }
    var first = shell.querySelector('[data-panel="' + mode + '"] input:not([type="hidden"])');
    if (first) setTimeout(function () { first.focus({ preventScroll: true }); }, 380);
  }
  links.forEach(function (a) {
    a.addEventListener("click", function (e) { e.preventDefault(); setMode(a.dataset.modeTab, true); });
  });

  // Parolni ko'rsatish / yashirish
  shell.querySelectorAll(".pw-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var input = btn.parentNode.querySelector("input");
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.querySelector("i").className = show ? "bi bi-eye-slash" : "bi bi-eye";
    });
  });
})();
