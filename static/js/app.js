(function () {
  // Mobil menyu
  var sidebar = document.getElementById("sidebar");
  var scrim = document.getElementById("scrim");
  var burger = document.getElementById("burger");
  function toggle(open) {
    if (!sidebar) return;
    sidebar.classList.toggle("open", open);
    scrim.classList.toggle("show", open);
  }
  if (burger) burger.addEventListener("click", function () { toggle(!sidebar.classList.contains("open")); });
  if (scrim) scrim.addEventListener("click", function () { toggle(false); });

  // Ochiq dropdownni tashqariga bosilganda yopish
  document.addEventListener("click", function (e) {
    document.querySelectorAll("details.menu[open]").forEach(function (d) {
      if (!d.contains(e.target)) d.removeAttribute("open");
    });
  });

  // Tasdiqlash oynasi
  document.querySelectorAll("form[data-confirm]").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      if (!window.confirm(f.dataset.confirm)) e.preventDefault();
    });
  });

  // Xabarlarni avtomatik yopish
  setTimeout(function () {
    document.querySelectorAll(".toast").forEach(function (t) { t.style.display = "none"; });
  }, 6000);
})();
