"""Registration data shared by the welcome list, selector, and model views.

The welcome screen, the shared model selector, and model view headers all read
from this registry, so adding a model requires one entry here together with its
matching frontend view. Display names, stable internal IDs, and resource paths
are stored independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class InputMode:
    """An input method offered by a model, such as upload or drawing."""

    id: str
    label: str
    hint: str


@dataclass(frozen=True)
class ModelRegistration:
    """Metadata and mappings for one available model."""

    id: str
    series: int
    task_type: str
    display_name: str
    description: str
    instructions: str
    input_label: str
    input_note: str
    input_modes: tuple[InputMode, ...]
    frontend_view: str
    adapter: str
    resource_dir: str

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation for the frontend."""
        return {
            "id": self.id,
            "series": self.series,
            "task_type": self.task_type,
            "display_name": self.display_name,
            "description": self.description,
            "instructions": self.instructions,
            "input_label": self.input_label,
            "input_note": self.input_note,
            "input_modes": [
                {"id": mode.id, "label": mode.label, "hint": mode.hint}
                for mode in self.input_modes
            ],
            "frontend_view": self.frontend_view,
            "adapter": self.adapter,
        }


NUMBERS_0 = ModelRegistration(
    id="numbers-0",
    series=0,
    task_type="numbers",
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
    input_note="One grayscale digit on a dark background with bright strokes.",
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
    adapter="backend.adapters.numbers",
    resource_dir="models/0-numbers",
)

_MODELS: tuple[ModelRegistration, ...] = (NUMBERS_0,)


def all_models() -> tuple[ModelRegistration, ...]:
    """Return every registered model in display order."""
    return _MODELS


def find_model(model_id: str) -> ModelRegistration | None:
    """Return the model with the given stable ID, if it is registered."""
    return next((model for model in _MODELS if model.id == model_id), None)
