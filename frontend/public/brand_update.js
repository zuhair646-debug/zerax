// Brand Update Detector — polls /api/brand/version every 5 min.
// When the version increases, shows a small "تحديث متاح" banner inviting
// the user to reload (and for installed PWAs, to reinstall).

(function () {
  var BACKEND = window._BRAND_BACKEND ||
    (window.process && window.process.env && window.process.env.REACT_APP_BACKEND_URL) ||
    "";
  var STORAGE_KEY = "zenrex_brand_v";
  var POLL_MS = 5 * 60 * 1000;

  function show(newV) {
    if (document.getElementById("zenrex-update-banner")) return;
    var bar = document.createElement("div");
    bar.id = "zenrex-update-banner";
    bar.style.cssText =
      "position:fixed;left:0;right:0;bottom:0;z-index:99999;" +
      "background:linear-gradient(90deg,#f59e0b,#ef4444);" +
      "color:#0a0a14;padding:14px 18px;font:600 14px/1.4 system-ui,sans-serif;" +
      "display:flex;justify-content:space-between;align-items:center;" +
      "box-shadow:0 -6px 24px rgba(0,0,0,.35);direction:rtl";
    bar.innerHTML =
      '<span>⬇️ تحديث جديد للمنصة متاح (إصدار ' + newV + ') — أعد التحميل لتظهر آخر التغييرات.</span>' +
      '<div style="display:flex;gap:8px">' +
      '<button id="zb-reload" style="background:#0a0a14;color:#fff;border:0;padding:8px 16px;border-radius:6px;cursor:pointer;font-weight:700">إعادة تحميل</button>' +
      '<button id="zb-later" style="background:transparent;color:#0a0a14;border:1px solid #0a0a14;padding:8px 12px;border-radius:6px;cursor:pointer">لاحقاً</button>' +
      '</div>';
    document.body.appendChild(bar);
    document.getElementById("zb-reload").onclick = function () {
      try { localStorage.setItem(STORAGE_KEY, String(newV)); } catch (e) {}
      // For installed PWA: unregister SW to force fresh fetch on next launch
      if ("serviceWorker" in navigator) {
        navigator.serviceWorker.getRegistrations().then(function (regs) {
          regs.forEach(function (r) { r.update().catch(function () {}); });
        });
      }
      window.location.reload(true);
    };
    document.getElementById("zb-later").onclick = function () {
      bar.remove();
    };
  }

  function check() {
    fetch(BACKEND + "/api/brand/version", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var v = parseInt(d.version || 1, 10);
        var stored = parseInt(localStorage.getItem(STORAGE_KEY) || "0", 10);
        if (!stored) {
          // First visit — just remember the current version, no banner.
          try { localStorage.setItem(STORAGE_KEY, String(v)); } catch (e) {}
          return;
        }
        if (v > stored) show(v);
      })
      .catch(function () { /* silent */ });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", check);
  } else {
    setTimeout(check, 1500);
  }
  setInterval(check, POLL_MS);
})();
