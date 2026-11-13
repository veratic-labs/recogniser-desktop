"""Desktop entry point for the recogniser application.

Launch from the project root with:

    python -m backend.main
"""

from __future__ import annotations

from pathlib import Path

import webview

from .api import Api

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_INDEX = PROJECT_ROOT / "frontend" / "index.html"
WEBVIEW_STORAGE = PROJECT_ROOT / ".webview-data"


def create_window() -> webview.Window:
    """Create the application window, resolving frontend paths from source."""
    if not FRONTEND_INDEX.is_file():
        raise FileNotFoundError(f"Frontend entry point not found: {FRONTEND_INDEX}")

    window = webview.create_window(
        "recogniser",
        url=str(FRONTEND_INDEX),
        js_api=Api(),
        width=1000,
        height=760,
        min_size=(720, 560),
        background_color="#FAFAF9",
    )
    if window is None:
        raise RuntimeError("The application window could not be created.")
    return window


def main() -> None:
    """Start the pywebview window and its GUI event loop."""
    create_window()
    webview.start(
        private_mode=True,
        storage_path=str(WEBVIEW_STORAGE),
    )


if __name__ == "__main__":
    main()
