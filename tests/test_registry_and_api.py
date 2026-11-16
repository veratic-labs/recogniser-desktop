"""Focused regression checks for registry integrity and API validation.

Run from the project root with:

    python -m unittest discover -s tests -v

These checks do not open a GUI, use the network, or run inference. Adapter
modules are imported only to inspect their public function names. Any patched
registry or import state is restored by ``unittest.mock`` before a test returns.
"""

from __future__ import annotations

import dataclasses
import importlib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from backend import api
from backend.adapters import InvalidInputError, ModelUnavailableError
from backend.model_registry import (
    NUMBERS,
    NUMBERS_0,
    all_categories,
    all_models,
    find_category,
    find_model,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CATEGORY_MESSAGE = "That category is not available."
MODEL_MESSAGE = "That model is not available in this category."
UPLOAD_MESSAGE = "That category does not support image upload."
DRAWING_MESSAGE = "That category does not support drawing input."
FALLBACK_MESSAGE = "That category does not support this input mode."


class RegistryIntegrityTests(unittest.TestCase):
    """Check the current explicit registration data and resource mapping."""

    def test_ids_are_unique_and_models_reference_registered_categories(self):
        categories = all_categories()
        models = all_models()
        category_ids = [category.id for category in categories]
        model_ids = [model.id for model in models]

        self.assertTrue(category_ids, "At least one category must be registered.")
        self.assertTrue(all(category_ids))
        self.assertTrue(all(model_ids))
        self.assertEqual(len(category_ids), len(set(category_ids)))
        self.assertEqual(len(model_ids), len(set(model_ids)))

        for category in categories:
            mode_ids = [mode.id for mode in category.input_modes]
            with self.subTest(category=category.id):
                self.assertEqual(len(mode_ids), len(set(mode_ids)))

        for model in models:
            with self.subTest(model=model.id):
                self.assertTrue(model.id)
                self.assertIn(model.category_id, category_ids)
                self.assertIsNotNone(find_category(model.category_id))

    def test_current_model_resource_mapping_is_correct(self):
        model = find_model("numbers-0")
        self.assertIsNotNone(model)
        assert model is not None
        self.assertEqual(model.category_id, "numbers")
        self.assertEqual(model.adapter, "backend.adapters.numbers")
        self.assertEqual(model.resource_dir, "models/0-numbers")

        resource_dir = PROJECT_ROOT / model.resource_dir
        self.assertTrue(resource_dir.is_dir(), resource_dir)
        for filename in ("model_0_numbers.onnx", "model_0_numbers.py"):
            with self.subTest(filename=filename):
                self.assertTrue((resource_dir / filename).is_file())

    def test_each_model_adapter_supports_its_category_input_modes(self):
        for model in all_models():
            category = find_category(model.category_id)
            self.assertIsNotNone(category)
            assert category is not None
            module = importlib.import_module(model.adapter)
            for mode in category.input_modes:
                with self.subTest(
                    model=model.id, adapter=model.adapter, mode=mode.id
                ):
                    function = getattr(module, f"recognise_{mode.id}", None)
                    self.assertTrue(
                        callable(function),
                        f"{model.adapter} has no recognise_{mode.id} function",
                    )


class ApiValidationTests(unittest.TestCase):
    """Check category, model, and input-mode rejection behaviour."""

    def setUp(self):
        self.client = api.Api()

    def assert_error(self, result, message):
        self.assertEqual(
            result,
            {
                "status": "error",
                "prediction": None,
                "confidence": None,
                "message": message,
            },
        )

    def test_unknown_category_is_rejected(self):
        result = self.client.recognise_category_upload(
            "not-a-category", NUMBERS_0.id, "not-an-image"
        )
        self.assert_error(result, CATEGORY_MESSAGE)

    def test_unknown_model_is_rejected(self):
        result = self.client.recognise_category_upload(
            NUMBERS.id, "not-a-model", "not-an-image"
        )
        self.assert_error(result, MODEL_MESSAGE)

    def test_model_from_another_category_is_rejected(self):
        mismatch = dataclasses.replace(
            NUMBERS_0,
            id="numbers-model-elsewhere",
            category_id="another-category",
        )
        with mock.patch.object(api, "find_model", return_value=mismatch):
            result = self.client.recognise_category_upload(
                NUMBERS.id, mismatch.id, "not-an-image"
            )
        self.assert_error(result, MODEL_MESSAGE)
        self.assertEqual(find_model("numbers-0"), NUMBERS_0)

    def test_standard_unsupported_modes_keep_their_messages(self):
        upload_mode = next(
            mode for mode in NUMBERS.input_modes if mode.id == "upload"
        )
        drawing_mode = next(
            mode for mode in NUMBERS.input_modes if mode.id == "drawing"
        )
        drawing_only = dataclasses.replace(
            NUMBERS, input_modes=(drawing_mode,)
        )
        upload_only = dataclasses.replace(
            NUMBERS, input_modes=(upload_mode,)
        )

        with mock.patch.object(api, "find_category", return_value=drawing_only):
            upload_result = self.client.recognise_category_upload(
                NUMBERS.id, NUMBERS_0.id, "not-an-image"
            )
        self.assert_error(upload_result, UPLOAD_MESSAGE)

        with mock.patch.object(api, "find_category", return_value=upload_only):
            drawing_result = self.client.recognise_category_drawing(
                NUMBERS.id,
                NUMBERS_0.id,
                "not-an-image",
                "dark_on_light",
            )
        self.assert_error(drawing_result, DRAWING_MESSAGE)

        restored = find_category(NUMBERS.id)
        self.assertEqual(
            [mode.id for mode in restored.input_modes], ["upload", "drawing"]
        )

    def test_unmapped_mode_uses_the_neutral_fallback(self):
        model, result = api._resolve(NUMBERS.id, NUMBERS_0.id, "video")
        self.assertIsNone(model)
        self.assert_error(result, FALLBACK_MESSAGE)


class AdapterErrorMappingTests(unittest.TestCase):
    """Check the API's adapter error-to-status translation without inference."""

    def run_adapter(self, function):
        module = SimpleNamespace(recognise_upload=function)
        with mock.patch(
            "backend.api.importlib.import_module", return_value=module
        ):
            return api._run_adapter(
                NUMBERS_0,
                "recognise_upload",
                ("payload",),
                "an upload",
            )

    def test_invalid_input_becomes_invalid_input_status(self):
        message = "The supplied image cannot be used."

        def invalid_input(_payload):
            raise InvalidInputError(message)

        result = self.run_adapter(invalid_input)
        self.assertEqual(
            result,
            {
                "status": "invalid_input",
                "prediction": None,
                "confidence": None,
                "message": message,
            },
        )

    def test_model_unavailable_and_unexpected_errors_become_error_status(self):
        errors = (
            ModelUnavailableError("The model resources are missing."),
            RuntimeError("Unexpected adapter failure."),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__):
                def fail(_payload, error=error):
                    raise error

                with mock.patch.object(api.LOGGER, "exception"):
                    result = self.run_adapter(fail)
                self.assertEqual(
                    result,
                    {
                        "status": "error",
                        "prediction": None,
                        "confidence": None,
                        "message": api.MODEL_ERROR_MESSAGE,
                    },
                )

    def test_missing_adapter_function_becomes_error_status(self):
        module = SimpleNamespace()
        with mock.patch(
            "backend.api.importlib.import_module", return_value=module
        ), mock.patch.object(api.LOGGER, "exception"):
            result = api._run_adapter(
                NUMBERS_0, "recognise_upload", ("payload",), "an upload"
            )
        self.assertEqual(
            result,
            {
                "status": "error",
                "prediction": None,
                "confidence": None,
                "message": api.MODEL_ERROR_MESSAGE,
            },
        )

    def test_adapter_import_failure_becomes_error_status(self):
        with mock.patch(
            "backend.api.importlib.import_module",
            side_effect=ImportError("Adapter unavailable."),
        ), mock.patch.object(api.LOGGER, "exception"):
            result = api._run_adapter(
                NUMBERS_0, "recognise_upload", ("payload",), "an upload"
            )
        self.assertEqual(
            result,
            {
                "status": "error",
                "prediction": None,
                "confidence": None,
                "message": api.MODEL_ERROR_MESSAGE,
            },
        )

    def test_successful_adapter_result_is_returned_unchanged(self):
        expected = {
            "status": "ok",
            "prediction": 4,
            "confidence": 0.99,
            "message": "Predicted digit: 4.",
        }
        result = self.run_adapter(lambda _payload: expected)
        self.assertIs(result, expected)


if __name__ == "__main__":
    unittest.main()
