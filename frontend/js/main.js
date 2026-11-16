/* Shared navigation: welcome category list, category views, and appearance. */

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
    categoryView: document.getElementById("category-view"),
    categoryList: document.getElementById("category-list"),
    categoryCount: document.getElementById("category-count"),
    categoryTitle: document.getElementById("category-title"),
    categoryGuidance: document.getElementById("category-guidance"),
    modelDescription: document.getElementById("model-description"),
    modelInstructions: document.getElementById("model-instructions"),
    modelSelect: document.getElementById("model-select"),
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
    categories: [],
    loaded: false,
    loadError: false,
    currentCategoryId: null,
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

  function currentCategory() {
    return (
      state.categories.find(
        (category) => category.id === state.currentCategoryId
      ) || null
    );
  }

  function currentModel() {
    const category = currentCategory();
    if (!category || !Array.isArray(category.models)) {
      return null;
    }
    return (
      category.models.find((model) => model.id === state.currentModelId) || null
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

  /* A category view owns the markup for a successful result. It returns true
     after adding content; a missing renderer, or one that declines the result,
     still leaves the recognition itself successful. */
  function showCategoryResult(result) {
    clearResult();
    const category = currentCategory();
    const view = category ? views[category.frontend_view] : null;
    if (!view || typeof view.renderResult !== "function") {
      return false;
    }

    let rendered = false;
    try {
      rendered = view.renderResult(result, dom.resultArea) === true;
    } catch (error) {
      console.error("Category result renderer failed:", error);
    }

    if (!rendered) {
      clearResult();
      return false;
    }

    dom.resultArea.dataset.tone = "success";
    dom.resultArea.hidden = false;
    return true;
  }

  function renderWelcome() {
    clearElement(dom.categoryList);
    dom.categoryCount.textContent = "";

    if (state.loadError) {
      const box = make("div", "empty-state");
      box.append(
        make("p", "empty-title", "Categories aren’t available"),
        make(
          "p",
          null,
          "The category list could not be loaded from the application backend."
        )
      );
      const retry = make("button", "button secondary", "Try again");
      retry.type = "button";
      retry.addEventListener("click", loadCategories);
      box.append(retry);
      dom.categoryList.append(box);
      return;
    }

    if (!state.loaded) {
      dom.categoryList.append(
        make("p", "placeholder", "Loading categories…")
      );
      return;
    }

    dom.categoryCount.textContent =
      state.categories.length === 1
        ? "1 available"
        : state.categories.length + " available";

    if (state.categories.length === 0) {
      dom.categoryList.append(
        make("p", "placeholder", "No categories are registered.")
      );
      return;
    }

    state.categories.forEach((category) => {
      const card = make("button", "category-card");
      card.type = "button";
      card.addEventListener("click", () => openCategory(category.id));

      const body = make("span", "category-card-body");
      body.append(
        make("span", "category-card-name", category.label),
        make("span", "category-card-description", category.description)
      );

      const action = make("span", "category-card-action", "Open");
      action.insertAdjacentHTML("beforeend", ARROW_ICON);

      card.append(body, action);
      dom.categoryList.append(card);
    });
  }

  function renderModelSelect() {
    clearElement(dom.modelSelect);
    const category = currentCategory();
    if (!category) {
      dom.modelSelect.disabled = true;
      return;
    }

    const models = Array.isArray(category.models) ? category.models : [];
    models.forEach((model) => {
      const option = document.createElement("option");
      option.value = model.id;
      option.textContent = model.display_name;
      dom.modelSelect.append(option);
    });

    /* The dropdown stays visible and enabled with one model, so another
       registered model can be selected without changing this view. */
    dom.modelSelect.disabled = models.length === 0;
    dom.modelSelect.value = state.currentModelId || "";
  }

  function updateModelText() {
    const model = currentModel();
    dom.modelDescription.textContent = model ? model.description : "";
    dom.modelInstructions.textContent = model ? model.instructions : "";
  }

  function renderModeTabs() {
    clearElement(dom.modeTabs);
    const category = currentCategory();
    if (!category) {
      return;
    }

    category.input_modes.forEach((mode) => {
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
      },
      /* The mounted input reads the current category and model when it
         submits, so a model switch keeps the same input panel. */
      getCategory() {
        return currentCategory();
      },
      getModel() {
        return currentModel();
      }
    };
  }

  function resetRecognitionState() {
    state.recognitionToken += 1;
    state.recognitionBusy = false;
    dom.recogniseButton.textContent = "Recognise";
  }

  function updateRecognitionReadiness() {
    const submission = state.submission;
    const ready =
      !state.recognitionBusy &&
      submission !== null &&
      typeof submission.isReady === "function" &&
      Boolean(submission.isReady());
    dom.recogniseButton.disabled = !ready;
  }

  function selectModel(modelId) {
    const category = currentCategory();
    if (!category || modelId === state.currentModelId) {
      return;
    }

    const model = (category.models || []).find((entry) => entry.id === modelId);
    if (!model) {
      dom.modelSelect.value = state.currentModelId || "";
      return;
    }

    state.currentModelId = model.id;
    dom.modelSelect.value = model.id;
    updateModelText();

    /* The mounted input is reused unchanged. A pending request for the
       previous model can no longer update the view, and a result or message
       produced by that model is no longer relevant. */
    resetRecognitionState();
    clearResult();
    setStatus("");
    updateRecognitionReadiness();
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

    if (result.status === "ok") {
      showCategoryResult(result);
      setStatus(result.message || "Recognised.", "success");
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

    if (!currentModel()) {
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
    setStatus("Recognising…", "info");

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

    const category = currentCategory();
    if (!category) {
      return;
    }

    const model = currentModel();
    if (!model) {
      dom.modePanel.append(
        make("p", "mode-note", "This category has no models registered yet.")
      );
      setStatus("This category has no models registered yet.", "warning");
      return;
    }

    const mode = category.input_modes.find(
      (entry) => entry.id === state.activeModeId
    );
    if (!mode) {
      dom.modePanel.append(
        make("p", "mode-note", "This category has no input modes yet.")
      );
      setStatus("This category has no input modes yet.", "warning");
      return;
    }

    const view = views[category.frontend_view];
    if (!view || typeof view.renderMode !== "function") {
      dom.modePanel.append(
        make("p", "mode-note", "This category does not have an interface yet.")
      );
      setStatus("This category does not have an interface yet.", "error");
      return;
    }

    view.renderMode(mode, dom.modePanel, createModeHost());
    dom.modePanel.setAttribute("aria-labelledby", "mode-tab-" + mode.id);
    dom.modeHint.textContent = mode.hint;
  }

  function selectMode(modeId) {
    const category = currentCategory();
    if (!category) {
      return;
    }
    const mode = category.input_modes.find((entry) => entry.id === modeId);
    if (!mode) {
      return;
    }

    state.activeModeId = mode.id;
    syncModeTabs();
    renderModePanel();
  }

  function renderCategoryView() {
    const category = currentCategory();
    if (!category) {
      return;
    }

    dom.categoryTitle.textContent = category.label;
    dom.categoryGuidance.textContent = category.guidance;

    renderModelSelect();
    updateModelText();
    renderModeTabs();
    renderModePanel();
  }

  function openCategory(categoryId) {
    const category = state.categories.find((entry) => entry.id === categoryId);
    if (!category) {
      return;
    }

    const models = Array.isArray(category.models) ? category.models : [];
    state.currentCategoryId = category.id;
    state.currentModelId = models.length ? models[0].id : null;
    state.activeModeId = category.input_modes.length
      ? category.input_modes[0].id
      : null;

    renderCategoryView();
    dom.welcomeView.hidden = true;
    dom.categoryView.hidden = false;
    closeSettingsMenu();
    window.scrollTo(0, 0);
  }

  function showWelcome() {
    state.currentCategoryId = null;
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
    dom.categoryView.hidden = true;
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

    dom.modelSelect.addEventListener("change", () => {
      selectModel(dom.modelSelect.value);
    });

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

  async function loadCategories() {
    state.loaded = false;
    state.loadError = false;
    renderWelcome();

    try {
      state.categories = await bridge.getCategories();
      state.loaded = true;
    } catch (error) {
      console.error("Could not load the category registry:", error);
      state.categories = [];
      state.loadError = true;
    }

    renderWelcome();

    if (state.currentCategoryId) {
      if (
        state.categories.some(
          (category) => category.id === state.currentCategoryId
        )
      ) {
        renderCategoryView();
      } else {
        showWelcome();
      }
    }

    window.recogniser.appReady = true;
  }

  window.recogniser.appReady = false;
  bindEvents();
  renderWelcome();
  loadCategories();
})();