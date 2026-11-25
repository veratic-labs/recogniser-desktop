"""Runtime diagnostics for source runs and the packaged application.

A packaged build uses ``console=False``, so there is no usable stdout or stderr.
This module supplies what replaces them:

- :func:`configure_logging` sends the records ``backend.api`` and the adapters
  already emit to a file under the writable data directory.
- :func:`run_self_test` checks the resources, the GUI layer, the category list,
  and one recognition call without opening a window, and reports through a JSON
  file plus the process exit code.

``webview`` is imported lazily so this module stays importable without loading
pythonnet and .NET.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .api import Api
from .model_registry import all_models
from .paths import data_dir, model_resource_path, resource_path, resource_root

LOGGER = logging.getLogger(__name__)

LOGS_DIRECTORY = "logs"
LOG_FILENAME = "recogniser.log"
SELF_TEST_FILENAME = "self-test.json"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

# The startup guard refuses to run with any other renderer.
SUPPORTED_RENDERER = "edgechromium"

UPLOAD_MODE_ID = "upload"

# Api.get_categories() returns a category list (PLAN.md section 7.4), never a
# recognition status envelope.
CATEGORY_KEYS = (
    "id",
    "label",
    "description",
    "guidance",
    "frontend_view",
    "input_modes",
    "models",
)
CATEGORY_TEXT_KEYS = ("id", "label", "description", "guidance", "frontend_view")
INPUT_MODE_KEYS = ("id", "label", "hint")
MODEL_KEYS = (
    "id",
    "category_id",
    "series",
    "display_name",
    "description",
    "instructions",
    "input_label",
)

# A recognition result is the shared envelope. A correct pipeline may be unsure
# about a synthetic fixture, so `uncertain` is a pass; only a broken pipeline
# produces `error`, `invalid_input`, an exception, or a malformed envelope.
ACCEPTED_RECOGNITION_STATUSES = frozenset({"ok", "uncertain"})
RESULT_KEYS = ("status", "prediction", "confidence", "message")

# The fixture is drawn in memory so the self-test needs no external image.
FIXTURE_SIZE = 64


def logs_dir() -> Path:
    """Return the writable log directory, creating it if needed."""
    directory = data_dir() / LOGS_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def log_file() -> Path:
    """Return the path of the application log file."""
    return logs_dir() / LOG_FILENAME


def configure_logging(level: int = logging.INFO) -> Path:
    """Send log records to the application log file and return its path.

    Every backend module logs through its own module logger, so one handler on
    the root logger is enough. Calling this twice does not add it twice.
    """
    path = log_file()
    root = logging.getLogger()
    attached = {
        getattr(handler, "baseFilename", None) for handler in root.handlers
    }
    if str(path) not in attached:
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root.addHandler(handler)
        if root.level > level or root.level == logging.NOTSET:
            root.setLevel(level)
    return path


def detect_renderer() -> str:
    """Return the pywebview renderer that ``webview.start()`` would select.

    ``initialize()`` returns the platform module and is safe to call before
    ``create_window()``; ``setup_app()`` inside it is guarded by a flag.
    """
    from webview.guilib import initialize

    return str(getattr(initialize(), "renderer", "unknown"))


def category_problems(payload: Any) -> list[str]:
    """Return the contract violations in an ``Api.get_categories()`` result.

    The method returns a list of category objects. A status envelope is itself a
    violation, because ``get_categories()`` never reports through one.
    """
    if not isinstance(payload, list):
        return [
            "Api.get_categories() returned "
            f"{type(payload).__name__}, not a category list."
        ]
    if not payload:
        return ["Api.get_categories() returned an empty category list."]

    problems: list[str] = []
    for index, category in enumerate(payload):
        if not isinstance(category, dict):
            problems.append(
                f"Category {index} is {type(category).__name__}, not an object."
            )
            continue

        category_id = category.get("id")
        if isinstance(category_id, str) and category_id:
            label = f"Category {category_id!r}"
        else:
            label = f"Category {index}"

        missing = [key for key in CATEGORY_KEYS if key not in category]
        if missing:
            problems.append(f"{label} is missing {', '.join(missing)}.")

        for key in CATEGORY_TEXT_KEYS:
            if key in category and not isinstance(category[key], str):
                problems.append(f"{label} field {key!r} is not text.")

        problems.extend(_input_mode_problems(label, category.get("input_modes")))
        problems.extend(_model_problems(label, category.get("models")))

    return problems


def _input_mode_problems(label: str, modes: Any) -> list[str]:
    """Return the contract violations in one category's input modes."""
    if not isinstance(modes, list):
        return [f"{label} has no input mode list."]

    problems: list[str] = []
    for index, mode in enumerate(modes):
        if not isinstance(mode, dict):
            problems.append(f"{label} input mode {index} is not an object.")
            continue
        missing = [key for key in INPUT_MODE_KEYS if key not in mode]
        if missing:
            problems.append(
                f"{label} input mode {index} is missing {', '.join(missing)}."
            )
    return problems


def _model_problems(label: str, models: Any) -> list[str]:
    """Return the contract violations in one category's nested models."""
    if not isinstance(models, list):
        return [f"{label} has no model list."]

    problems: list[str] = []
    for index, model in enumerate(models):
        if not isinstance(model, dict):
            problems.append(f"{label} model {index} is not an object.")
            continue
        missing = [key for key in MODEL_KEYS if key not in model]
        if missing:
            problems.append(
                f"{label} model {index} is missing {', '.join(missing)}."
            )
        model_id = model.get("id")
        if not isinstance(model_id, str) or not model_id:
            problems.append(f"{label} model {index} has no usable id.")
    return problems


def upload_target(categories: Any) -> tuple[str, str] | None:
    """Return the category and model IDs the self-test recognition call uses.

    The first category whose ``input_modes`` include ``upload`` wins, together
    with its first registered model. ``None`` means the registry offers no upload
    path at all, which is a failure in its own right.
    """
    if not isinstance(categories, list):
        return None

    for category in categories:
        if not isinstance(category, dict):
            continue
        category_id = category.get("id")
        modes = category.get("input_modes")
        models = category.get("models")
        if not isinstance(category_id, str) or not category_id:
            continue
        if not isinstance(modes, list) or not isinstance(models, list):
            continue
        if not any(
            isinstance(mode, dict) and mode.get("id") == UPLOAD_MODE_ID
            for mode in modes
        ):
            continue
        for model in models:
            model_id = model.get("id") if isinstance(model, dict) else None
            if isinstance(model_id, str) and model_id:
                return category_id, model_id

    return None


def recognition_problems(result: Any) -> list[str]:
    """Return the contract violations in one recognition result.

    ``ok`` and ``uncertain`` both pass. ``error``, ``invalid_input``, any other
    status, and a malformed envelope fail the self-test.
    """
    if not isinstance(result, dict):
        return [
            "Recognition returned "
            f"{type(result).__name__}, not a result object."
        ]

    problems: list[str] = []
    missing = [key for key in RESULT_KEYS if key not in result]
    if missing:
        problems.append(f"The recognition result is missing {', '.join(missing)}.")

    status = result.get("status")
    if status not in ACCEPTED_RECOGNITION_STATUSES:
        problems.append(
            f"Recognition returned status {status!r}: {result.get('message')!r}"
        )

    if "message" in result and not isinstance(result["message"], str):
        problems.append("The recognition message is not text.")

    confidence = result.get("confidence")
    if confidence is not None and (
        isinstance(confidence, bool) or not isinstance(confidence, (int, float))
    ):
        problems.append("The recognition confidence is not a number.")

    return problems


def sample_upload_data_url() -> str:
    """Return a deterministic PNG data URL that passes upload preprocessing.

    The fixture is drawn in memory with integer coordinates on a plain
    ``L``-mode canvas, so it is byte-identical on every run: a white 64 x 64
    canvas carrying a black "1" (stem, flag, and base). Only the fixture is
    deterministic; the model's answer is never asserted beyond ``ok`` or
    ``uncertain``.
    """
    image = Image.new("L", (FIXTURE_SIZE, FIXTURE_SIZE), color=255)
    draw = ImageDraw.Draw(image)
    draw.rectangle((28, 8, 36, 52), fill=0)
    draw.polygon(((28, 20), (16, 32), (22, 34), (30, 30)), fill=0)
    draw.rectangle((16, 52, 48, 56), fill=0)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode(
        "ascii"
    )


def build_report() -> dict[str, Any]:
    """Collect the self-test evidence together with the problems it found."""
    problems: list[str] = []
    index = resource_path("frontend", "index.html")
    report: dict[str, Any] = {
        "frozen": bool(getattr(sys, "frozen", False)),
        "executable": sys.executable,
        "resource_root": str(resource_root()),
        "data_dir": str(data_dir()),
        "frontend_index": {"path": str(index), "present": index.is_file()},
        "model_directories": {},
        "renderer": None,
        "supported_renderer": SUPPORTED_RENDERER,
        "categories": None,
        "recognition": None,
        "problems": problems,
        "passed": False,
    }

    if not index.is_file():
        problems.append(f"The frontend entry point is missing: {index}")

    for model in all_models():
        directory = model_resource_path(model.resource_dir)
        if directory.is_dir():
            files = sorted(
                entry.name for entry in directory.iterdir() if entry.is_file()
            )
        else:
            files = []
        report["model_directories"][model.id] = {
            "path": str(directory),
            "files": files,
        }
        if not files:
            problems.append(f"The model directory is missing or empty: {directory}")

    try:
        renderer = detect_renderer()
    except Exception as exc:
        LOGGER.exception("The pywebview GUI layer could not be initialised.")
        problems.append(f"The pywebview GUI layer could not be initialised: {exc}")
    else:
        report["renderer"] = renderer
        if renderer != SUPPORTED_RENDERER:
            problems.append(
                f"pywebview selected the {renderer!r} renderer, but "
                f"{SUPPORTED_RENDERER!r} is required."
            )

    client = Api()
    categories: Any = None
    try:
        categories = client.get_categories()
    except Exception as exc:
        LOGGER.exception("Api.get_categories() raised an exception.")
        problems.append(f"Api.get_categories() raised {type(exc).__name__}: {exc}")
    else:
        report["categories"] = categories
        problems.extend(category_problems(categories))

    target = upload_target(categories)
    if target is None:
        problems.append(
            "No registered model accepts image upload, so recognition was not "
            "checked."
        )
    else:
        category_id, model_id = target
        report["recognition"] = {
            "category_id": category_id,
            "model_id": model_id,
            "result": None,
        }
        try:
            result = client.recognise_category_upload(
                category_id, model_id, sample_upload_data_url()
            )
        except Exception as exc:
            LOGGER.exception("The self-test recognition call raised an exception.")
            problems.append(f"Recognition raised {type(exc).__name__}: {exc}")
        else:
            report["recognition"]["result"] = result
            problems.extend(recognition_problems(result))

    report["passed"] = not problems
    return report


def run_self_test() -> int:
    """Run the self-test, write its JSON report, and return an exit code.

    The report always lands beside the log file. Nothing is printed when
    ``sys.stdout`` is ``None``, which is the case for a ``console=False`` build.
    """
    report = build_report()
    path = logs_dir() / SELF_TEST_FILENAME
    try:
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    except OSError as exc:
        LOGGER.exception("The self-test report could not be written.")
        report["problems"].append(f"The self-test report could not be written: {exc}")
        report["passed"] = False

    passed = bool(report["passed"])
    LOGGER.info("Self-test %s; report: %s", "passed" if passed else "failed", path)
    for problem in report["problems"]:
        LOGGER.error("Self-test problem: %s", problem)

    if sys.stdout is not None:
        print(f"Self-test {'passed' if passed else 'failed'}: {path}")
        for problem in report["problems"]:
            print(f"  - {problem}")

    return 0 if passed else 1

