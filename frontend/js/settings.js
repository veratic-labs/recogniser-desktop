/* Appearance settings: Light, Dark, and Follow system.

   The preference is intentionally in-memory only. Whether it persists across
   launches is still an open product decision, so no storage is used. */

(function () {
  "use strict";

  window.recogniser = window.recogniser || {};

  const PREFERENCES = [
    { id: "light", label: "Light" },
    { id: "dark", label: "Dark" },
    { id: "system", label: "Follow system" }
  ];

  const CHECK_ICON =
    '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" ' +
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true" focusable="false">' +
    '<path d="M3.5 8.5l3 3 6-7"></path></svg>';

  const systemQuery = window.matchMedia("(prefers-color-scheme: dark)");
  const changeListeners = new Set();
  let preference = "light";

  function resolveTheme(value) {
    if (value === "system") {
      return systemQuery.matches ? "dark" : "light";
    }
    return value;
  }

  function getState() {
    return { preference, resolved: resolveTheme(preference) };
  }

  function updateOptions() {
    document.querySelectorAll("[data-theme-preference]").forEach((button) => {
      const selected = button.dataset.themePreference === preference;
      button.setAttribute("aria-checked", selected ? "true" : "false");
    });
  }

  function apply() {
    const state = getState();
    const root = document.documentElement;
    root.dataset.theme = state.resolved;
    root.dataset.themePreference = state.preference;
    updateOptions();
    changeListeners.forEach((listener) => listener(state));
  }

  function setPreference(value) {
    if (!PREFERENCES.some((option) => option.id === value)) {
      return;
    }
    preference = value;
    apply();
  }

  function buildOptions() {
    const container = document.getElementById("theme-options");
    if (!container) {
      return;
    }

    PREFERENCES.forEach((option) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "menu-item";
      button.dataset.themePreference = option.id;
      button.setAttribute("role", "menuitemradio");
      button.setAttribute("aria-checked", "false");

      const label = document.createElement("span");
      label.className = "menu-item-label";
      label.textContent = option.label;

      const check = document.createElement("span");
      check.className = "menu-item-check";
      check.setAttribute("aria-hidden", "true");
      check.innerHTML = CHECK_ICON;

      button.append(label, check);
      button.addEventListener("click", () => setPreference(option.id));
      container.append(button);
    });
  }

  systemQuery.addEventListener("change", () => {
    if (preference === "system") {
      apply();
    }
  });

  buildOptions();
  apply();

  window.recogniser.settings = {
    getState,
    setPreference,
    onChange(listener) {
      changeListeners.add(listener);
      listener(getState());
      return () => changeListeners.delete(listener);
    }
  };
})();
