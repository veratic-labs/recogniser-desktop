"""Frozen entry point for the recogniser desktop application.

PyInstaller analyses this module, so the bundle starts through exactly the same
``backend.main.main`` that ``python -m backend.main`` uses. It performs no
``os.chdir()``, which is why every resource path must resolve independently of
the working directory.
"""

import sys

sys.dont_write_bytecode = True

from backend.main import main

if __name__ == "__main__":
    raise SystemExit(main())
