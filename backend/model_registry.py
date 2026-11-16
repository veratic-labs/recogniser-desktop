"""Registration data shared by the category list, category views, and models.

Categories own the interactions: which input modes they offer and which shared
frontend view renders them. Models own their identity, presentation text, input
format, adapter, and resource paths, so tensor dimensions and preprocessing
never belong to a category. Adding a model therefore needs one category
reference and its own backend adapter, while adding a category needs its input
modes and one shared frontend view.

Display names, stable internal IDs, and resource paths are stored
independently, so a display-name change never renames model directories.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class InputMode:
    """An input method offered by a category, such as upload or drawing."""

    id: str
    label: str
    hint: str

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-serialisable representation of the input mode."""
        return {"id": self.id, "label": self.label, "hint": self.hint}


@dataclass(frozen=True)
class ModelRegistration:
    """Identity, presentation, and inference metadata for one model.

    ``input_label`` describes this model's own input format. It is deliberately
    model-owned: models in one category may use different dimensions.
    """

    id: str
    category_id: str
    series: int
    display_name: str
    description: str
    instructions: str
    input_label: str
    adapter: str
    resource_dir: str

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation for the frontend."""
        return {
            "id": self.id,
            "category_id": self.category_id,
            "series": self.series,
            "display_name": self.display_name,
            "description": self.description,
            "instructions": self.instructions,
            "input_label": self.input_label,
        }


@dataclass(frozen=True)
class CategoryRegistration:
    """A group of models that share one interaction view and input modes."""

    id: str
    label: str
    description: str
    guidance: str
    input_modes: tuple[InputMode, ...]
    frontend_view: str

    def as_dict(self) -> dict[str, Any]:
        """Return the category with its registered models nested below it."""
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "guidance": self.guidance,
            "frontend_view": self.frontend_view,
            "input_modes": [mode.as_dict() for mode in self.input_modes],
            "models": [model.as_dict() for model in models_for_category(self.id)],
        }


NUMBERS = CategoryRegistration(
    id="numbers",
    label="Numbers",
    description="Recognise handwritten digits from 0 to 9.",
    guidance="A single handwritten digit, from 0 to 9.",
    input_modes=(
        InputMode(
            id="upload",
            label="Image upload",
            hint="Choose a picture containing a single handwritten digit.",
        ),
        InputMode(
            id="drawing",
            label="Freehand drawing",
            hint="Draw one digit with the mouse on the canvas.",
        ),
    ),
    frontend_view="numbers",
)

NUMBERS_0 = ModelRegistration(
    id="numbers-0",
    category_id="numbers",
    series=0,
    display_name="recogniser 0 (numbers)",
    description=(
        "Recognises a single handwritten digit from 0 to 9. "
        "Trained on MNIST with a small multilayer perceptron."
    ),
    instructions=(
        "Provide one handwritten digit using an image or the drawing canvas. "
        "The model returns the digit it recognises and a confidence score."
    ),
    input_label="28 × 28",
    adapter="backend.adapters.numbers",
    resource_dir="models/0-numbers",
)

_CATEGORIES: tuple[CategoryRegistration, ...] = (NUMBERS,)
_MODELS: tuple[ModelRegistration, ...] = (NUMBERS_0,)


def all_categories() -> tuple[CategoryRegistration, ...]:
    """Return every registered category in display order."""
    return _CATEGORIES


def find_category(category_id: str) -> CategoryRegistration | None:
    """Return the category with the given stable ID, if it is registered."""
    return next(
        (category for category in _CATEGORIES if category.id == category_id),
        None,
    )


def models_for_category(category_id: str) -> tuple[ModelRegistration, ...]:
    """Return the registered models that belong to one category."""
    return tuple(
        model for model in _MODELS if model.category_id == category_id
    )


def all_models() -> tuple[ModelRegistration, ...]:
    """Return every registered model in display order."""
    return _MODELS


def find_model(model_id: str) -> ModelRegistration | None:
    """Return the model with the given stable ID, if it is registered."""
    return next((model for model in _MODELS if model.id == model_id), None)
