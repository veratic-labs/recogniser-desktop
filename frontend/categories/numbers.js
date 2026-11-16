/* Shared Numbers category interface: image upload and freehand drawing.

   The same view serves every model registered in the category. The selected
   model is read when a submission starts, so switching models reuses the
   mounted input instead of rebuilding it. */

(function () {
  "use strict";

  window.recogniser = window.recogniser || {};
  window.recogniser.views = window.recogniser.views || {};

  const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;
  const MAX_UPLOAD_MEGABYTES = MAX_UPLOAD_BYTES / (1024 * 1024);
  const ACCEPTED_TYPES = new Set(["image/png", "image/jpeg"]);
  const ACCEPTED_EXTENSIONS = new Set(["png", "jpg", "jpeg"]);
  /* Uploaded digits are often tiny, such as the 28 x 28 model input. Preview
     images at or below this size use nearest-neighbour scaling so their
     pixels stay sharp when enlarged. */
  const LOW_RESOLUTION_PREVIEW_MAX = 64;

  /* The freehand canvas scales with the workspace, so its bitmap is larger
     than its responsive CSS display box and independent of the 28 x 28 model
     input. Pointer positions are converted from CSS to bitmap pixels. */
  const CANVAS_BITMAP_SIZE = 560;
  const CANVAS_STROKE_WIDTH = Math.round(CANVAS_BITMAP_SIZE / 28);

  /* Canvas polarity describes the submitted pixels, not the theme setting. */
  const CANVAS_POLARITY = {
    light: "dark_on_light",
    dark: "light_on_dark"
  };

  const CANVAS_APPEARANCE = {
    dark_on_light: "a white background and black strokes",
    light_on_dark: "a black background and white strokes"
  };

  /* Palettes used only if a theme colour token cannot be read or parsed. */
  const FALLBACK_PALETTES = {
    dark_on_light: {
      background: "#ffffff",
      stroke: "#000000",
      backgroundRgb: [255, 255, 255],
      strokeRgb: [0, 0, 0]
    },
    light_on_dark: {
      background: "#000000",
      stroke: "#ffffff",
      backgroundRgb: [0, 0, 0],
      strokeRgb: [255, 255, 255]
    }
  };

  /* Controllers are looked up by canvas so a theme change reaches the drawing
     that is currently mounted without keeping removed views alive. */
  const canvasControllers = new WeakMap();

  function parseColour(value, fallback) {
    const text = String(value || "").trim().toLowerCase();
    const short = /^#([0-9a-f]{3})$/.exec(text);
    if (short) {
      return short[1].split("").map((digit) => parseInt(digit + digit, 16));
    }
    const full = /^#([0-9a-f]{6})$/.exec(text);
    if (full) {
      return [0, 2, 4].map((offset) =>
        parseInt(full[1].slice(offset, offset + 2), 16)
      );
    }
    const rgb = /^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/.exec(
      text
    );
    if (rgb) {
      return [rgb[1], rgb[2], rgb[3]].map((channel) =>
        Math.min(255, parseInt(channel, 10))
      );
    }
    return fallback.slice();
  }

  function canvasPalette() {
    const rootStyle = window.getComputedStyle(document.documentElement);
    const settings = window.recogniser.settings;
    const resolved = settings ? settings.getState().resolved : "light";
    const polarity = CANVAS_POLARITY[resolved] || CANVAS_POLARITY.light;
    const fallback = FALLBACK_PALETTES[polarity];

    const background =
      rootStyle.getPropertyValue("--color-canvas-background").trim() ||
      fallback.background;
    const stroke =
      rootStyle.getPropertyValue("--color-canvas-stroke").trim() ||
      fallback.stroke;

    return {
      background,
      stroke,
      polarity,
      backgroundRgb: parseColour(background, fallback.backgroundRgb),
      strokeRgb: parseColour(stroke, fallback.strokeRgb)
    };
  }

  /* Remap every canvas pixel from one background/stroke pair to another. The
     confirmed palettes are exact inverses, so a theme switch converts the
     background and strokes together while leaving the drawing's geometry
     untouched. */
  function convertCanvasColours(canvas, context, from, to) {
    const image = context.getImageData(0, 0, canvas.width, canvas.height);
    const data = image.data;
    const spans = [0, 1, 2].map(
      (channel) => from.strokeRgb[channel] - from.backgroundRgb[channel]
    );

    for (let index = 0; index < data.length; index += 4) {
      for (let channel = 0; channel < 3; channel += 1) {
        const span = spans[channel];
        const next =
          span === 0
            ? to.backgroundRgb[channel]
            : to.backgroundRgb[channel] +
              ((data[index + channel] - from.backgroundRgb[channel]) / span) *
                (to.strokeRgb[channel] - to.backgroundRgb[channel]);
        data[index + channel] = Math.max(0, Math.min(255, Math.round(next)));
      }
      data[index + 3] = 255;
    }

    context.putImageData(image, 0, 0);
  }

  const settings = window.recogniser.settings;
  if (settings) {
    settings.onChange(() => {
      document.querySelectorAll(".drawing-canvas").forEach((canvas) => {
        const controller = canvasControllers.get(canvas);
        if (controller) {
          controller.applyTheme();
        }
      });
    });
  }

  function createCanvasController(canvas, handlers) {
    const context = canvas.getContext("2d");
    let palette = canvasPalette();
    let hasInk = false;
    let activePointer = null;
    let lastPoint = null;

    function updateMetadata() {
      canvas.dataset.canvasPolarity = palette.polarity;
      canvas.dataset.canvasBackground = palette.background;
      canvas.dataset.canvasStroke = palette.stroke;
      canvas.setAttribute(
        "aria-label",
        "Drawing canvas with " +
          CANVAS_APPEARANCE[palette.polarity] +
          ". Draw one digit, then choose Recognise."
      );
      context.strokeStyle = palette.stroke;
      context.fillStyle = palette.stroke;
      context.lineWidth = CANVAS_STROKE_WIDTH;
      context.lineCap = "round";
      context.lineJoin = "round";
    }

    function fillBackground(colour) {
      context.save();
      context.globalCompositeOperation = "source-over";
      context.fillStyle = colour;
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.restore();
    }

    function pointFromEvent(event) {
      const rect = canvas.getBoundingClientRect();
      if (!rect.width || !rect.height) {
        return null;
      }
      /* The bitmap is larger than the responsive display box, so pointer
         positions must be converted rather than used as bitmap pixels. */
      return {
        x: ((event.clientX - rect.left) / rect.width) * canvas.width,
        y: ((event.clientY - rect.top) / rect.height) * canvas.height
      };
    }

    function startStroke(event) {
      if (activePointer !== null) {
        return;
      }
      if (event.pointerType === "mouse" && event.button !== 0) {
        return;
      }
      const point = pointFromEvent(event);
      if (!point) {
        return;
      }

      event.preventDefault();
      activePointer = event.pointerId;
      lastPoint = point;

      /* A press without movement still marks a visible dot. */
      context.fillStyle = palette.stroke;
      context.beginPath();
      context.arc(point.x, point.y, CANVAS_STROKE_WIDTH / 2, 0, Math.PI * 2);
      context.fill();
      context.beginPath();
      context.moveTo(point.x, point.y);

      try {
        canvas.setPointerCapture(event.pointerId);
      } catch (error) {
        /* Synthetic pointers cannot be captured; drawing continues. */
      }

      if (!hasInk) {
        hasInk = true;
        handlers.onInkChange(true);
      }
      handlers.onStrokeStart();
    }

    function continueStroke(event) {
      if (activePointer === null || event.pointerId !== activePointer) {
        return;
      }
      const point = pointFromEvent(event);
      if (!point) {
        return;
      }

      event.preventDefault();
      context.beginPath();
      context.moveTo(lastPoint.x, lastPoint.y);
      context.lineTo(point.x, point.y);
      context.stroke();
      lastPoint = point;
    }

    function endStroke(event) {
      if (activePointer === null || event.pointerId !== activePointer) {
        return;
      }
      activePointer = null;
      lastPoint = null;
      try {
        canvas.releasePointerCapture(event.pointerId);
      } catch (error) {
        /* The pointer was never captured; nothing to release. */
      }
    }

    canvas.addEventListener("pointerdown", startStroke);
    canvas.addEventListener("pointermove", continueStroke);
    canvas.addEventListener("pointerup", endStroke);
    canvas.addEventListener("pointercancel", endStroke);
    canvas.addEventListener("lostpointercapture", endStroke);

    updateMetadata();
    fillBackground(palette.background);

    return {
      hasInk() {
        return hasInk;
      },
      clear() {
        activePointer = null;
        lastPoint = null;
        fillBackground(palette.background);
        if (hasInk) {
          hasInk = false;
          handlers.onInkChange(false);
        }
      },
      applyTheme() {
        const next = canvasPalette();
        const paletteChanged =
          next.background !== palette.background ||
          next.stroke !== palette.stroke;
        if (paletteChanged) {
          if (hasInk) {
            convertCanvasColours(canvas, context, palette, next);
          } else {
            fillBackground(next.background);
          }
        }
        palette = next;
        updateMetadata();
      },
      snapshot() {
        return {
          dataUrl: canvas.toDataURL("image/png"),
          polarity: canvas.dataset.canvasPolarity || palette.polarity
        };
      }
    };
  }

  function createNote(text) {
    const note = document.createElement("p");
    note.className = "mode-note";
    note.textContent = text;
    return note;
  }

  function isAcceptedFile(file) {
    const type = (file.type || "").toLowerCase();
    if (ACCEPTED_TYPES.has(type)) {
      return true;
    }
    if (type) {
      return false;
    }
    const name = (file.name || "").toLowerCase();
    const dot = name.lastIndexOf(".");
    const extension = dot === -1 ? "" : name.slice(dot + 1);
    return ACCEPTED_EXTENSIONS.has(extension);
  }

  function renderUpload(container, host) {
    const area = document.createElement("div");
    area.className = "input-area";

    const title = document.createElement("p");
    title.className = "input-area-title";
    title.textContent = "Image upload";

    const description = document.createElement("p");
    description.className = "input-area-text";
    description.textContent =
      "Choose a PNG or JPEG image containing one handwritten digit. The " +
      "picture is prepared for the selected model's input format before " +
      "recognition.";

    const chooseButton = document.createElement("button");
    chooseButton.type = "button";
    chooseButton.className = "button secondary";
    chooseButton.textContent = "Choose image";

    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = "image/png,image/jpeg";
    fileInput.className = "visually-hidden";
    fileInput.tabIndex = -1;

    const preview = document.createElement("figure");
    preview.className = "upload-preview";
    preview.hidden = true;

    const previewFrame = document.createElement("div");
    previewFrame.className = "upload-preview-frame";

    const previewImage = document.createElement("img");
    previewImage.className = "upload-preview-image";
    previewImage.alt = "Preview of the selected image.";

    const previewCaption = document.createElement("figcaption");
    previewCaption.className = "upload-preview-name";

    previewFrame.append(previewImage);
    preview.append(previewFrame, previewCaption);
    /* The preview replaces the heading and helper text. The choose button
       stays below it so another image can be selected at any time. */
    area.append(title, description, preview, chooseButton, fileInput);
    container.append(area);

    let selection = null;
    let selectionToken = 0;

    function updatePreviewRendering() {
      const longestSide = Math.max(
        previewImage.naturalWidth,
        previewImage.naturalHeight
      );
      const lowResolution =
        longestSide > 0 && longestSide <= LOW_RESOLUTION_PREVIEW_MAX;
      previewImage.classList.toggle(
        "upload-preview-image-pixelated",
        lowResolution
      );
    }

    previewImage.addEventListener("load", updatePreviewRendering);

    function showPlaceholder() {
      title.hidden = false;
      description.hidden = false;
      previewImage.removeAttribute("src");
      previewImage.alt = "Preview of the selected image.";
      previewImage.classList.remove("upload-preview-image-pixelated");
      previewCaption.textContent = "";
      preview.hidden = true;
    }

    function clearSelection() {
      selection = null;
      selectionToken += 1;
      fileInput.value = "";
      showPlaceholder();
      host.setReady(false, "Choose an image to recognise.");
    }

    chooseButton.addEventListener("click", () => fileInput.click());

    host.provideSubmission({
      isReady: () => selection !== null,
      submit: () => {
        /* Read the selection at submission time, so a model switch reuses
           the mounted preview instead of rebuilding the input panel. */
        const category = host.getCategory();
        const model = host.getModel();
        return window.recogniser.bridge.recogniseCategoryUpload(
          category.id,
          model.id,
          selection.dataUrl
        );
      }
    });
    host.setReady(false, "Choose an image to recognise.");
    host.setStatus("Choose a local image, then run the model.", "info");

    fileInput.addEventListener("change", () => {
      const file = fileInput.files && fileInput.files[0];
      fileInput.value = "";
      if (!file) {
        return;
      }

      host.inputChanged();
      host.setReady(false, "Reading the selected image…");
      selection = null;
      const token = ++selectionToken;

      if (!isAcceptedFile(file)) {
        clearSelection();
        host.setStatus("Choose a PNG or JPEG image.", "error");
        return;
      }

      if (file.size > MAX_UPLOAD_BYTES) {
        clearSelection();
        host.setStatus(
          "That image is larger than " +
            MAX_UPLOAD_MEGABYTES +
            " MB. Choose a smaller image.",
          "error"
        );
        return;
      }

      /* Keep the placeholder visible while the replacement is read. A
         cancelled picker never reaches this handler and keeps the old image. */
      showPlaceholder();
      host.setStatus("Reading the selected image…", "info");

      const reader = new FileReader();
      reader.addEventListener("error", () => {
        if (token !== selectionToken) {
          return;
        }
        clearSelection();
        host.setStatus(
          "The selected image could not be read. Try another file.",
          "error"
        );
      });
      reader.addEventListener("load", () => {
        if (token !== selectionToken) {
          return;
        }
        if (
          typeof reader.result !== "string" ||
          !reader.result.startsWith("data:image/")
        ) {
          clearSelection();
          host.setStatus(
            "The selected image could not be read. Try another file.",
            "error"
          );
          return;
        }

        selection = { dataUrl: reader.result };
        title.hidden = true;
        description.hidden = true;
        previewImage.src = reader.result;
        previewImage.alt = "Preview of " + file.name + ".";
        previewCaption.textContent = file.name;
        preview.hidden = false;
        host.setReady(true);
        host.setStatus("Image ready. Choose Recognise to run the model.", "info");
      });
      reader.readAsDataURL(file);
    });
  }

  function renderDrawing(container, host) {
    const frame = document.createElement("div");
    frame.className = "canvas-frame";

    const canvas = document.createElement("canvas");
    canvas.className = "drawing-canvas";
    canvas.width = CANVAS_BITMAP_SIZE;
    canvas.height = CANVAS_BITMAP_SIZE;
    canvas.setAttribute("role", "img");

    frame.append(canvas);

    const actions = document.createElement("div");
    actions.className = "canvas-actions";

    const clearButton = document.createElement("button");
    clearButton.type = "button";
    clearButton.className = "button secondary";
    clearButton.textContent = "Clear";
    clearButton.disabled = true;
    actions.append(clearButton);

    container.append(frame, actions);
    container.append(
      createNote(
        "Draw one digit in the canvas. Changing the appearance keeps the " +
          "drawing and converts only its colours."
      )
    );

    const controller = createCanvasController(canvas, {
      onStrokeStart() {
        host.inputChanged();
        host.setReady(true);
        host.setStatus(
          "Drawing ready. Choose Recognise to run the model.",
          "info"
        );
      },
      onInkChange(hasInk) {
        clearButton.disabled = !hasInk;
      }
    });
    canvasControllers.set(canvas, controller);

    clearButton.addEventListener("click", () => {
      controller.clear();
      host.inputChanged();
      host.setReady(false, "Draw a digit to recognise.");
      host.setStatus(
        "Canvas cleared. Draw a digit, then choose Recognise.",
        "info"
      );
    });

    host.provideSubmission({
      isReady: () => controller.hasInk(),
      submit: () => {
        /* Polarity is captured with the pixels, so a later theme change
           cannot alter how this drawing is interpreted. The selected model
           is read now, not when this view was mounted. */
        const category = host.getCategory();
        const model = host.getModel();
        const drawing = controller.snapshot();
        return window.recogniser.bridge.recogniseCategoryDrawing(
          category.id,
          model.id,
          drawing.dataUrl,
          drawing.polarity
        );
      }
    });

    host.setReady(false, "Draw a digit to recognise.");
    host.setStatus("Draw one digit with the mouse, then run the model.", "info");
  }

  const renderers = {
    upload: renderUpload,
    drawing: renderDrawing
  };

  function renderMode(mode, container, host) {
    const render = renderers[mode.id];
    if (render) {
      render(container, host);
      return;
    }
    host.setReady(false, "This input mode is not available.");
    host.setStatus("This input mode has no interface yet.", "warning");
    container.append(createNote("This input mode has no interface yet."));
  }

  /* The Numbers view owns digit-specific result markup. A successful result
     whose prediction is not an integer has no card to show here; the shared
     layer still reports that recognition succeeded. */
  function renderResult(result, container) {
    if (!container || !Number.isInteger(result.prediction)) {
      return false;
    }

    const label = document.createElement("p");
    label.className = "result-label";
    label.textContent = "Predicted digit";

    const value = document.createElement("p");
    value.className = "result-digit";
    value.textContent = String(result.prediction);

    container.append(label, value);
    return true;
  }

  window.recogniser.views.numbers = { renderMode, renderResult };
})();
