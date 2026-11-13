# recogniser — Development Plan

Status: requirements draft v0.7. Confirmed decisions and provisional proposals are identified separately. This document defines the product, architecture, implementation milestones, and acceptance criteria. Agent workflow instructions will be maintained separately in `AGENT.md`.

## 1. Project Goal

Build `recogniser`, a Python desktop application using pywebview and HTML/CSS/JavaScript, so users can interact with trained neural networks exported to ONNX.

The first supported model is an MNIST MLP named `recogniser 0 (numbers)`. Future releases may introduce CNNs and models for other tasks. All models share a welcome screen model list, while each model has its own interaction view, input modes, preprocessing, and result presentation.

The architecture should support gradual expansion with a small, understandable codebase. Requirements are still being discussed; implementation has not started.

## 2. Technology and Existing Model

| Item | Decision or current information |
| --- | --- |
| Desktop window | pywebview |
| Frontend | HTML, CSS, JavaScript |
| Backend and inference | Python, ONNX Runtime, NumPy |
| Image processing proposal | Pillow |
| Training dataset | MNIST |
| Training transform | `transforms.ToTensor()` only; no additional `Normalize` |
| Model directory | `models/0-numbers/` under the project root |
| ONNX filename | Provisionally `model_0_numbers.onnx`, based on the latest filename description; verify the actual extension during integration |
| Inference script | `model_0_numbers.py` |
| Inference function | `model_0_numbers_predict(image)` |
| Return value | `(prediction, confidence)`, where confidence is a softmax score between 0 and 1 |
| Execution provider | `CPUExecutionProvider` |

The supplied training code uses linear layers `784 → 128 → 64 → 10`, ReLU after the first two layers, cross-entropy loss, Adam with a learning rate of 0.001, batch size 64, and five epochs.

The existing inference function converts input to `float32`, reshapes it to `(1, 784)`, runs ONNX inference, computes softmax from logits, and returns the predicted digit and its score. It can continue accepting already preprocessed input without changing its return format.

The original script references `mnist_mlp.onnx`. If the actual model file is now named `model_0_numbers.onnx`, its path must match:

```python
MODEL_PATH = Path(__file__).resolve().parent / "model_0_numbers.onnx"
```

The model file itself has not been inspected. Input/output names, shapes, and data types remain integration checks.

## 3. Confirmed Input Size

The model input is **28 × 28**, corresponding to 784 pixels. The drawing canvas is displayed responsively at a larger size for comfortable drawing and scales with the available workspace. Its CSS display size and internal bitmap are independent of the final 28 × 28 model input; preprocessing always produces 28 × 28 grayscale values.

## 4. Screens and Navigation

### 4.1 Welcome Screen

- Show a welcome message and the application name `recogniser`.
- Display available models below the welcome message.
- Initially list only `recogniser 0 (numbers)`, with a short description explaining that it recognises a single handwritten digit from 0 to 9 using an MNIST-trained MLP.
- Selecting a model opens its interaction view.
- Generate the model list from shared registration data.
- Future models can provide their own interaction views and input methods.

### 4.2 Model Naming and Selection

The display-name format is:

```text
recogniser <series> (<type>)
```

`series` is the user-assigned series number; `type` describes the task or category. These placeholders are replaced in the actual name.

| Purpose | Display name |
| --- | --- |
| Initial model | `recogniser 0 (numbers)` |
| Future naming example | `recogniser 2 (animals)` |

The animals example illustrates naming only; it is not an additional first-release model or placeholder entry.

- Series numbers are assigned explicitly and are not recalculated from list order.
- Network architectures such as MLP or CNN appear in descriptions rather than replacing the task label.
- Keep model selection on the welcome screen. Do not provide a model selector in model interaction views.
- Label the welcome-screen model list `Select a model` and open the selected model's interaction view from that list.
- Use the same registration data for the welcome list, titles, and descriptions.
- Show the list even when only one model is registered.
- List only integrated models.
- On model change, clear the previous model's input state, results, and error messages. An outstanding request for a previous model must not update the new view.
- Each model defines its own input modes, preprocessing, and output presentation.
- Store display names, stable internal IDs, and resource paths separately. Display-name changes do not require renaming existing model files or directories.

### 4.3 recogniser 0 (numbers) Interaction View

- Show the model name, concise instructions, and navigation back to the model list.
- Provide two input modes: image upload and mouse drawing.
- Switching input modes does not require reselecting the model.
- Show an input area, a recognition action, and result/status messages.
- Clear the previous result when the image changes, drawing changes, or input mode changes.

### 4.4 Image Upload

- Let the user select a local image and preview it.
- After a valid selection, show the original image inside the upload area in place of the placeholder text. Use a responsive square preview of approximately 320 × 320 CSS pixels that scales images both up and down to fit without stretching or cropping. Apply pixelated rendering to low-resolution sources so enlarged digit pixels stay clear. Keep **Choose image** enabled below the preview, and keep the recognition action and result/status area below the upload controls.
- A new valid selection replaces the preview and clears the previous prediction or error. An outstanding result for the replaced image must not update the new result area. Cancelling the file picker preserves the current image and result.
- The preview shows the uploaded original, not the processed 28 × 28 model input. Do not add a separate processed-input preview panel.
- Convert it to the model's 28 × 28 input format.
- Inference runs when the user clicks the explicit recognition button; automatic recognition remains undecided.
- Support a single digit in the first release. Page detection, multiple-digit segmentation, and general OCR are outside this scope.
- PNG and JPEG uploads are supported up to 20 MB. Digit-region extraction and framing are confirmed in section 6.2.

### 4.5 Mouse Drawing

- Use a normal freehand canvas rather than a pixel-by-pixel grid.
- Display it responsively as a square, large enough for comfortable mouse input and scaled with the workspace. Its display size is independent of the 28 × 28 model input.
- Follow the resolved application theme:
  - **Light:** white canvas background with black strokes.
  - **Dark:** black canvas background with white strokes.
  - **Follow system:** use the palette of the currently resolved light or dark theme.
- Annotate each drawing submission with its explicit canvas polarity. The metadata describes the submitted pixels, not the current theme setting.
- Switching themes while a drawing exists preserves its geometry and converts its background and stroke colours consistently with the newly resolved palette. Do not silently clear the drawing or change its interpretation. Update the polarity metadata to match the converted canvas.
- Convert the drawing to the model's dark-background, bright-stroke representation before inference using the submitted polarity as defined in Section 6.
- Provide Clear and Recognise actions.
- Reject an empty canvas with an appropriate prompt instead of interpreting its model score as a valid recognition result.

### 4.6 Appearance and Settings

- Default to light mode.
- Provide Light, Dark, and Follow system options in settings.
- Follow system uses the current system appearance when selected; it is not the default setting.
- Theme changes affect presentation and drawing-canvas colours. They do not change a drawing's geometry or interpretation, and they do not affect thresholds or model behaviour.
- Whether the preference persists across launches and where settings appear remain undecided.
- Use a minimal visual style inspired by Codex's restrained desktop interface, without requiring a pixel-perfect recreation.
- Use neutral colours, generous whitespace, clear typography, subtle borders, and lightweight buttons, with consistent spacing and corner radii.
- Focus the welcome screen on the greeting and model selection; focus model views on input, mode selection, and recognition results.
- Avoid large gradients, heavy shadows, decorative illustrations, promotional headings, and unnecessary animation.
- Preserve layout and readability in dark mode through appropriate background, text, and border colours.

## 5. Prediction and Confidence Rules

Use a confidence threshold of `0.90`, comparing the raw score before display rounding.

| Condition | User-facing behaviour |
| --- | --- |
| `confidence >= 0.90` | Show the predicted digit |
| `confidence < 0.90` | Show an unable-to-predict message suggesting another image or drawing |
| Empty or invalid input | Show an input-specific prompt without proceeding with normal recognition |
| Model loading or inference failure | Show an error distinct from a low-confidence result |

Exactly 90% is accepted. Low-confidence results must not reveal a candidate digit. Whether the confidence percentage is displayed alongside accepted or rejected results remains undecided.

The softmax score is a display and rejection heuristic, not a guaranteed probability of correctness. This threshold cannot reliably filter every non-digit image or incorrect prediction. The first release does not add confidence calibration or a separate unknown-input detection model.

User-facing error messages should be understandable rather than raw Python tracebacks or internal file paths. Exact wording depends on the eventual interface language.

## 6. Image Preprocessing

Proposed tools:

- Pillow for image decoding, grayscale conversion, resizing, padding, and inversion.
- NumPy for array conversion, data types, and pixel-value scaling.
- HTML Canvas for drawing input, submitted to Python as image data for processing.

Both input modes share the model's final Python preprocessing path. The frontend collects and presents input; Python validates and prepares the final model data.

The supplied training and data-loading code confirms that the only training transform is `ToTensor()`. The training loop subsequently flattens the tensor without additional image normalisation.

### 6.1 Drawing Input Polarity

Drawing submissions include explicit `canvas_polarity` metadata alongside the submitted image. The value describes the polarity of the actual submitted pixels, not the current theme preference, a stored setting, or the system appearance.

| `canvas_polarity` | Submitted drawing | Required preprocessing |
| --- | --- | --- |
| `dark_on_light` | Dark strokes on a light background (Light-theme canvas) | Invert the grayscale image |
| `light_on_dark` | Light strokes on a dark background (Dark-theme canvas) | Do not invert |

A drawing request therefore carries the submitted image together with this explicit field. The final bridge payload may add transport-specific fields later, but `canvas_polarity` must remain available to preprocessing.

The two paths must ultimately produce the same kind of input: a 28 × 28 grayscale `float32` array in `[0, 1]` with a dark background and bright strokes.

- The frontend records `canvas_polarity` from the drawing canvas at submission and sends it with that drawing's image data.
- Python preprocessing selects inversion from this metadata only. It must not infer inversion from the current application theme, the system appearance, or a theme preference that may have changed since the drawing was made.
- If a theme switch recolours an existing drawing, the frontend converts the background and strokes together, preserves the drawing's geometry, and updates `canvas_polarity` to match the converted pixels. The drawing's meaning and final normalized model input remain unchanged.
- A missing or invalid `canvas_polarity` on drawing input is invalid input. It must not be guessed from the current theme.
- Uploaded-image polarity is estimated from the submitted pixels, using the median brightness of the outer border. A bright border means the image is inverted; a dark border leaves it unchanged. This detection never consults the application theme or `canvas_polarity`.

### 6.2 Shared Final Input

The final inference input must therefore be:

| Property | Required value |
| --- | --- |
| Image size | 28 × 28 |
| Channels | One grayscale channel |
| Polarity | Dark background, bright digit strokes |
| Data type | `float32` |
| Pixel range | `[0, 1]` |
| Mean/std normalisation | None |
| Shape passed to ONNX | `(1, 784)`, produced by the existing inference function |

Processing sequence:

1. Decode the image and composite transparent regions onto an explicit background. A drawing is submitted with an opaque canvas background.
2. Convert to grayscale.
3. For drawing input, establish the required dark-background, bright-stroke polarity from `canvas_polarity`: invert `dark_on_light`; leave `light_on_dark` unchanged. Do not use the current theme to select this branch. Uploaded images use their separate policy and never use `canvas_polarity`.
4. Produce a 28 × 28 image: crop to the digit's ink bounding box, preserve the aspect ratio, scale the longest side to 20 pixels, and place the result on a 28 × 28 black canvas with its centre of mass at the canvas centre. Subpixel placement avoids geometry shifts that change predictions for narrow digits.
5. Convert Pillow's 0–255 grayscale values to `float32` and divide by 255 once. Data already in `[0, 1]` must not be scaled again.
6. Pass the resulting 28 × 28 array to the existing inference function, which performs flattening.

`np.asarray(..., dtype=np.float32)` alone does not divide by 255. Scaling belongs in the preprocessing layer and must occur exactly once.

Training preprocessing is confirmed from the supplied source. The actual ONNX interface still requires validation during integration.

## 7. Lightweight Architecture

### 7.1 Responsibilities

| Component | Responsibility |
| --- | --- |
| Desktop entry point | Create the window, bind the Python API, and load the frontend |
| Shared navigation | Welcome screen, model selection, model views, and return navigation |
| Model registry | Stable ID, series number, task type, display name, description, view, and adapter mapping |
| Python API bridge | Validate requests, dispatch to the selected model, and return serialisable results |
| Model adapter | Preprocess input, call the existing inference function, and apply model-specific result rules |
| Model view | Present the model's input modes and results |

Provisional communication mechanism: pywebview's JavaScript–Python bridge. No additional FastAPI/Flask server or frontend framework is planned for the first release. Exact API usage depends on the selected dependency versions.

### 7.2 Project Structure

The project root contains `frontend/`, `backend/`, and `models/`. Shared backend code belongs in `backend/`; model resources and original inference scripts remain in `models/`.

Initial project contents:

```text
recogniser/
  PLAN.md
  models/
    0-numbers/
      model_0_numbers.onnx
      model_0_numbers.py
```

`PLAN.md` is a Markdown file, while `models/` is a directory. Frontend and backend files are added as implementation progresses.

Proposed implementation structure:

```text
recogniser/
  PLAN.md
  requirements.txt
  backend/
    __init__.py
    main.py
    api.py
    model_registry.py
    adapters/
      __init__.py
      numbers.py
  frontend/
    index.html
    css/
      style.css
      themes.css
    js/
      main.js
      bridge.js
      settings.js
    models/
      numbers.js
  models/
    0-numbers/
      model_0_numbers.onnx
      model_0_numbers.py
```

The module split is provisional and may be adjusted to keep responsibilities clear without creating unnecessary empty files. The separate agent-instructions file is not defined by this product structure and will be supplied independently.

| Path | Purpose |
| --- | --- |
| `PLAN.md` | Requirements, architecture, milestones, and acceptance criteria |
| `requirements.txt` | Python runtime dependencies for the application |
| `backend/main.py` | Desktop entry point and pywebview window/API setup |
| `backend/api.py` | Python functions exposed to the frontend |
| `backend/model_registry.py` | Model registration and adapter/view mapping |
| `backend/adapters/numbers.py` | Digit preprocessing, inference invocation, and threshold/result conversion |
| `frontend/index.html` | Application shell, welcome screen, and shared navigation |
| `frontend/css/` | Layout, components, and light/dark theme styles |
| `frontend/js/` | Navigation, Python bridge, and settings interaction |
| `frontend/models/numbers.js` | Digit-specific upload, drawing, and result interface |
| `models/0-numbers/` | ONNX resource and original inference script |

Proposed launch command from the project root:

```bash
python -m backend.main
```

Frontend and model-resource paths are resolved relative to source locations rather than relying on the current working directory.

The existing `models/0-numbers/` path is retained. Since `0-numbers` is not a valid identifier for ordinary Python package imports, loading requires a simple explicit file-path mapping rather than a regular dotted import through that directory.

Future models add resources under `models/<model-directory>/`, an adapter under `backend/adapters/`, a view under `frontend/models/`, and a registry entry. Internal IDs, filenames, and display names are independent.

### 7.3 Extension Behaviour

- Each model owns its input shape, preprocessing, supported interactions, output interpretation, and any confidence policy.
- The application does not assume all models accept 784 values, classify digits, or use a 90% threshold.
- CNN-specific tensor layouts belong to the corresponding adapter.
- Adding a model should not require rewriting the welcome screen or the existing digit view.
- Load models on demand and reuse each loaded inference session.
- Explicit registration is sufficient for the first release; automatic plugin discovery and hot loading are outside scope.
- Model failures leave navigation available so the application remains usable.

### 7.4 Frontend–Backend Result Contract

Shared result statuses are `ok`, `uncertain`, `invalid_input`, and `error`.

Digit results contain `prediction`, `confidence`, and a user-facing message. For low-confidence results, the user-facing payload uses `prediction: null`.

The original inference function continues returning `(prediction, confidence)`; the adapter converts it to the application result format.

The digit model's exposed API call is `recognise_upload(model_id, image_data_url)`. The model ID must match a registered model, the request must use upload input, and unexpected internal failures return the generic `error` envelope without exposing implementation details.

Future models can return model-specific data within the shared status envelope. Image-transfer format and payload schemas beyond the digit model remain implementation details to settle for those models.

## 8. Implementation Milestones and Acceptance Criteria

### Milestone 1: Desktop Shell and Navigation

- Create a launchable pywebview window.
- Implement the welcome screen, registry-driven model list, digit-model view, and return navigation.
- Display `recogniser 0 (numbers)` consistently in all user-facing model labels.
- List only the single integrated model in the first release.
- Implement default light mode and the Light, Dark, and Follow system settings.
- Acceptance: the application opens, shows the welcome screen and model, and supports navigation. Views without inference integration do not present fabricated recognition results.

### Milestone 2: Model Integration and Image Upload

- Validate the ONNX interface and connect the existing inference function using the confirmed preprocessing contract.
- Implement upload, inference, and threshold-based result presentation.
- Acceptance: known MNIST samples produce matching predictions/scores through the client and direct inference when given identical processed input. Invalid files, low-confidence results, and loading failures produce appropriate feedback.

### Milestone 3: Freehand Drawing

- Implement the responsive theme-aware canvas, theme-switch colour conversion, explicit canvas-polarity metadata, Clear action, and recognition.
- Acceptance: pointer coordinates and scaling are correct; blank input is rejected; changed input clears old results; both modes follow the same final input contract. A theme switch with an existing drawing preserves its geometry and interpretation while converting its palette and metadata. Equivalent Light- and Dark-theme drawings produce the same 28 × 28 grayscale `float32` input after their metadata-directed preprocessing.

### Milestone 4: End-to-End Verification and Usage Documentation

- Verify model/mode navigation, repeated recognition, error recovery, and view state.
- Keep the interface responsive during inference and prevent duplicate submissions or stale results from replacing current input results.
- Document dependencies, launch instructions, and the process for adding another model.
- Acceptance: the agreed entry point launches the application and both recognition flows work end to end.

Targeted automated checks cover confidence values `0.8999`, `0.90`, and `0.9001`, along with preprocessing shape, data type, range, and both `canvas_polarity` branches. Threshold-boundary checks use controlled scores rather than depending on an actual model to produce an exact boundary value.

## 9. Outside the First Release

- Training or replacing models.
- A model-download marketplace.
- Accounts or cloud inference.
- A recognition-history database.
- Automatic application updates.
- Multiple-digit detection or general OCR.
- Installer packaging.
- A complex plugin system or separate unknown-input detection model.

## 10. Open Product Decisions

| Topic | Current proposal or unresolved question |
| --- | --- |
| Confidence display | Threshold confirmed; percentage visibility remains undecided |
| Recognition trigger | Explicit button confirmed; automatic recognition undecided |
| Interface language | Undecided; the English language of this plan does not determine the UI language |
| Theme settings | Preference persistence and settings-entry placement |
| Target platforms | Windows first versus additional desktop systems |

Agent workflow, approval/reporting conventions, and Git-operation rules are intentionally left for the separate `AGENT.md` document.
