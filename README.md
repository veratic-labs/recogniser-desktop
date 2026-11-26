# recogniser

A minimal desktop application for trying trained neural networks on your own
input. The current build includes the desktop shell, welcome screen,
registry-driven category list, shared category view with a model dropdown,
appearance settings, and image-upload and freehand-drawing recognition for the
digit model. The registry currently contains one category, `Numbers`, with one
model, `recogniser 0 (numbers)`.

Milestones 1–4 and the category-navigation refactor are complete. Milestone 4's
successful-result delegation, API mode-message fallback, focused backend tests,
and extension documentation are implemented. Backend, live DOM/bridge, and
regression checks have passed, and the user accepted the interface.

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

If PowerShell's execution policy blocks `Activate.ps1`, call the virtual
environment's interpreter directly instead, for example
`.\venv\Scripts\python.exe -m pip install -r requirements.txt`.

## Launch

From the project root, with the virtual environment active:

```powershell
python -m backend.main
```

Frontend and model paths resolve from their source locations rather than the
current working directory, but the module must still be launched from the
project root so that `backend` is importable. If activation is unavailable, run
`.\venv\Scripts\python.exe -m backend.main` instead.

## Tests

Activate the virtual environment and run the standard-library test suite from
the project root:

```powershell
python -m unittest discover -s tests -v
```

If the virtual environment is not active, use
`.\venv\Scripts\python.exe -m unittest discover -s tests -v`.

The checks cover registry integrity, model-to-category relationships, the
current model resource mapping, adapter support for each category input mode,
API validation and fallback messages, and adapter error-to-status mapping. They
use no GUI, network access, or real inference. Adapter modules are imported only
to inspect function names; mocked modules exercise the API error paths, and all
patched state is restored automatically.

## Build and install

The Windows executable bundle and the Inno Setup installer are produced with one
command each:

```powershell
.\packaging\build.ps1            # tests, bundle, frozen self-tests, manifest
.\packaging\build.ps1 -Installer # package the verified bundle as a setup file
```

- [docs/BUILDING.md](docs/BUILDING.md) covers prerequisites, outputs, the
  reviewed-bundle manifest, version and icon changes, and troubleshooting.
- [docs/INSTALL.md](docs/INSTALL.md) covers installing, upgrading, uninstalling,
  prerequisites, and where user data lives.

Building needs Inno Setup 7 only for the installer step. Installing a finished
build needs neither Python nor the repository.

## Current behaviour

- The welcome screen shows a **Select a category** list of registered
  categories, currently only `Numbers`.
- Selecting a category opens its shared interaction view, which serves every
  model registered in that category. Use **Back to categories** or the header
  wordmark to return to the welcome screen and choose another category.
- The **Model** dropdown sits in the action row immediately to the left of
  **Recognise** and lists the category's registered models, initially
  `recogniser 0 (numbers)`. Switching models keeps the current image or
  drawing, clears the previous result and any model-specific message, and
  ignores a recognition request that was still outstanding for the previous
  model. The description and instructions above the input area describe the
  selected model.
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
- For `numbers-0`, uploaded images are converted to its 28 × 28 `float32` input.
  The digit is cropped to its ink, scaled with its aspect ratio preserved so its
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
  theme at recognition time. The stroke is then converted to `numbers-0`'s
  28 × 28 `float32` input by the same ink-crop, aspect-preserving 20-pixel
  scaling, and centring used for uploads. A blank canvas is rejected before
  inference.
- For `numbers-0`, a score of at least `0.90` shows the predicted digit. Lower
  scores show an "unable to predict with enough confidence" message without
  revealing the candidate digit. Invalid files, oversized images, empty
  drawings, and model failures show user-facing messages. The confidence
  percentage is not displayed.
- A successful result is passed to the active category view's `renderResult()`.
  The Numbers view shows the predicted digit. If a view cannot render a
  successful result, the status still reports success but no result card is
  shown. `uncertain` and `invalid_input` results use warning styling, while
  `error` results use error styling.
- The input mode and result/status area share one workspace. There is no
  separate processed-image preview.
- Light mode is the default. The appearance menu offers Light, Dark, and
  Follow system. Theme preferences are not persisted yet because persistence
  remains an open product decision.

## Project layout

```text
backend/
  main.py              Desktop entry point and pywebview setup
  api.py               Functions exposed to the frontend and request validation
  model_registry.py    Explicit category and model registration data
  adapters/
    __init__.py        Adapter error types
    numbers.py         Numbers preprocessing, inference, and result policy
frontend/
  index.html           Application shell, views, and script loading
  css/                 Layout and theme styles
  js/
    bridge.js          Calls to the Python API through pywebview
    main.js            Navigation, category views, and shared result handling
    settings.js        Appearance selection
  categories/
    numbers.js         Shared Numbers upload, drawing, and result interface
models/
  0-numbers/
    model_0_numbers.onnx
    model_0_numbers.py
packaging/
  build.ps1            One-command build, verification, and installer packaging
  launcher.py          Frozen entry point used by PyInstaller
  prepare_build.py     Generates version_info.txt and the multi-size ICO
  recogniser.spec      PyInstaller specification
  recogniser.iss       Inno Setup script
  version.txt          Single source of the application version
  assets/              Generated installer and executable icon
tests/
  __init__.py
  test_registry_and_api.py  Registry, API validation, and error-mapping checks
  test_paths_and_diagnostics.py  Data paths, logging, and the self-test report
docs/
  BUILDING.md          Build and packaging instructions
  INSTALL.md           Install, upgrade, and uninstall instructions
AGENTS.md              Agent workflow policy
PLAN.md                Product requirements, architecture, and milestones
PACKAGING_PLAN.md      Packaging plan, completed stages, and their evidence
README.md              Installation, usage, contracts, and extension guide
requirements.txt       Python runtime dependencies
```

`venv/`, `.webview-data/`, `.tmp/`, `build/`, `dist/`, Python caches, and other
generated files are ignored by Git. Model resources are intentional repository
content.

## Adding a model to an existing category

1. Put the model's ONNX file and its original inference script in a resource
   directory under `models/`, for example `models/<model-directory>/`. Resolve
   files relative to that directory or the project root, not the current working
   directory.
2. Add an adapter module under `backend/adapters/`. One adapter module per model
   is the current implementation convention, not a permanent architectural
   requirement. The adapter must expose a callable named
   `recognise_<mode-id>` for every input mode offered by its category. For the
   current Numbers category that means:

   ```python
   def recognise_upload(image_data_url): ...
   def recognise_drawing(image_data_url, canvas_polarity): ...
   ```

   Keep the model's preprocessing, tensor dimensions, inference invocation,
   output interpretation, and confidence policy in this adapter. Return the
   shared result envelope described below. Raise `InvalidInputError` for
   user-correctable input and `ModelUnavailableError` for missing resources,
   interface mismatches, or inference failures.
3. Register a `ModelRegistration` in `backend/model_registry.py` and add it to
   `_MODELS`. Give it a unique `id`, an existing `category_id`, a `series`
   number, display text, `input_label`, the dotted adapter module path, and a
   `resource_dir` relative to the project root. Keep internal IDs and directory
   names stable when changing display text.
4. The shared category view normally needs no changes when the new model accepts
   the same input modes and returns a result its `renderResult()` can display.
   If it returns a different result shape, update that category's result
   renderer or add a category whose view can display it. Do not force an integer
   prediction or confidence score into the shared result contract.
5. If you package the application, add the new model's `.py` and `.onnx` files to
   `datas` and the adapter module to `hiddenimports` in `packaging/recogniser.spec`.
   The frozen bundle does not discover model files on its own; see
   [docs/BUILDING.md](docs/BUILDING.md).
6. Run `python -m unittest discover -s tests -v`. The registry checks reject
   duplicate IDs and invalid model-to-category relationships, and verify that
   every registered model adapter exposes each mode's required function.

Do not add placeholder registrations. A model is registered only when its
resources and adapter are ready.

## Adding a new category

1. Add a `CategoryRegistration` in `backend/model_registry.py` and include it in
   `_CATEGORIES`. Provide a unique `id`, user-facing label, description,
   guidance, `input_modes`, and a `frontend_view` key. Each `InputMode` needs a
   unique ID within the category, a label, and a hint. The mode ID determines
   the adapter functions required from every model in the category:
   `recognise_<mode-id>`.
2. Add a shared category view at `frontend/categories/<name>.js`. It must
   register an object on the global view registry using the registration's
   `frontend_view` value:

   ```javascript
   window.recogniser.views[frontendViewId] = { renderMode, renderResult };
   ```

   `frontendViewId` is the registration's `frontend_view` value.
   `renderMode` builds the interface for each mode and supplies submission
   handlers. `renderResult` renders successful results for every model in the
   category and returns `true` only when it added content.
3. Load the new category script from `frontend/index.html` before
   `js/main.js`, alongside `categories/numbers.js`. There is no automatic
   discovery: script loading, the registration, and the view key are explicit.
4. Add each model's resources, adapter, and model registration as described
   above. All models in the category must support every category input mode.
5. Run the test suite. It checks category/model ID uniqueness, valid
   relationships, and adapter/mode coverage. Then launch the application and
   verify the category card, view, mode tabs, model dropdown, and recognition
   flows manually.

If a category's script or `renderMode` is missing, the shared UI reports that
the category has no interface rather than crashing. If its `renderResult` is
missing or declines a successful result, recognition still succeeds but no
result card is shown.

## Adapter contract

The API imports the dotted module named by `ModelRegistration.adapter` and calls
the function matching the requested category mode:

| Category mode | Required adapter function | Arguments |
| --- | --- | --- |
| `upload` | `recognise_upload` | `image_data_url` |
| `drawing` | `recognise_drawing` | `image_data_url`, `canvas_polarity` |

Each function must return a JSON-serialisable result envelope:

```python
{
    "status": "ok" | "uncertain" | "invalid_input" | "error",
    "prediction": ...,   # model-specific, or None
    "confidence": ...,   # model-specific, or None
    "message": "...",    # user-facing text
}
```

The status meanings are:

- `ok`: recognition succeeded. The active category view's `renderResult()` is
  offered the result. The shared layer does not require an integer prediction
  or a confidence score.
- `uncertain`: the model ran but did not produce a usable answer. The UI shows
  the message with warning styling and no result card.
- `invalid_input`: the supplied image, drawing, or metadata cannot be used. The
  adapter raises `InvalidInputError` with a user-facing explanation; the API
  converts it to this status and message.
- `error`: the model or application could not complete recognition. The UI uses
  error styling.

Adapters raise:

- `backend.adapters.InvalidInputError` for missing, malformed, oversized, or
  otherwise unusable user input. Its message is returned to the user.
- `backend.adapters.ModelUnavailableError` for missing model files, an
  incompatible ONNX interface, or a failed inference call. The API logs the
  failure and returns the generic model-error message instead of internal
  details.

Any other exception from importing the adapter, looking up the function, or
calling it is also logged and converted to the generic `error` envelope. The
frontend never receives a traceback or resource path.

The category-aware API validates requests before importing an adapter. It checks
the category, then the model and its category relationship, then the requested
input mode. Unknown categories and models are rejected with error envelopes.
So are models selected from another category and modes the category does not
offer. Upload and drawing have their own unsupported-mode messages; any other
unregistered mode uses the neutral fallback “That category does not support
this input mode.”

For uploads, `image_data_url` is a base64 data URL whose media type is PNG or
JPEG. For drawings, it is a base64 PNG plus `canvas_polarity`, whose values are
`dark_on_light` or `light_on_dark` and describe the submitted pixels, not the
current application theme. The adapter is responsible for rejecting unsupported
or malformed payloads with an `InvalidInputError`.

The adapter owns its model's input dimensions, preprocessing, output
interpretation, and confidence policy. It should load model resources lazily and
reuse the inference session where practical. The current Numbers adapter caches
its loaded predictor after the first successful load.

## Category view contract

A category view is a JavaScript object registered at
`window.recogniser.views[category.frontend_view]`. Its script must load before
`frontend/js/main.js`, because shared navigation reads the registry while the
application starts.

### `renderMode(mode, container, host)`

Called when the category opens and whenever the user selects a mode. The
arguments are:

- `mode`: the category's input-mode object, with `id`, `label`, and `hint`.
- `container`: the empty mode panel element. The shared layer clears the panel
  and previous result before calling the renderer.
- `host`: helpers for the mounted input:
  - `host.setStatus(message, tone)` sets the status text and `info`, `success`,
    `warning`, or `error` tone.
  - `host.setReady(ready, reason)` enables or disables **Recognise** and sets its
    explanatory tooltip.
  - `host.provideSubmission({ isReady, submit })` registers the active input.
    `isReady()` reports whether there is usable input. `submit()` returns the
    recognition promise. Read the current category and model at submission time
    with `host.getCategory()` and `host.getModel()` rather than capturing them
    when the view mounts.
  - `host.inputChanged()` invalidates an outstanding request, clears the previous
    result, disables **Recognise**, and resets the button text. Call it when the
    user replaces or edits the input.
  - `host.getCategory()` and `host.getModel()` return the current selections.

The shared layer refuses duplicate submissions while a request is busy and
ignores a result whose request was invalidated by an input or model change.

### `renderResult(result, container)`

Called for a successful (`status: "ok"`) result after the shared layer has
cleared the result area. The renderer:

- Appends the category-appropriate result markup to `container`.
- Returns exactly `true` when it added content.
- Returns `false` when it cannot or chooses not to display the result.

A missing renderer, `false`, or a thrown exception leaves the result area empty
and the recognition still reported as successful in the status line. Returning
`true` makes the shared layer show the result area with success styling.

The renderer must not require an integer prediction or a confidence score,
although the current Numbers renderer displays an integer prediction. Models in
one category may return different result data.

The Numbers view registers `renderMode` and `renderResult` under the `numbers`
view key. Its result renderer shows the label “Predicted digit” and the value,
and returns `false` when the prediction is not an integer.

## Model-owned input and result policies

Preprocessing, input dimensions, tensor layout, output interpretation, and
confidence policy belong to the model and its adapter—not to the category, the
shared navigation, or the API layer. `input_label` is model-owned presentation
metadata; it is sent to the frontend with the model payload but is not a shared
validation rule.

The current `numbers-0` model specifically uses:

- A 28 × 28 grayscale image, flattened to 784 `float32` values in `[0, 1]`.
- An ink crop, aspect-preserving scaling to a 20-pixel longest side, and
  centring on a dark background.
- Polarity detection for uploads and explicit `canvas_polarity` handling for
  drawings.
- ONNX input `input` with shape `(1, 784)` and output `output` with shape
  `(1, 10)` logits.
- Softmax confidence and a `0.90` acceptance threshold; lower scores hide the
  candidate digit.

Those values are not defaults for every future model, even within the Numbers
category. Each new model records and implements its own input and confidence
behaviour. Shared upload or image-processing helpers are not extracted until a
second real model demonstrates the need.

## Current limitations

- The registry contains one category (`Numbers`) and one model
  (`recogniser 0 (numbers)`). There is no automatic model or category discovery,
  plugin system, or hot loading; all additions are explicit registrations.
- One adapter module per model is the current convention. This is not a
  permanent restriction, and the test suite does not require adapter modules to
  be unique.
- The application targets Windows with WebView2 and uses
  `CPUExecutionProvider`. Other desktop platforms and GPU execution have not
  been verified.
- Model loading happens on demand in the adapter and the loaded predictor is
  reused. A missing or incompatible model produces the generic model-error
  message.
- The current upload path accepts PNG and JPEG files up to 20 MB. These are
  properties of the Numbers adapter, not guarantees for future categories.
- Theme preference is held in memory only and is not persisted across launches.
- The automated suite under `tests/` covers the backend registry, API, adapter
  error paths, filesystem helpers, and the self-test report only. There is no
  committed frontend DOM test runner, training workflow, recognition history,
  multi-digit detection, or general OCR.
- A Windows x64 bundle and installer are produced by `packaging\build.ps1`; see
  [docs/BUILDING.md](docs/BUILDING.md) and
  [docs/INSTALL.md](docs/INSTALL.md). The installer is unsigned and has no
  automatic updates, and only one Windows 11 x64 machine has been tested.
- A non-digit image is not guaranteed to produce low confidence. Threshold
  verification uses controlled scores rather than relying on an arbitrary image.
- Automated milestone regression verification and manual interface acceptance
  are complete. Future interface changes will still require user review.

## Manual UI verification

Install the dependencies and launch the application from the project root:

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m backend.main
```

Then check the following:

1. The welcome screen lists the **Numbers** category with a working **Open**
   action.
2. Opening Numbers shows the shared category view, the two input-mode tabs, the
   model dropdown (`recogniser 0 (numbers)`), and disabled **Recognise** until
   input is ready.
3. On **Image upload**, choose a PNG or JPEG containing one handwritten digit.
   Confirm the image preview appears, then choose **Recognise**. A confident
   result should show a **Predicted digit** value and a success status; a
   low-confidence result should show the unable-to-predict message without a
   candidate digit.
4. Replace the uploaded image and confirm the previous result is cleared.
   Cancelling the file picker should keep the current image and result.
5. On **Freehand drawing**, draw one digit and choose **Recognise**. Confirm a
   result appears. Switch between Light and Dark and verify the drawing remains
   and is recoloured, then choose **Clear**. **Recognise** should be disabled
   again until new ink is drawn.
6. Use **Back to categories** and the header wordmark to return to the welcome
   screen. Open Numbers again and confirm the view resets to its first model and
   mode.
7. Confirm that malformed input or a model failure produces a readable
   user-facing message, with no traceback or internal path in the interface.

Automated end-to-end and DOM/bridge checks have passed for both recognition
flows. The user reviewed and accepted the layout, spacing, alignment, and
interaction quality.
