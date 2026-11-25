"""Regression checks for the frozen-safe paths and the self-test rules.

Run from the project root with:

    python -m unittest discover -s tests -v

These checks never open a GUI window, import pythonnet, or run inference. The
only model call is ``prepare_upload``, which stops before the ONNX session is
created. Temporary data directories live under ``.tmp`` inside the project.
"""

from __future__ import annotations

import base64
import contextlib
import io
import json
import logging
import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from backend import diagnostics
from backend.adapters import numbers
from backend.api import Api
from backend.paths import (
    DATA_DIRECTORY_VARIABLE,
    data_dir,
    model_resource_path,
    resource_path,
    resource_root,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / ".tmp" / "path-tests"


@contextlib.contextmanager
def environment(**changes: object):
    """Patch ``os.environ``, removing a key when its value is ``None``."""
    with mock.patch.dict(os.environ):
        for key, value in changes.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(value)
        yield


def make_data_directory(name: str) -> Path:
    """Return a clean, absolute data directory under ``.tmp`` for one test."""
    directory = DATA_ROOT / name
    shutil.rmtree(directory, ignore_errors=True)
    return directory


class ResourcePathTests(unittest.TestCase):
    def test_source_checkout_uses_the_project_root(self):
        self.assertFalse(getattr(sys, "frozen", False))
        self.assertEqual(resource_root(), PROJECT_ROOT)

    def test_frontend_entry_point_resolves_from_the_project_root(self):
        index = resource_path("frontend", "index.html")
        self.assertTrue(index.is_file(), index)
        self.assertEqual(index, PROJECT_ROOT / "frontend" / "index.html")

    def test_model_directory_resolves_from_its_relative_registration(self):
        directory = model_resource_path("models/0-numbers")
        self.assertEqual(directory, PROJECT_ROOT / "models" / "0-numbers")
        for filename in ("model_0_numbers.py", "model_0_numbers.onnx"):
            self.assertTrue((directory / filename).is_file(), filename)
        self.assertEqual(
            model_resource_path("models/0-numbers", "model_0_numbers.onnx"),
            PROJECT_ROOT / "models" / "0-numbers" / "model_0_numbers.onnx",
        )

    def test_model_resource_ignores_the_working_directory(self):
        before = model_resource_path("models/0-numbers", "model_0_numbers.onnx")
        previous = os.getcwd()
        os.chdir(DATA_ROOT if DATA_ROOT.is_dir() else PROJECT_ROOT)
        self.addCleanup(os.chdir, previous)
        self.assertEqual(
            model_resource_path("models/0-numbers", "model_0_numbers.onnx"), before
        )

    def test_frozen_bundle_uses_the_extraction_directory(self):
        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(
            sys, "_MEIPASS", str(PROJECT_ROOT), create=True
        ):
            self.assertEqual(resource_root(), PROJECT_ROOT)
            self.assertEqual(
                resource_path("frontend", "index.html"),
                PROJECT_ROOT / "frontend" / "index.html",
            )


class DataDirectoryTests(unittest.TestCase):
    def test_absolute_override_is_created_and_used(self):
        directory = make_data_directory("override")
        with environment(**{DATA_DIRECTORY_VARIABLE: directory}):
            self.assertEqual(data_dir(), directory)
            self.assertTrue(directory.is_dir())

    def test_relative_override_is_rejected(self):
        with environment(**{DATA_DIRECTORY_VARIABLE: os.path.join(".tmp", "relative")}):
            with self.assertRaises(ValueError) as raised:
                data_dir()
        self.assertIn(DATA_DIRECTORY_VARIABLE, str(raised.exception))

    def test_default_lives_under_local_app_data(self):
        local_app_data = make_data_directory("local-app-data")
        local_app_data.mkdir(parents=True)
        with environment(
            **{DATA_DIRECTORY_VARIABLE: None, "LOCALAPPDATA": local_app_data}
        ):
            self.assertEqual(data_dir(), local_app_data / "recogniser")
            self.assertTrue((local_app_data / "recogniser").is_dir())

    def test_missing_local_app_data_is_reported(self):
        with environment(**{DATA_DIRECTORY_VARIABLE: None, "LOCALAPPDATA": None}):
            with self.assertRaises(RuntimeError) as raised:
                data_dir()
        self.assertIn("LOCALAPPDATA", str(raised.exception))


class CategoryContractTests(unittest.TestCase):
    def setUp(self):
        self.categories = Api().get_categories()

    def test_registry_satisfies_the_category_contract(self):
        self.assertEqual(diagnostics.category_problems(self.categories), [])
        self.assertEqual(
            diagnostics.upload_target(self.categories), ("numbers", "numbers-0")
        )

    def test_status_envelope_is_rejected(self):
        envelope = {
            "status": "ok",
            "prediction": 1,
            "confidence": 1.0,
            "message": "",
        }
        problems = diagnostics.category_problems(envelope)
        self.assertTrue(problems)
        self.assertIn("not a category list", problems[0])

    def test_empty_category_list_is_rejected(self):
        self.assertTrue(diagnostics.category_problems([]))

    def test_missing_category_fields_are_reported(self):
        problems = diagnostics.category_problems([{"id": "numbers"}])
        self.assertTrue(any("is missing" in problem for problem in problems))
        self.assertTrue(any("input mode list" in problem for problem in problems))
        self.assertTrue(any("model list" in problem for problem in problems))

    def test_nested_model_fields_are_validated(self):
        category = {
            "id": "numbers",
            "label": "Numbers",
            "description": "Digits.",
            "guidance": "One digit.",
            "frontend_view": "numbers",
            "input_modes": [
                {"id": "upload", "label": "Upload", "hint": "Pick one."}
            ],
            "models": [{"id": "numbers-0", "category_id": "numbers"}],
        }
        problems = diagnostics.category_problems([category])
        self.assertTrue(
            any("model 0 is missing" in problem for problem in problems)
        )

    def test_categories_without_upload_have_no_target(self):
        drawing_only = [
            {
                "id": "shapes",
                "input_modes": [
                    {"id": "drawing", "label": "Draw", "hint": "Draw one."}
                ],
                "models": [{"id": "shapes-0"}],
            }
        ]
        self.assertIsNone(diagnostics.upload_target(drawing_only))
        self.assertIsNone(diagnostics.upload_target({"status": "ok"}))


class RecognitionContractTests(unittest.TestCase):
    def envelope(self, status: str, **overrides: object) -> dict[str, object]:
        envelope: dict[str, object] = {
            "status": status,
            "prediction": 1,
            "confidence": 0.99,
            "message": "Predicted digit: 1.",
        }
        envelope.update(overrides)
        return envelope

    def test_ok_and_uncertain_pass(self):
        for status in ("ok", "uncertain"):
            self.assertEqual(
                diagnostics.recognition_problems(self.envelope(status)), [], status
            )

    def test_uncertain_without_a_prediction_passes(self):
        result = self.envelope("uncertain", prediction=None, confidence=None)
        self.assertEqual(diagnostics.recognition_problems(result), [])

    def test_error_statuses_fail(self):
        for status in ("error", "invalid_input"):
            problems = diagnostics.recognition_problems(self.envelope(status))
            self.assertTrue(problems, status)
            self.assertIn(repr(status), problems[0])

    def test_malformed_result_objects_fail(self):
        self.assertTrue(diagnostics.recognition_problems("ok"))
        self.assertTrue(diagnostics.recognition_problems({"status": "ok"}))
        self.assertTrue(
            diagnostics.recognition_problems(self.envelope("ok", message=None))
        )
        self.assertTrue(
            diagnostics.recognition_problems(self.envelope("ok", confidence="high"))
        )
        self.assertTrue(
            diagnostics.recognition_problems(self.envelope("ok", confidence=True))
        )


class FixtureTests(unittest.TestCase):
    def test_fixture_is_a_deterministic_png(self):
        first = diagnostics.sample_upload_data_url()
        self.assertEqual(first, diagnostics.sample_upload_data_url())
        self.assertTrue(first.startswith("data:image/png;base64,"))

        payload = base64.b64decode(first.split(",", 1)[1])
        with Image.open(io.BytesIO(payload)) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (diagnostics.FIXTURE_SIZE,) * 2)

    def test_fixture_passes_upload_preprocessing(self):
        prepared = numbers.prepare_upload(diagnostics.sample_upload_data_url())
        self.assertEqual(prepared.shape, (numbers.INPUT_SIZE, numbers.INPUT_SIZE))
        self.assertEqual(prepared.dtype.name, "float32")
        self.assertGreater(float(prepared.max()), 0.5)


class LoggingAndReportTests(unittest.TestCase):
    def test_logging_writes_the_file_and_adds_one_handler(self):
        directory = make_data_directory("logging")
        root = logging.getLogger()
        previous_level = root.level
        previous_handlers = list(root.handlers)
        self.addCleanup(root.setLevel, previous_level)
        self.addCleanup(setattr, root, "handlers", previous_handlers)

        with environment(**{DATA_DIRECTORY_VARIABLE: directory}):
            path = diagnostics.configure_logging()
            added = [h for h in root.handlers if h not in previous_handlers]
            for handler in added:
                self.addCleanup(handler.close)
            diagnostics.configure_logging()
            logging.getLogger("backend.test").warning("self-test log line")
            text = path.read_text(encoding="utf-8")

        self.assertEqual(path, directory / "logs" / diagnostics.LOG_FILENAME)
        self.assertEqual(len(added), 1)
        self.assertIn("self-test log line", text)

    def test_report_file_and_exit_code_follow_the_problems(self):
        directory = make_data_directory("report")
        with environment(**{DATA_DIRECTORY_VARIABLE: directory}):
            passed = {"passed": True, "problems": []}
            failed = {"passed": False, "problems": ["something broke"]}

            with mock.patch.object(diagnostics, "build_report", return_value=passed):
                self.assertEqual(diagnostics.run_self_test(), 0)
            with mock.patch.object(diagnostics, "build_report", return_value=failed):
                self.assertEqual(diagnostics.run_self_test(), 1)

            report_path = directory / "logs" / diagnostics.SELF_TEST_FILENAME
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertFalse(report["passed"])
            self.assertEqual(report["problems"], ["something broke"])
