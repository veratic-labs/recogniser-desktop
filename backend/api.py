"""Python functions exposed to the frontend through pywebview's JS bridge."""

from __future__ import annotations

from typing import Any

from .model_registry import all_models


class Api:
    """The API object bound to the desktop window."""

    def get_models(self) -> list[dict[str, Any]]:
        """Return the registered models for the welcome list and selector."""
        return [model.as_dict() for model in all_models()]
