// REST API reference: makes each endpoint dropdown deep-linkable.
//
// sphinx-design renders `.. dropdown:: ... :name: ...` as a plain
// <details id="..."> element -- collapsed by default, and browsers don't
// auto-expand a <details> just because its id is the URL's hash target.
// This opens the right dropdown (and scrolls to it) on load/hash-change,
// and keeps the URL in sync when a reader opens one manually so the
// address bar always has a copy-able link to the dropdown they're looking at.
(function () {
  function openTargetDropdown() {
    if (!location.hash) return;
    var id;
    try {
      id = decodeURIComponent(location.hash.slice(1));
    } catch (e) {
      return;
    }
    var el = document.getElementById(id);
    if (!el) return;
    var details = el.closest('details.sd-dropdown');
    if (details && !details.open) {
      details.open = true;
    }
    el.scrollIntoView();
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('details.sd-dropdown[id]').forEach(function (details) {
      details.addEventListener('toggle', function () {
        if (details.open) {
          history.replaceState(null, '', '#' + details.id);
        }
      });
    });

    openTargetDropdown();
    window.addEventListener('hashchange', openTargetDropdown);
  });
})();
