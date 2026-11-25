"""Filesystem locations for bundled resources and writable user data.

Read-only resources resolve from the frozen bundle's ``sys._MEIPASS`` directory
and from the project root in a source checkout, so neither depends on the
process working directory.

Writable data never lives in the install directory. It defaults to
``%LOCALAPPDATA%\\recogniser`` and can be redirected with
``RECOGNISER_DATA_DIR``, which must be an absolute path so that a stray relative
value cannot scatter user data across whatever directory the process happens to
start in.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path, PurePosixPath

DATA_DIRECTORY_VARIABLE = "RECOGNISER_DATA_DIR"
APPLICATION_DIRECTORY = "recogniser"


def resource_root() -> Path:
    """Return the root of the read-only bundled resources."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> Path:
    """Return the path of a bundled resource below :func:`resource_root`."""
    return resource_root().joinpath(*parts)


def model_resource_path(resource_dir: str, *parts: str) -> Path:
    """Resolve a registered model directory, stored relative to the project root.

    Registration keeps ``resource_dir`` relative and POSIX-style so display-name
    changes never rename a directory; this helper turns it into an absolute path
    in both source and frozen runs.
    """
    return resource_path(*PurePosixPath(resource_dir).parts, *parts)


def data_dir() -> Path:
    """Return the writable per-user data directory, creating it if needed.

    Raises:
        ValueError: the ``RECOGNISER_DATA_DIR`` override is not absolute.
        RuntimeError: no override is set and ``LOCALAPPDATA`` is missing.
    """
    override = os.environ.get(DATA_DIRECTORY_VARIABLE)
    if override:
        base = Path(override)
        if not base.is_absolute():
            raise ValueError(
                f"{DATA_DIRECTORY_VARIABLE} must be an absolute path, "
                f"but it is {override!r}."
            )
    else:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError(
                "LOCALAPPDATA is not set, so the application data directory "
                "cannot be located. Set it, or set "
                f"{DATA_DIRECTORY_VARIABLE} to an absolute path."
            )
        base = Path(local_app_data) / APPLICATION_DIRECTORY

    base.mkdir(parents=True, exist_ok=True)
    return base
