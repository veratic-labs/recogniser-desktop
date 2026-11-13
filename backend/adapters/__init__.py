"""Model adapters and the errors they use to report unusable input or models.

Adapters preprocess input, invoke the model's existing inference code, and
convert the raw result into the shared frontend result envelope. Errors are
raised with user-facing messages so the API layer can return them without
exposing tracebacks or internal paths.
"""

from __future__ import annotations


class InvalidInputError(ValueError):
    """The supplied input is missing, malformed, or cannot be used."""


class ModelUnavailableError(RuntimeError):
    """The model resources, interface, or inference call are unavailable."""
