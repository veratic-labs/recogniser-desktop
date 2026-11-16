"""Python functions exposed to the frontend through pywebview's JS bridge."""

from __future__ import annotations

import importlib
import logging
from typing import Any

from .adapters import InvalidInputError, ModelUnavailableError
from .model_registry import (
    ModelRegistration,
    all_categories,
    find_category,
    find_model,
)

LOGGER = logging.getLogger(__name__)

MODEL_ERROR_MESSAGE = (
    "The model could not be loaded or run. Try again, or restart the application."
)

# Category-level input modes are shared by every model in the category.
MODE_SUPPORT_MESSAGES = {
    "upload": "That category does not support image upload.",
    "drawing": "That category does not support drawing input.",
}
# Used when an input mode has no specific support message.
DEFAULT_MODE_SUPPORT_MESSAGE = (
    "That category does not support this input mode."
)


def _result(status: str, message: str) -> dict[str, Any]:
    """Return the shared result envelope used by every model view."""
    return {
        "status": status,
        "prediction": None,
        "confidence": None,
        "message": message,
    }


def _resolve(
    category_id: Any,
    model_id: Any,
    mode_id: str,
) -> tuple[ModelRegistration | None, dict[str, Any] | None]:
    """Validate a category/model pair for one of the category's input modes."""
    category = find_category(category_id) if isinstance(category_id, str) else None
    if category is None:
        return None, _result("error", "That category is not available.")

    model = find_model(model_id) if isinstance(model_id, str) else None
    if model is None or model.category_id != category.id:
        return None, _result(
            "error", "That model is not available in this category."
        )

    if not any(mode.id == mode_id for mode in category.input_modes):
        return None, _result(
            "error",
            MODE_SUPPORT_MESSAGES.get(mode_id, DEFAULT_MODE_SUPPORT_MESSAGE),
        )

    return model, None


def _run_adapter(
    model: ModelRegistration,
    function_name: str,
    arguments: tuple[Any, ...],
    description: str,
) -> dict[str, Any]:
    """Call the model's adapter and convert failures into the shared envelope."""
    try:
        adapter = importlib.import_module(model.adapter)
        recognise = getattr(adapter, function_name, None)
        if not callable(recognise):
            raise ModelUnavailableError(
                f"The model adapter does not provide {function_name}."
            )
        return recognise(*arguments)
    except InvalidInputError as exc:
        return _result("invalid_input", str(exc))
    except ModelUnavailableError:
        LOGGER.exception("The model %s could not be loaded or used.", model.id)
        return _result("error", MODEL_ERROR_MESSAGE)
    except Exception:
        LOGGER.exception("Unexpected failure while recognising %s.", description)
        return _result("error", MODEL_ERROR_MESSAGE)


class Api:
    """The API object bound to the desktop window."""

    def get_categories(self) -> list[dict[str, Any]]:
        """Return every category with its registered models nested below it."""
        return [category.as_dict() for category in all_categories()]

    def recognise_category_upload(
        self,
        category_id: str,
        model_id: str,
        image_data_url: str,
    ) -> dict[str, Any]:
        """Run an upload through the selected model after category validation."""
        model, error = _resolve(category_id, model_id, "upload")
        if error is not None:
            return error
        assert model is not None
        return _run_adapter(
            model, "recognise_upload", (image_data_url,), "an uploaded image"
        )

    def recognise_category_drawing(
        self,
        category_id: str,
        model_id: str,
        image_data_url: str,
        canvas_polarity: str,
    ) -> dict[str, Any]:
        """Run a drawing through the selected model after category validation.

        ``canvas_polarity`` describes the pixels in ``image_data_url``; the
        adapter selects the required preprocessing branch from it and never
        from the current theme.
        """
        model, error = _resolve(category_id, model_id, "drawing")
        if error is not None:
            return error
        assert model is not None
        return _run_adapter(
            model,
            "recognise_drawing",
            (image_data_url, canvas_polarity),
            "a drawing",
        )
