# recogniser

A minimal desktop application for trying trained neural networks on your own
input. This build covers **Milestone 1**: the desktop shell, welcome screen,
registry-driven model list, model interaction view, and appearance settings.

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
- The model view offers **Image upload** and **Freehand drawing** mode
  navigation. Actual upload, drawing, preprocessing, and recognition arrive in
  later milestones, so the relevant controls are disabled and no predictions
  are shown.
- The input mode and result/status area share one workspace. There is no
  separate processed-image preview.
- Light mode is the default. The appearance menu offers Light, Dark, and
  Follow system. Theme preferences are not persisted yet because persistence
  remains an open product decision.
- The drawing canvas follows the resolved theme: white with black strokes in
  Light mode and black with white strokes in Dark mode. Follow system uses the
  palette of the currently resolved theme.
- The canvas scales with the workspace and stays square. Its display size is
  independent of the final 28 × 28 model input. Drawing is not active in this
  build, so the canvas is currently blank; drawings will submit explicit
  canvas-polarity metadata when the drawing and preprocessing milestones are
  implemented.

## Project layout

```text
backend/
  main.py            Desktop entry point and pywebview setup
  api.py             Functions exposed to the frontend
  model_registry.py  Shared model registration data
frontend/
  index.html         Application shell and views
  css/               Layout and theme styles
  js/                Navigation, bridge, and appearance logic
  models/            Model-specific interface modules
models/0-numbers/    ONNX model and original inference script
```
