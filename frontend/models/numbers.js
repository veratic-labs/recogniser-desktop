/* Interface for recogniser 0 (numbers).

   This milestone provides the input-mode navigation only. Upload, drawing,
   preprocessing, and recognition belong to later milestones, so every control
   that would run the model is explicitly disabled. */

(function () {
  "use strict";

  window.recogniser = window.recogniser || {};
  window.recogniser.views = window.recogniser.views || {};

  const INACTIVE_CONTROL_TITLE =
    "Not available yet. Recognition is added in a later milestone.";

  /* The canvas follows the resolved theme. Its bitmap is larger than its CSS
     display size so a future drawing stays crisp as the workspace grows.
     Neither value is tied to the 28 x 28 model input. */
  const CANVAS_BITMAP_SIZE = 560;

  const CANVAS_POLARITY = {
    light: "dark_on_light",
    dark: "light_on_dark"
  };

  const CANVAS_APPEARANCE = {
    dark_on_light: "a white background and black strokes",
    light_on_dark: "a black background and white strokes"
  };

  function canvasPalette() {
    const rootStyle = window.getComputedStyle(document.documentElement);
    const settings = window.recogniser.settings;
    const resolved = settings ? settings.getState().resolved : "light";
    const polarity = CANVAS_POLARITY[resolved] || CANVAS_POLARITY.light;

    return {
      background:
        rootStyle.getPropertyValue("--color-canvas-background").trim() ||
        "#ffffff",
      stroke:
        rootStyle.getPropertyValue("--color-canvas-stroke").trim() || "#000000",
      polarity
    };
  }

  function applyCanvasTheme(canvas) {
    const palette = canvasPalette();
    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    /* This milestone has no drawn content. The drawing milestone must replace
       this fill with an in-place background/stroke conversion so an existing
       drawing keeps its geometry when the resolved theme changes. */
    context.fillStyle = palette.background;
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.strokeStyle = palette.stroke;

    canvas.dataset.canvasPolarity = palette.polarity;
    canvas.dataset.canvasBackground = palette.background;
    canvas.dataset.canvasStroke = palette.stroke;
    canvas.setAttribute(
      "aria-label",
      "Blank drawing canvas with " +
        CANVAS_APPEARANCE[palette.polarity] +
        ". Drawing input is not enabled yet."
    );
  }

  function refreshCanvasThemes() {
    document
      .querySelectorAll(".drawing-canvas")
      .forEach((canvas) => applyCanvasTheme(canvas));
  }

  const settings = window.recogniser.settings;
  if (settings) {
    settings.onChange(refreshCanvasThemes);
  }

  function createNote(text) {
    const note = document.createElement("p");
    note.className = "mode-note";
    note.textContent = text;
    return note;
  }

  function renderUpload(container, model) {
    const area = document.createElement("div");
    area.className = "input-area";

    const title = document.createElement("p");
    title.className = "input-area-title";
    title.textContent = "Image upload";

    const description = document.createElement("p");
    description.className = "input-area-text";
    description.textContent =
      "Choosing a local image and preparing its " +
      model.input_label +
      " model input will be enabled when recognition is connected.";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "button secondary";
    button.textContent = "Choose image";
    button.disabled = true;
    button.title = INACTIVE_CONTROL_TITLE;

    area.append(title, description, button);
    container.append(area);
    container.append(
      createNote(
        "Not implemented in this milestone. No image is selected or processed."
      )
    );
  }

  function renderDrawing(container) {
    const frame = document.createElement("div");
    frame.className = "canvas-frame";

    const canvas = document.createElement("canvas");
    canvas.className = "drawing-canvas";
    canvas.width = CANVAS_BITMAP_SIZE;
    canvas.height = CANVAS_BITMAP_SIZE;
    canvas.setAttribute("role", "img");
    applyCanvasTheme(canvas);

    frame.append(canvas);
    container.append(frame);
    container.append(
      createNote(
        "Drawing is not implemented in this milestone. The canvas follows " +
          "the resolved appearance theme: white with black strokes in Light, " +
          "black with white strokes in Dark. Freehand input and Clear arrive " +
          "later."
      )
    );
  }

  const renderers = {
    upload: renderUpload,
    drawing: renderDrawing
  };

  function renderMode(mode, container, model) {
    const render = renderers[mode.id];
    if (render) {
      render(container, model);
      return;
    }
    container.append(createNote("This input mode has no interface yet."));
  }

  window.recogniser.views.numbers = { renderMode };
})();
