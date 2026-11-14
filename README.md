# recogniser

A minimal desktop application for trying trained neural networks on your own
input. This build covers **Milestones 1 to 3**: the desktop shell, welcome
screen, registry-driven model list, model interaction view, appearance settings,
and image-upload and freehand-drawing recognition for the digit model.

## Requirements

- Windows with the Microsoft Edge WebView2 runtime (installed with Microsoft
  Edge by default)
- Python 3.10 or newer

## Install

From the project root:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Launch

```powershell
python -m backend.main
```

## Current behaviour

- The welcome screen shows a **Select a model** list of registered models,
  currently only `recogniser 0 (numbers)`.
- Selecting a model opens its interaction view. Use **Back to models** or the
  header wordmark to return to the welcome screen and choose another model.
- **Image upload** accepts PNG and JPEG files up to 20 MB. **Choose image**
  opens the file picker. A valid selection replaces the upload placeholder with
  the original image in a responsive preview of approximately 320 × 320 CSS
  pixels. The image is scaled up or down to fit without cropping or stretching;
  low-resolution sources use pixelated rendering so their digit pixels stay
  sharp. **Choose image** stays enabled below the preview, and **Recognise**
  runs inference only when clicked. Selecting another valid image replaces the
  preview and clears the previous result; cancelling the picker keeps the
  current image and result. An outstanding result for a replaced image is
  ignored.
- Uploaded images are converted to the model's 28 × 28 `float32` input. The
  digit is cropped to its ink, scaled with its aspect ratio preserved so its
  longest side is 20 pixels, and centred on a black canvas. Image polarity is
  detected from the border pixels, so recognition is independent of the
  application theme.
- **Freehand drawing** shows a canvas that follows the resolved theme. Draw one
  digit with the mouse (or a pointer), then click **Recognise**. **Clear**
  empties the canvas, disables itself, and drops the previous result; the
  button is disabled until the canvas contains ink. Starting a new stroke also
  drops the previous result. Changing the appearance converts the drawing's
  background and strokes together, so its geometry is preserved.
- Submitted drawings are sent as a PNG together with `canvas_polarity`, which
  describes the submitted pixels rather than the current theme. Light-theme
  drawings (`dark_on_light`) are inverted and Dark-theme drawings
  (`light_on_dark`) are used as drawn, so a prediction does not depend on the
  theme at recognition time. The stroke is then converted to the model's
  28 × 28 `float32` input by the same ink-crop, aspect-preserving 20-pixel
  scaling, and centring used for uploads. A blank canvas is rejected before
  inference.
- A score of at least `0.90` shows the predicted digit. Lower scores show an
  "unable to predict with enough confidence" message without revealing the
  candidate digit. Invalid files, oversized images, empty drawings, and model
  failures show user-facing messages. The confidence percentage is not
  displayed.
- The input mode and result/status area share one workspace. There is no
  separate processed-image preview.
- Light mode is the default. The appearance menu offers Light, Dark, and
  Follow system. Theme preferences are not persisted yet because persistence
  remains an open product decision.

## Project layout

```text
backend/
  main.py            Desktop entry point and pywebview setup
  api.py             Functions exposed to the frontend
  model_registry.py  Shared model registration data
  adapters/          Per-model preprocessing and inference
frontend/
  index.html         Application shell and views
  css/               Layout and theme styles
  js/                Navigation, bridge, and appearance logic
  models/            Model-specific interface modules
models/0-numbers/    ONNX model and original inference script
```
