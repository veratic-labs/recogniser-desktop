"""Python functions exposed to the frontend through pywebview's JS bridge."""

from __future__ import annotations

import importlib
import logging
from typing import Any

from .adapters import InvalidInputError, ModelUnavailableError
from .model_registry import all_models, find_model

LOGGER = logging.getLogger(__name__)

MODEL_ERROR_MESSAGE = (
    "The model could not be loaded or run. Try again, or restart the application."
)


def _result(status: str, message: str) -> dict[str, Any]:
    """Return the shared result envelope used by every model view."""
    return {
        "status": status,
        "prediction": None,
        "confidence": None,
        "message": message,
    }


class Api:
    """The API object bound to the desktop window."""

    def get_models(self) -> list[dict[str, Any]]:
        """Return the registered models for the welcome list and selector."""
        return [model.as_dict() for model in all_models()]

    def recognise_upload(self, model_id: str, image_data_url: str) -> dict[str, Any]:
        """Run an uploaded image through the selected model's upload adapter."""
        model = find_model(model_id) if isinstance(model_id, str) else None
        if model is None:
            return _result("error", "That model is not available.")
        if not any(mode.id == "upload" for mode in model.input_modes):
            return _result("error", "That model does not support image upload.")

        try:
            adapter = importlib.import_module(model.adapter)
            recognise = getattr(adapter, "recognise_upload", None)
            if not callable(recognise):
                raise ModelUnavailableError(
                    "The model adapter does not support image upload."
                )
            return recognise(image_data_url)
        except InvalidInputError as exc:
            return _result("invalid_input", str(exc))
        except ModelUnavailableError:
            LOGGER.exception("The digit model could not be loaded or used.")
            return _result("error", MODEL_ERROR_MESSAGE)
        except Exception:
            LOGGER.exception("Unexpected failure while recognising an uploaded image.")
            return _result("error", MODEL_ERROR_MESSAGE)

    def recognise_drawing(
        self,
        model_id: str,
        image_data_url: str,
        canvas_polarity: str,
    ) -> dict[str, Any]:
        """Run a submitted drawing through the selected model's drawing adapter.

        ``canvas_polarity`` describes the pixels in ``image_data_url``; the
        adapter selects the required preprocessing branch from it and never
        from the current theme.
        """
        model = find_model(model_id) if isinstance(model_id, str) else None
        if model is None:
            return _result("error", "That model is not available.")
        if not any(mode.id == "drawing" for mode in model.input_modes):
            return _result("error", "That model does not support drawing input.")

        try:
            adapter = importlib.import_module(model.adapter)
            recognise = getattr(adapter, "recognise_drawing", None)
            if not callable(recognise):
                raise ModelUnavailableError(
                    "The model adapter does not support drawing input."
                )
            return recognise(image_data_url, canvas_polarity)
        except InvalidInputError as exc:
            return _result("invalid_input", str(exc))
        except ModelUnavailableError:
            LOGGER.exception("The digit model could not be loaded or used.")
            return _result("error", MODEL_ERROR_MESSAGE)
        except Exception:
            LOGGER.exception("Unexpected failure while recognising a drawing.")
            return _result("error", MODEL_ERROR_MESSAGE)
