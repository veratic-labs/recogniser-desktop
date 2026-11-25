"""Desktop entry point for the recogniser application.

Launch from a source checkout with:

    python -m backend.main

A packaged build uses the same entry point; append ``--self-test`` to check a
build non-interactively (it writes a JSON report and returns an exit code).
"""

from __future__ import annotations

import ctypes
import logging
import sys
from typing import Sequence

import webview

from .api import Api
from .diagnostics import (
    SUPPORTED_RENDERER,
    configure_logging,
    detect_renderer,
    run_self_test,
)
from .paths import data_dir, resource_path, resource_root

LOGGER = logging.getLogger(__name__)

SELF_TEST_FLAG = "--self-test"

WINDOW_TITLE = "recogniser"
WINDOW_SIZE = (1000, 760)
WINDOW_MIN_SIZE = (720, 560)
BACKGROUND_COLOR = "#FAFAF9"
WEBVIEW_STORAGE_DIRECTORY = "webview-data"

WEBVIEW2_DOWNLOAD_URL = "https://developer.microsoft.com/microsoft-edge/webview2/"
STARTUP_FAILURE_TITLE = "recogniser cannot start"

MB_ICONERROR = 0x00000010
MB_OK = 0x00000000


def renderer_failure_message(renderer: str) -> str:
    """Return the message shown when pywebview cannot use EdgeChromium."""
    return (
        "recogniser needs the Microsoft Edge WebView2 Runtime, which provides "
        f"its {SUPPORTED_RENDERER!r} renderer. pywebview selected {renderer!r} "
        "instead, so the application will not start.\n\n"
        f"Install the WebView2 Runtime from {WEBVIEW2_DOWNLOAD_URL} and start "
        "recogniser again."
    )


def show_message(title: str, message: str) -> None:
    """Show a blocking message box, for failures a windowed build cannot print."""
    ctypes.windll.user32.MessageBoxW(None, message, title, MB_OK | MB_ICONERROR)


def create_window() -> webview.Window:
    """Create the application window, resolving frontend paths from resources."""
    index = resource_path("frontend", "index.html")
    if not index.is_file():
        raise FileNotFoundError(f"Frontend entry point not found: {index}")

    window = webview.create_window(
        WINDOW_TITLE,
        url=str(index),
        js_api=Api(),
        width=WINDOW_SIZE[0],
        height=WINDOW_SIZE[1],
        min_size=WINDOW_MIN_SIZE,
        background_color=BACKGROUND_COLOR,
    )
    if window is None:
        raise RuntimeError("The application window could not be created.")
    return window


def _startup_failure(message: str) -> int:
    """Log a startup failure, show it, and return the failure exit code."""
    LOGGER.error("%s", message)
    try:
        show_message(STARTUP_FAILURE_TITLE, message)
    except Exception:
        LOGGER.exception("The failure message could not be displayed.")
    return 1


def start_gui() -> int:
    """Check the GUI prerequisites, then run the window and its event loop."""
    try:
        renderer = detect_renderer()
    except Exception as exc:
        LOGGER.exception("The pywebview GUI layer could not be initialised.")
        return _startup_failure(
            "The Windows desktop layer for recogniser could not be initialised: "
            f"{exc}"
        )

    LOGGER.info("pywebview selected the %r renderer.", renderer)
    if renderer != SUPPORTED_RENDERER:
        return _startup_failure(renderer_failure_message(renderer))

    try:
        create_window()
    except Exception as exc:
        LOGGER.exception("The application window could not be created.")
        return _startup_failure(str(exc))

    storage = data_dir() / WEBVIEW_STORAGE_DIRECTORY
    storage.mkdir(parents=True, exist_ok=True)
    webview.start(private_mode=True, storage_path=str(storage))
    LOGGER.info("The application window closed.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Start the application, or run the self-test, and return an exit code."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    self_test = SELF_TEST_FLAG in arguments

    try:
        configure_logging()
    except Exception as exc:
        message = f"The recogniser data directory could not be created: {exc}"
        if self_test and sys.stderr is not None:
            print(message, file=sys.stderr)
        elif not self_test:
            try:
                show_message(STARTUP_FAILURE_TITLE, message)
            except Exception:
                pass
        return 1

    LOGGER.info(
        "Starting recogniser from %s (data: %s).", resource_root(), data_dir()
    )
    if self_test:
        LOGGER.info("Self-test requested.")
        return run_self_test()

    return start_gui()


if __name__ == "__main__":
    raise SystemExit(main())
