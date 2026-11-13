/* Access to the Python API exposed by pywebview. */

(function () {
  "use strict";

  window.recogniser = window.recogniser || {};

  function waitForApi(timeoutMs) {
    if (window.pywebview && window.pywebview.api) {
      return Promise.resolve(window.pywebview.api);
    }

    return new Promise((resolve, reject) => {
      const timer = window.setTimeout(() => {
        window.removeEventListener("pywebviewready", onReady);
        reject(new Error("The application backend did not become available."));
      }, timeoutMs);

      function onReady() {
        window.clearTimeout(timer);
        if (window.pywebview && window.pywebview.api) {
          resolve(window.pywebview.api);
          return;
        }
        reject(new Error("The application backend is not ready."));
      }

      window.addEventListener("pywebviewready", onReady, { once: true });
    });
  }

  async function getModels() {
    const api = await waitForApi(10000);
    const models = await api.get_models();
    if (!Array.isArray(models)) {
      throw new Error("The backend returned an unexpected model registry.");
    }
    return models;
  }

  window.recogniser.bridge = { getModels };
})();
