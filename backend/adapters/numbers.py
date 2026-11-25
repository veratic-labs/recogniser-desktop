"""Preprocessing and inference for recogniser 0 (numbers).

Uploaded images have their own polarity path. The background is estimated from
the image border, so recognition never depends on the application theme.

Drawing submissions instead carry explicit ``canvas_polarity`` metadata that
describes the submitted pixels: ``dark_on_light`` drawings are inverted, while
``light_on_dark`` drawings are used as submitted. Both paths then share the same
digit framing and produce the final model input required by PLAN.md section 6.2:

- 28 x 28, one grayscale channel
- dark background with bright strokes
- ``float32`` values in ``[0, 1]``, scaled exactly once
"""

from __future__ import annotations

import base64
import binascii
import importlib.util
import io
import threading
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

import numpy as np
from PIL import Image, UnidentifiedImageError

from ..model_registry import find_model
from ..paths import model_resource_path
from . import InvalidInputError, ModelUnavailableError

MODEL_ID = "numbers-0"
INFERENCE_SCRIPT = "model_0_numbers.py"
MODEL_FILENAME = "model_0_numbers.onnx"
PREDICT_FUNCTION = "model_0_numbers_predict"

INPUT_SIZE = 28
DIGIT_SIZE = 20
EXPECTED_INPUT_SHAPE = (1, 784)
EXPECTED_OUTPUT_SHAPE = (1, 10)
CONFIDENCE_THRESHOLD = 0.90

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_UPLOAD_MEGABYTES = MAX_UPLOAD_BYTES // (1024 * 1024)
SUPPORTED_FORMATS = frozenset({"PNG", "JPEG"})

# Polarity values the drawing canvas may report alongside a submitted drawing.
# The vocabulary describes the submitted pixels, not the current theme.
CANVAS_POLARITIES = frozenset({"dark_on_light", "light_on_dark"})

# A normalised drawing whose brightest pixel stays below this level is empty.
DRAWING_MIN_INK = 8

UPLOAD_READ_ERROR = (
    "The selected image could not be read. Choose a PNG or JPEG image."
)
UPLOAD_NO_DIGIT_MESSAGE = (
    "No digit was found in that image. Choose a picture with one clear "
    "handwritten digit."
)
DRAWING_EMPTY_MESSAGE = "The canvas is empty. Draw a digit before recognising."
DRAWING_NO_DIGIT_MESSAGE = (
    "No digit could be found in the drawing. Clear the canvas and draw the "
    "digit again."
)
DRAWING_UNREADABLE_MESSAGE = (
    "The drawing could not be read. Clear the canvas and draw the digit again."
)
DRAWING_MISSING_POLARITY_MESSAGE = (
    "The drawing did not include its canvas polarity. Clear the canvas and "
    "draw the digit again."
)

Predictor = Callable[[np.ndarray], tuple[int, float]]
_PREDICTOR: Predictor | None = None
_PREDICTOR_LOCK = threading.Lock()


def _model_resource(filename: str) -> Path:
    """Return a resource path from the registered model directory.

    ``resource_dir`` is relative registration metadata, so it is resolved
    through ``model_resource_path`` to work from a source checkout and from the
    frozen bundle alike.
    """
    model = find_model(MODEL_ID)
    if model is None:
        raise ModelUnavailableError("The digit model is not registered.")
    return model_resource_path(model.resource_dir, filename)


def _decode_data_url(
    data_url: str,
    *,
    missing_message: str,
    unreadable_message: str,
    empty_message: str,
) -> bytes:
    """Decode a base64 image data URL, rejecting unusable payloads."""
    if not isinstance(data_url, str) or not data_url.strip():
        raise InvalidInputError(missing_message)

    header, separator, payload = data_url.partition(",")
    if (
        not separator
        or "base64" not in header.lower()
        or "image/" not in header.lower()
    ):
        raise InvalidInputError(unreadable_message)

    # Reject oversized payloads before allocating the decoded bytes.
    if len(payload) > (MAX_UPLOAD_BYTES * 4) // 3 + 4:
        raise InvalidInputError(
            f"That image is larger than {MAX_UPLOAD_MEGABYTES} MB. "
            "Choose a smaller image."
        )

    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidInputError(unreadable_message) from exc

    if not raw:
        raise InvalidInputError(empty_message)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise InvalidInputError(
            f"That image is larger than {MAX_UPLOAD_MEGABYTES} MB. "
            "Choose a smaller image."
        )
    return raw


def _decode_upload(data_url: str) -> bytes:
    """Decode an upload data URL with upload-specific messages."""
    return _decode_data_url(
        data_url,
        missing_message="No image was provided. Choose an image to recognise.",
        unreadable_message=UPLOAD_READ_ERROR,
        empty_message="The selected image is empty. Choose another image.",
    )


def _decode_drawing(data_url: str) -> bytes:
    """Decode a drawing data URL with drawing-specific messages."""
    return _decode_data_url(
        data_url,
        missing_message="No drawing was provided. Draw a digit on the canvas first.",
        unreadable_message=DRAWING_UNREADABLE_MESSAGE,
        empty_message="The drawing is empty. Draw a digit on the canvas first.",
    )


def _flatten_alpha(image: Image.Image) -> Image.Image:
    """Composite transparent regions onto white, then return an RGB image."""
    if image.mode in {"RGBA", "LA"} or (
        image.mode == "P" and "transparency" in image.info
    ):
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(background, rgba).convert("RGB")
    return image.convert("RGB")


def _load_grayscale(raw: bytes) -> np.ndarray:
    """Decode image bytes to a uint8 grayscale array."""
    try:
        with Image.open(io.BytesIO(raw)) as opened:
            if opened.format not in SUPPORTED_FORMATS:
                raise InvalidInputError("Choose a PNG or JPEG image.")
            opened.load()
            if opened.width < 2 or opened.height < 2:
                raise InvalidInputError(
                    "That image is too small to contain a digit. "
                    "Choose a larger image."
                )
            flattened = _flatten_alpha(opened)
            return np.asarray(flattened.convert("L"), dtype=np.uint8)
    except InvalidInputError:
        raise
    except UnidentifiedImageError as exc:
        raise InvalidInputError(
            "That file is not a readable PNG or JPEG image."
        ) from exc
    except Image.DecompressionBombError as exc:
        raise InvalidInputError(
            "That image is too large to process. Choose a smaller image."
        ) from exc
    except (OSError, ValueError) as exc:
        raise InvalidInputError(
            "That image could not be read. It may be damaged or use an "
            "unsupported format."
        ) from exc


def _load_drawing_grayscale(raw: bytes) -> np.ndarray:
    """Decode a submitted drawing, reporting failures in drawing terms."""
    try:
        return _load_grayscale(raw)
    except InvalidInputError as exc:
        raise InvalidInputError(DRAWING_UNREADABLE_MESSAGE) from exc


def _background_is_bright(gray: np.ndarray) -> bool:
    """Estimate upload polarity from the median value of the outer border."""
    height, width = gray.shape
    border = max(1, min(height, width) // 20)
    edges = np.concatenate(
        (
            gray[:border, :].ravel(),
            gray[-border:, :].ravel(),
            gray[:, :border].ravel(),
            gray[:, -border:].ravel(),
        )
    )
    return float(np.median(edges)) >= 128.0


def _otsu_threshold(gray: np.ndarray) -> int:
    """Return an Otsu threshold separating bright strokes from the background."""
    histogram = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    total = float(histogram.sum())
    if total == 0.0:
        return 0

    levels = np.arange(256, dtype=np.float64)
    sum_total = float(np.dot(levels, histogram))
    weight_background = 0.0
    sum_background = 0.0
    best_variance = -1.0
    best_threshold = 0

    for threshold in range(256):
        weight_background += histogram[threshold]
        if weight_background == 0.0:
            continue
        weight_foreground = total - weight_background
        if weight_foreground == 0.0:
            break
        sum_background += levels[threshold] * histogram[threshold]
        mean_background = sum_background / weight_background
        mean_foreground = (sum_total - sum_background) / weight_foreground
        variance = (
            weight_background
            * weight_foreground
            * (mean_background - mean_foreground) ** 2
        )
        if variance > best_variance:
            best_variance = variance
            best_threshold = threshold

    return best_threshold


def _digit_bounds(
    gray: np.ndarray, message: str = UPLOAD_NO_DIGIT_MESSAGE
) -> tuple[int, int, int, int]:
    """Return the bounding box of the digit's bright strokes."""
    threshold = _otsu_threshold(gray)
    mask = gray > threshold
    if not bool(mask.any()):
        raise InvalidInputError(message)

    rows = np.flatnonzero(mask.any(axis=1))
    columns = np.flatnonzero(mask.any(axis=0))
    return int(rows[0]), int(rows[-1]), int(columns[0]), int(columns[-1])


def _frame_digit(
    gray: np.ndarray, empty_message: str = UPLOAD_NO_DIGIT_MESSAGE
) -> np.ndarray:
    """Crop the digit and centre it, aspect-preserved, on a 28 x 28 canvas.

    The digit is scaled so its longest side is 20 pixels, matching the MNIST
    normalisation used for training, then placed so that its centre of mass
    sits at the canvas centre. Subpixel placement avoids a quantisation shift
    that otherwise changes predictions for narrow digits such as 9 and 7.
    """
    top, bottom, left, right = _digit_bounds(gray, empty_message)
    crop = Image.fromarray(gray[top : bottom + 1, left : right + 1])

    width, height = crop.size
    scale = DIGIT_SIZE / max(width, height)
    resized_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    resized = crop.resize(resized_size, Image.Resampling.LANCZOS)
    values = np.asarray(resized, dtype=np.float64)

    total = float(values.sum())
    if total <= 0.0:
        raise InvalidInputError(empty_message)

    resized_width, resized_height = resized_size
    rows = np.arange(resized_height, dtype=np.float64)
    columns = np.arange(resized_width, dtype=np.float64)
    centre_row = float(np.dot(values.sum(axis=1), rows) / total)
    centre_column = float(np.dot(values.sum(axis=0), columns) / total)

    # Keep the whole digit inside the canvas; a digit fitted within 20 pixels
    # has enough slack for this clamp to matter only at extreme masses.
    offset_row = min(
        max(INPUT_SIZE / 2.0 - centre_row, 0.0),
        float(INPUT_SIZE - resized_height),
    )
    offset_column = min(
        max(INPUT_SIZE / 2.0 - centre_column, 0.0),
        float(INPUT_SIZE - resized_width),
    )

    grid_rows, grid_columns = np.meshgrid(
        np.arange(resized_height, dtype=np.float64),
        np.arange(resized_width, dtype=np.float64),
        indexing="ij",
    )
    target_rows = grid_rows + offset_row
    target_columns = grid_columns + offset_column
    row_base = np.floor(target_rows).astype(int)
    column_base = np.floor(target_columns).astype(int)
    row_fraction = target_rows - row_base
    column_fraction = target_columns - column_base

    canvas = np.zeros((INPUT_SIZE, INPUT_SIZE), dtype=np.float64)
    for row_shift, row_weight in ((0, 1.0 - row_fraction), (1, row_fraction)):
        for column_shift, column_weight in (
            (0, 1.0 - column_fraction),
            (1, column_fraction),
        ):
            canvas_rows = row_base + row_shift
            canvas_columns = column_base + column_shift
            inside = (
                (canvas_rows >= 0)
                & (canvas_rows < INPUT_SIZE)
                & (canvas_columns >= 0)
                & (canvas_columns < INPUT_SIZE)
            )
            np.add.at(
                canvas,
                (canvas_rows[inside], canvas_columns[inside]),
                (values * row_weight * column_weight)[inside],
            )

    prepared = np.clip(canvas, 0.0, 255.0).astype(np.float32) / 255.0
    return prepared


def _validate_prepared(prepared: np.ndarray) -> None:
    """Guard the preprocessing contract before handing data to the model."""
    if prepared.shape != (INPUT_SIZE, INPUT_SIZE):
        raise ModelUnavailableError("The prepared model input has an unexpected shape.")
    if prepared.dtype != np.float32:
        raise ModelUnavailableError("The prepared model input has an unexpected type.")
    if not bool(np.isfinite(prepared).all()):
        raise ModelUnavailableError("The prepared model input contains invalid values.")
    if float(prepared.min()) < 0.0 or float(prepared.max()) > 1.0:
        raise ModelUnavailableError(
            "The prepared model input is outside the expected range."
        )


def prepare_upload(data_url: str) -> np.ndarray:
    """Decode and prepare an uploaded image for the digit model."""
    raw = _decode_upload(data_url)
    gray = _load_grayscale(raw)

    # Uploaded-image polarity is independent of the application theme.
    if _background_is_bright(gray):
        gray = 255 - gray

    prepared = _frame_digit(gray)
    _validate_prepared(prepared)
    return prepared


def _normalise_drawing(gray: np.ndarray, canvas_polarity: Any) -> np.ndarray:
    """Return a drawing on the model's dark background with bright strokes.

    Inversion is selected from the submitted drawing's own metadata only. The
    theme preference and system appearance are never consulted, because either
    may have changed since the drawing was made.
    """
    if not isinstance(canvas_polarity, str) or canvas_polarity not in CANVAS_POLARITIES:
        raise InvalidInputError(DRAWING_MISSING_POLARITY_MESSAGE)

    if canvas_polarity == "dark_on_light":
        return 255 - gray
    return gray


def _drawing_has_ink(gray: np.ndarray) -> bool:
    """Report whether a normalised drawing contains any visible stroke."""
    return int(gray.max(initial=0)) >= DRAWING_MIN_INK


def prepare_drawing(data_url: str, canvas_polarity: Any) -> np.ndarray:
    """Decode a submitted drawing and prepare the digit model input.

    ``canvas_polarity`` describes the submitted pixels, so a Light-theme
    drawing (dark strokes on white) is inverted while a Dark-theme drawing
    (bright strokes on black) is used as submitted. Both branches then share
    the upload path's framing and scaling.
    """
    raw = _decode_drawing(data_url)
    gray = _load_drawing_grayscale(raw)
    gray = _normalise_drawing(gray, canvas_polarity)

    if not _drawing_has_ink(gray):
        raise InvalidInputError(DRAWING_EMPTY_MESSAGE)

    prepared = _frame_digit(gray, DRAWING_NO_DIGIT_MESSAGE)
    _validate_prepared(prepared)
    return prepared


def _validate_model_interface(module: ModuleType) -> None:
    """Verify the ONNX session matches the interface confirmed for this model."""
    session = getattr(module, "session", None)
    if session is None:
        raise ModelUnavailableError("The digit model does not expose an ONNX session.")

    inputs = session.get_inputs()
    outputs = session.get_outputs()
    if (
        len(inputs) != 1
        or inputs[0].name != "input"
        or inputs[0].type != "tensor(float)"
        or tuple(inputs[0].shape) != EXPECTED_INPUT_SHAPE
    ):
        raise ModelUnavailableError(
            "The digit model input does not match the expected 784-value input."
        )
    if (
        len(outputs) != 1
        or outputs[0].name != "output"
        or outputs[0].type != "tensor(float)"
        or tuple(outputs[0].shape) != EXPECTED_OUTPUT_SHAPE
    ):
        raise ModelUnavailableError(
            "The digit model output does not match the expected ten scores."
        )


def _load_predictor() -> Predictor:
    """Load the existing inference script once and reuse its session."""
    global _PREDICTOR

    if _PREDICTOR is not None:
        return _PREDICTOR

    with _PREDICTOR_LOCK:
        if _PREDICTOR is not None:
            return _PREDICTOR

        script_path = _model_resource(INFERENCE_SCRIPT)
        model_path = _model_resource(MODEL_FILENAME)
        if not script_path.is_file() or not model_path.is_file():
            raise ModelUnavailableError("The digit model files are missing.")

        spec = importlib.util.spec_from_file_location(
            "recogniser_numbers_0", script_path
        )
        if spec is None or spec.loader is None:
            raise ModelUnavailableError("The digit model could not be loaded.")

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            raise ModelUnavailableError("The digit model could not be loaded.") from exc

        _validate_model_interface(module)

        predict = getattr(module, PREDICT_FUNCTION, None)
        if not callable(predict):
            raise ModelUnavailableError(
                "The digit model does not provide an inference function."
            )

        _PREDICTOR = predict
        return predict


def _run_inference(prepared: np.ndarray) -> tuple[int, float]:
    """Call the existing inference function and validate its return values."""
    predictor = _load_predictor()
    try:
        prediction, confidence = predictor(prepared)
    except Exception as exc:
        raise ModelUnavailableError("The digit model could not run.") from exc

    if (
        isinstance(prediction, bool)
        or not isinstance(prediction, (int, np.integer))
        or not 0 <= int(prediction) <= 9
    ):
        raise ModelUnavailableError(
            "The digit model returned an unexpected prediction."
        )

    score = float(confidence)
    if not np.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ModelUnavailableError(
            "The digit model returned an unexpected confidence score."
        )

    return int(prediction), score


def build_result(prediction: int, confidence: float) -> dict[str, Any]:
    """Apply the confirmed 0.90 threshold and build the shared result envelope."""
    if confidence >= CONFIDENCE_THRESHOLD:
        return {
            "status": "ok",
            "prediction": int(prediction),
            "confidence": float(confidence),
            "message": f"Predicted digit: {int(prediction)}.",
        }

    # Low-confidence results never expose the candidate digit.
    return {
        "status": "uncertain",
        "prediction": None,
        "confidence": float(confidence),
        "message": (
            "Unable to predict with enough confidence. Try another image or drawing."
        ),
    }


def recognise_upload(image_data_url: str) -> dict[str, Any]:
    """Recognise the digit in an uploaded image and return the shared result."""
    prepared = prepare_upload(image_data_url)
    prediction, confidence = _run_inference(prepared)
    return build_result(prediction, confidence)


def recognise_drawing(image_data_url: str, canvas_polarity: Any) -> dict[str, Any]:
    """Recognise the digit in a submitted drawing and return the shared result."""
    prepared = prepare_drawing(image_data_url, canvas_polarity)
    prediction, confidence = _run_inference(prepared)
    return build_result(prediction, confidence)
