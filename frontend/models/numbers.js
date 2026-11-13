/* Interface for recogniser 0 (numbers).

   Milestone 2 enables local image selection, preprocessing, and recognition.
   Freehand drawing remains a preview of the future canvas and is added in
   Milestone 3. */

(function () {
  "use strict";

  window.recogniser = window.recogniser || {};
  window.recogniser.views = window.recogniser.views || {};

  const DRAWING_TITLE = "Drawing input is added in the next milestone.";
  const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;
  const MAX_UPLOAD_MEGABYTES = MAX_UPLOAD_BYTES / (1024 * 1024);
  const ACCEPTED_TYPES = new Set(["image/png", "image/jpeg"]);
  const ACCEPTED_EXTENSIONS = new Set(["png", "jpg", "jpeg"]);
  /* Uploaded digits are often tiny, such as the 28 x 28 model input. Preview
     images at or below this size use nearest-neighbour scaling so their
     pixels stay sharp when enlarged. */
  const LOW_RESOLUTION_PREVIEW_MAX = 64;

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

  function renderUpload(container, model, host) {
    const area = document.createElement("div");
    area.className = "input-area";

    const title = document.createElement("p");
    title.className = "input-area-title";
    title.textContent = "Image upload";

    const description = document.createElement("p");
    description.className = "input-area-text";
    description.textContent =
      "Choose a PNG or JPEG image containing one handwritten digit. The " +
      "picture is prepared for the " +
      model.input_label +
      " model input before recognition.";

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
      submit: () =>
        window.recogniser.bridge.recogniseUpload(model.id, selection.dataUrl)
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

  function renderDrawing(container, model, host) {
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
        "Drawing is not implemented yet. The canvas follows the resolved " +
          "appearance theme, but freehand input and Clear arrive in the next " +
          "milestone."
      )
    );

    host.setReady(false, DRAWING_TITLE);
    host.setStatus("Drawing input is added in the next milestone.", "info");
  }

  const renderers = {
    upload: renderUpload,
    drawing: renderDrawing
  };

  function renderMode(mode, container, model, host) {
    const render = renderers[mode.id];
    if (render) {
      render(container, model, host);
      return;
    }
    host.setReady(false, "This input mode is not available.");
    host.setStatus("This input mode has no interface yet.", "warning");
    container.append(createNote("This input mode has no interface yet."));
  }

  window.recogniser.views.numbers = { renderMode };
})();
