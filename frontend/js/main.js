/* Shared navigation: welcome model list, model views, and appearance. */

(function () {
  "use strict";

  const bridge = window.recogniser.bridge;
  const views = window.recogniser.views;

  const ARROW_ICON =
    '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" ' +
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true" focusable="false">' +
    '<path d="M3 8h9M8.5 4.5 12 8l-3.5 3.5"></path></svg>';

  const dom = {
    welcomeView: document.getElementById("welcome-view"),
    modelView: document.getElementById("model-view"),
    modelList: document.getElementById("model-list"),
    modelCount: document.getElementById("model-count"),
    modelTitle: document.getElementById("model-title"),
    modelDescription: document.getElementById("model-description"),
    modelInstructions: document.getElementById("model-instructions"),
    settingsButton: document.getElementById("settings-button"),
    settingsMenu: document.getElementById("settings-menu"),
    themeOptions: document.getElementById("theme-options"),
    modeTabs: document.getElementById("mode-tabs"),
    modePanel: document.getElementById("mode-panel"),
    modeHint: document.getElementById("mode-hint"),
    recogniseButton: document.getElementById("recognise-button"),
    resultArea: document.getElementById("result-area"),
    statusMessage: document.getElementById("status-message"),
    backButton: document.getElementById("back-button"),
    brandButton: document.getElementById("brand-button")
  };

  const state = {
    models: [],
    loaded: false,
    loadError: false,
    currentModelId: null,
    activeModeId: null,
    hostToken: 0,
    submission: null,
    recognitionToken: 0,
    recognitionBusy: false
  };

  function make(tagName, className, text) {
    const element = document.createElement(tagName);
    if (className) {
      element.className = className;
    }
    if (text !== undefined) {
      element.textContent = text;
    }
    return element;
  }

  function clearElement(element) {
    while (element.firstChild) {
      element.removeChild(element.firstChild);
    }
  }

  function currentModel() {
    return (
      state.models.find((model) => model.id === state.currentModelId) || null
    );
  }

  function setStatus(message, tone) {
    dom.statusMessage.textContent = message;
    dom.statusMessage.dataset.tone = tone || "info";
  }

  function clearResult() {
    clearElement(dom.resultArea);
    dom.resultArea.hidden = true;
    delete dom.resultArea.dataset.tone;
  }

  function showPrediction(digit) {
    clearElement(dom.resultArea);
    dom.resultArea.append(
      make("p", "result-label", "Predicted digit"),
      make("p", "result-digit", String(digit))
    );
    dom.resultArea.dataset.tone = "success";
    dom.resultArea.hidden = false;
  }

  function renderWelcome() {
    clearElement(dom.modelList);
    dom.modelCount.textContent = "";

    if (state.loadError) {
      const box = make("div", "empty-state");
      box.append(
        make("p", "empty-title", "Models aren’t available"),
        make(
          "p",
          null,
          "The model list could not be loaded from the application backend."
        )
      );
      const retry = make("button", "button secondary", "Try again");
      retry.type = "button";
      retry.addEventListener("click", loadModels);
      box.append(retry);
      dom.modelList.append(box);
      return;
    }

    if (!state.loaded) {
      dom.modelList.append(make("p", "placeholder", "Loading models…"));
      return;
    }

    dom.modelCount.textContent =
      state.models.length === 1
        ? "1 available"
        : state.models.length + " available";

    if (state.models.length === 0) {
      dom.modelList.append(
        make("p", "placeholder", "No models are registered.")
      );
      return;
    }

    state.models.forEach((model) => {
      const card = make("button", "model-card");
      card.type = "button";
      card.addEventListener("click", () => openModel(model.id));

      const body = make("span", "model-card-body");
      body.append(
        make("span", "model-card-name", model.display_name),
        make("span", "model-card-description", model.description)
      );

      const action = make("span", "model-card-action", "Open");
      action.insertAdjacentHTML("beforeend", ARROW_ICON);

      card.append(body, action);
      dom.modelList.append(card);
    });
  }

  function renderModeTabs() {
    clearElement(dom.modeTabs);
    const model = currentModel();
    if (!model) {
      return;
    }

    model.input_modes.forEach((mode) => {
      const tab = make("button", "mode-tab", mode.label);
      tab.type = "button";
      tab.id = "mode-tab-" + mode.id;
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-controls", "mode-panel");
      const selected = mode.id === state.activeModeId;
      tab.setAttribute("aria-selected", selected ? "true" : "false");
      tab.tabIndex = selected ? 0 : -1;
      tab.addEventListener("click", () => selectMode(mode.id));
      dom.modeTabs.append(tab);
    });
  }

  function syncModeTabs() {
    Array.from(dom.modeTabs.children).forEach((tab) => {
      const selected = tab.id === "mode-tab-" + state.activeModeId;
      tab.setAttribute("aria-selected", selected ? "true" : "false");
      tab.tabIndex = selected ? 0 : -1;
    });
  }

  function createModeHost() {
    state.hostToken += 1;
    const hostId = state.hostToken;

    function isCurrent() {
      return hostId === state.hostToken;
    }

    return {
      setStatus(message, tone) {
        if (isCurrent()) {
          setStatus(message, tone);
        }
      },
      setReady(ready, reason) {
        if (!isCurrent()) {
          return;
        }
        dom.recogniseButton.title = ready ? "" : reason || "";
        dom.recogniseButton.disabled = !ready || state.recognitionBusy;
      },
      provideSubmission(handlers) {
        if (isCurrent()) {
          state.submission = handlers;
        }
      },
      inputChanged() {
        if (!isCurrent()) {
          return;
        }
        state.recognitionToken += 1;
        state.recognitionBusy = false;
        dom.recogniseButton.textContent = "Recognise";
        dom.recogniseButton.disabled = true;
        clearResult();
        setStatus("");
      }
    };
  }

  function applyResult(result) {
    if (!result || typeof result !== "object") {
      clearResult();
      setStatus(
        "The application returned an unexpected response. Try again.",
        "error"
      );
      return;
    }

    if (result.status === "ok" && Number.isInteger(result.prediction)) {
      showPrediction(result.prediction);
      setStatus(
        result.message || "Recognised digit: " + result.prediction + ".",
        "success"
      );
      return;
    }

    clearResult();
    if (result.status === "uncertain" || result.status === "invalid_input") {
      setStatus(
        result.message || "The image could not be recognised.",
        "warning"
      );
    } else {
      setStatus(
        result.message || "The model could not be run. Try again.",
        "error"
      );
    }
  }

  async function recogniseCurrentInput() {
    if (state.recognitionBusy) {
      return;
    }

    const submission = state.submission;
    if (
      !submission ||
      typeof submission.isReady !== "function" ||
      typeof submission.submit !== "function" ||
      !submission.isReady()
    ) {
      return;
    }

    const token = ++state.recognitionToken;
    state.recognitionBusy = true;
    dom.recogniseButton.disabled = true;
    dom.recogniseButton.textContent = "Recognising…";
    clearResult();
    setStatus("Recognising the digit…", "info");

    try {
      const result = await submission.submit();
      if (token !== state.recognitionToken) {
        return;
      }
      applyResult(result);
    } catch (error) {
      if (token !== state.recognitionToken) {
        return;
      }
      console.error("Recognition request failed:", error);
      clearResult();
      setStatus("Recognition could not be completed. Try again.", "error");
    } finally {
      if (token === state.recognitionToken) {
        state.recognitionBusy = false;
        dom.recogniseButton.textContent = "Recognise";
        dom.recogniseButton.disabled = !(
          state.submission &&
          typeof state.submission.isReady === "function" &&
          state.submission.isReady()
        );
      }
    }
  }

  function renderModePanel() {
    clearElement(dom.modePanel);
    clearResult();
    dom.modeHint.textContent = "";
    state.hostToken += 1;
    state.submission = null;
    state.recognitionToken += 1;
    state.recognitionBusy = false;
    dom.recogniseButton.disabled = true;
    dom.recogniseButton.textContent = "Recognise";
    dom.recogniseButton.title = "";
    dom.modePanel.tabIndex = 0;
    setStatus("");

    const model = currentModel();
    if (!model) {
      return;
    }

    const mode = model.input_modes.find(
      (entry) => entry.id === state.activeModeId
    );
    if (!mode) {
      dom.modePanel.append(
        make("p", "mode-note", "This model has no input modes yet.")
      );
      setStatus("This model has no input modes yet.", "warning");
      return;
    }

    const view = views[model.frontend_view];
    if (!view || typeof view.renderMode !== "function") {
      dom.modePanel.append(
        make("p", "mode-note", "This model does not have an interface yet.")
      );
      setStatus("This model does not have an interface yet.", "error");
      return;
    }

    view.renderMode(mode, dom.modePanel, model, createModeHost());
    dom.modePanel.setAttribute("aria-labelledby", "mode-tab-" + mode.id);
    dom.modeHint.textContent = mode.hint;
  }

  function selectMode(modeId) {
    const model = currentModel();
    if (!model) {
      return;
    }
    const mode = model.input_modes.find((entry) => entry.id === modeId);
    if (!mode) {
      return;
    }

    state.activeModeId = mode.id;
    syncModeTabs();
    renderModePanel();
  }

  function renderModelView() {
    const model = currentModel();
    if (!model) {
      return;
    }

    dom.modelTitle.textContent = model.display_name;
    dom.modelDescription.textContent = model.description;
    dom.modelInstructions.textContent = model.instructions;

    renderModeTabs();
    renderModePanel();
  }

  function openModel(modelId) {
    const model = state.models.find((entry) => entry.id === modelId);
    if (!model) {
      return;
    }

    state.currentModelId = model.id;
    state.activeModeId = model.input_modes.length
      ? model.input_modes[0].id
      : null;

    renderModelView();
    dom.welcomeView.hidden = true;
    dom.modelView.hidden = false;
    closeSettingsMenu();
    window.scrollTo(0, 0);
  }

  function showWelcome() {
    state.currentModelId = null;
    state.activeModeId = null;
    state.hostToken += 1;
    state.submission = null;
    state.recognitionToken += 1;
    state.recognitionBusy = false;
    dom.recogniseButton.textContent = "Recognise";
    dom.recogniseButton.disabled = true;
    dom.recogniseButton.title = "";
    clearResult();
    setStatus("");
    dom.modelView.hidden = true;
    dom.welcomeView.hidden = false;
    closeSettingsMenu();
    window.scrollTo(0, 0);
  }

  function setSettingsMenuOpen(open) {
    dom.settingsMenu.hidden = !open;
    dom.settingsButton.setAttribute(
      "aria-expanded",
      open ? "true" : "false"
    );
  }

  function closeSettingsMenu() {
    setSettingsMenuOpen(false);
  }

  function bindEvents() {
    dom.brandButton.addEventListener("click", showWelcome);
    dom.backButton.addEventListener("click", showWelcome);
    dom.recogniseButton.addEventListener("click", recogniseCurrentInput);

    dom.settingsButton.addEventListener("click", () => {
      const willOpen = dom.settingsMenu.hidden;
      closeSettingsMenu();
      setSettingsMenuOpen(willOpen);
    });

    dom.themeOptions.addEventListener("click", closeSettingsMenu);

    dom.modeTabs.addEventListener("keydown", (event) => {
      const tabs = Array.from(dom.modeTabs.children);
      const currentIndex = tabs.indexOf(document.activeElement);
      if (currentIndex === -1) {
        return;
      }

      let nextIndex = null;
      if (event.key === "ArrowRight") {
        nextIndex = (currentIndex + 1) % tabs.length;
      } else if (event.key === "ArrowLeft") {
        nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
      } else if (event.key === "Home") {
        nextIndex = 0;
      } else if (event.key === "End") {
        nextIndex = tabs.length - 1;
      }

      if (nextIndex === null) {
        return;
      }

      event.preventDefault();
      const nextTab = tabs[nextIndex];
      nextTab.focus();
      nextTab.click();
    });

    document.addEventListener("click", (event) => {
      if (
        event.target instanceof Element &&
        event.target.closest(".menu-root")
      ) {
        return;
      }
      closeSettingsMenu();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeSettingsMenu();
      }
    });
  }

  async function loadModels() {
    state.loaded = false;
    state.loadError = false;
    renderWelcome();

    try {
      state.models = await bridge.getModels();
      state.loaded = true;
    } catch (error) {
      console.error("Could not load the model registry:", error);
      state.models = [];
      state.loadError = true;
    }

    renderWelcome();

    if (state.currentModelId) {
      if (state.models.some((model) => model.id === state.currentModelId)) {
        renderModelView();
      } else {
        showWelcome();
      }
    }

    window.recogniser.appReady = true;
  }

  window.recogniser.appReady = false;
  bindEvents();
  renderWelcome();
  loadModels();
})();
