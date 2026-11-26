# Building recogniser

This document describes how the Windows executable bundle and the Inno Setup
installer are produced. For installing a finished build, see
[INSTALL.md](INSTALL.md). For running from source, see the project
[README](../README.md).

All commands run in PowerShell from the project root, which is the directory
containing `README.md` and `packaging\`.

## Prerequisites

| Requirement | Why |
| --- | --- |
| Windows 10 or 11, x64 | The bundle is built for x64 only |
| Python 3.10 or newer | Interpreter used for the build |
| The project virtual environment at `venv\` with `requirements.txt` installed | `build.ps1` runs `venv\Scripts\python.exe` and never installs anything |
| PyInstaller 6.x installed in that same environment | Build tool only, so it is not listed in `requirements.txt`; `build.ps1` stops with a clear message if it is missing |
| Inno Setup 7 | Only needed for the installer step |

The environment directory in this project is `venv\`, created by the command
below. There is no `.venv\` directory, so `.\venv\Scripts\python.exe` is the
interpreter path used throughout this document, and it must be typed with that
name.

If the virtual environment does not exist yet:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m pip install "pyinstaller>=6.22,<7"
```

Inno Setup 7 is detected at `C:\Program Files\Inno Setup 7\ISCC.exe`, then on
`PATH`. Any other location is passed explicitly with `-IsccPath`.

## Build the executable bundle

```powershell
.\packaging\build.ps1
```

That single command:

1. Reads `packaging\version.txt` and checks the environment: the `venv\` interpreter
   exists, PyInstaller is importable, and `packaging\` does not shadow the installed
   `packaging` library that PyInstaller itself imports.
2. Runs the test suite (`python -m unittest discover -s tests -v`) and stops if any
   test fails.
3. Runs `packaging\prepare_build.py`, which writes `build\version_info.txt` from
   `packaging\version.txt` and regenerates `packaging\assets\recogniser.ico` from
   `images\icon.png` only when the icon source is newer.
4. Builds `dist\recogniser\` with PyInstaller and `packaging\recogniser.spec`.
5. Checks that the expected executable and resources are present.
6. Runs the frozen `--self-test` twice, once with the project root and once with
   `.tmp\selftest-cwd` as the working directory.
7. Writes `build\bundle-manifest.json`, the reviewed-bundle record, and
   immediately re-checks the bundle against it.

Add `-Clean` to discard PyInstaller's analysis cache:

```powershell
.\packaging\build.ps1 -Clean
```

The script fails on the first problem instead of producing a questionable bundle,
and exits non-zero when any step fails.

## Build outputs

| Path | Contents |
| --- | --- |
| `dist\recogniser\recogniser.exe` | The application launcher |
| `dist\recogniser\_internal\` | Python runtime, frontend, models, and native libraries |
| `build\version_info.txt` | Generated Windows version resource |
| `build\bundle-manifest.json` | Path, size, and SHA-256 of every bundle file |
| `build\pyinstaller\` | PyInstaller's intermediate work directory |
| `.tmp\build-tests.log` | Test output from the last build |
| `.tmp\prepare-build.log` | Version and icon preparation output |
| `.tmp\pyinstaller.log` | PyInstaller output |
| `.tmp\iscc.log` | Inno Setup compiler output |
| `.tmp\selftest-cwd\`, `.tmp\selftest-cwd-data\` | Working directory and data directory of the second self-test |

`build\` and `dist\` are ignored by Git. A bundle is an output, not a deliverable
to commit.

## Run and verify the bundle

Launch it directly:

```powershell
.\dist\recogniser\recogniser.exe
```

The self-test can be run on its own. The executable uses the Windows GUI
subsystem, so use `Start-Process -Wait` rather than the call operator when you
need the exit code, and point the data directory inside the project so nothing is
written to your profile:

```powershell
$env:RECOGNISER_DATA_DIR = "$PWD\.tmp\manual-selftest"
$process = Start-Process -FilePath .\dist\recogniser\recogniser.exe `
    -ArgumentList '--self-test' -WindowStyle Hidden -Wait -PassThru
$process.ExitCode
Get-Content "$env:RECOGNISER_DATA_DIR\logs\self-test.json"
```

Exit code `0` with `"passed": true` means the frozen application found its
frontend, imported the adapter, loaded the ONNX model, resolved the WebView2
renderer, and completed one recognition call. The `problems` list names anything
that failed.

The same self-test runs from a source checkout, which is useful when a bundle
fails and you need to know whether the model or the bundle is at fault:

```powershell
$env:RECOGNISER_DATA_DIR = "$PWD\.tmp\source-selftest"
.\venv\Scripts\python.exe -m backend.main --self-test
```

Remove `RECOGNISER_DATA_DIR` afterwards (`Remove-Item Env:RECOGNISER_DATA_DIR`) so
later runs use `%LOCALAPPDATA%\recogniser` again.

## Build the installer

```powershell
.\packaging\build.ps1 -Installer
```

`-Installer` never builds the bundle. It compares `dist\recogniser` against
`build\bundle-manifest.json` and stops before compiling if any file was added,
removed, or modified, naming the differences. This guarantees that the installer
wraps the bundle that was built and verified earlier. If the check fails, re-run
`.\packaging\build.ps1`, verify that bundle, and then package it.

It also refuses to package when the bundled executable's numeric version does not
match `packaging\version.txt`.

Output:

| Path | Contents |
| --- | --- |
| `dist\installer\recogniser-<version>-setup.exe` | The installer |
| `dist\installer\recogniser-<version>-setup.exe.sha256` | SHA-256 of that installer |

Pass `-IsccPath 'D:\Tools\Inno Setup 7\ISCC.exe'` when Inno Setup 7 is installed
elsewhere.

## Change the version

1. Edit `packaging\version.txt` to a three-part version such as `1.1.0`.
2. Re-run `.\packaging\build.ps1`.
3. Re-run `.\packaging\build.ps1 -Installer`.

The version flows into the executable's version resource, the installer's
metadata, the uninstall entry name, and the installer filename. The installer
keeps the same `AppId`, so a newer installer upgrades an existing installation
instead of adding a second copy.

## Change the application icon

1. Replace `images\icon.png` with a square PNG of at least 256 × 256 pixels.
2. Run `.\venv\Scripts\python.exe packaging\prepare_build.py` (or any build),
   which rewrites `packaging\assets\recogniser.ico` with 16, 24, 32, 48, 64, 128,
   and 256 pixel entries.
3. Rebuild the bundle and then the installer. Both take the icon from
   `packaging\assets\recogniser.ico`.

## Project-local temporary files

`build.ps1` sets `TEMP`, `TMP`, `PYTHONPYCACHEPREFIX`, and
`PYINSTALLER_CONFIG_DIR` to directories under `.tmp\` before it runs anything, so
build caches and logs stay inside the project. `.tmp\` is ignored by Git and can
be deleted at any time.

## What the bundle contains

`packaging\recogniser.spec` builds a one-directory bundle (`dist\recogniser`) and
declares:

- `frontend/` and `models/` as data, so HTML, CSS, JavaScript, and both model
  files stay plain files on disk instead of being embedded in the executable.
  The two model files are listed individually so their directory's `__pycache__`
  is not copied.
- `backend.adapters.numbers` in `hiddenimports`. `backend\api.py` loads the
  adapter with `importlib.import_module(model.adapter)`, which PyInstaller cannot
  detect. **A new adapter module must be added here**, or the frozen application
  cannot load that model.
- `onnxruntime` and `webview.platforms.winforms` / `webview.platforms.edgechromium`
  in `hiddenimports`, because those imports happen behind runtime selection.
- `tkinter`, `pytest`, `_pytest`, and `tests` as exclusions.
- `console=False`, so the application has no console window and reports problems
  through its own window and its log file.

Add a model or category as described in the README, then rebuild. The spec lists
model files explicitly, so a new model's `.py` and `.onnx` files must be added to
`datas`, and a new adapter module also needs its `hiddenimports` entry. Otherwise
the frozen application cannot see the new model even though a source checkout
can.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `The virtual environment interpreter is missing` | Create `venv\` as shown under Prerequisites |
| `PyInstaller is not available in …` | Install it into the environment: `.\venv\Scripts\python.exe -m pip install "pyinstaller>=6.22,<7"` |
| `The packaging\ directory shadows the installed packaging library` | Remove any `__init__.py` from `packaging\` so PyInstaller imports its own dependency |
| The build stops because tests failed | Fix the tests first; the build refuses to package a failing tree |
| `The reviewed-bundle manifest is missing` | Run `.\packaging\build.ps1` before `-Installer` |
| `dist\recogniser differs from the reviewed bundle` | Something changed since the reviewed build. Rebuild and re-verify the bundle |
| `ISCC.exe was not found` | Install Inno Setup 7, add it to `PATH`, or pass `-IsccPath` |
| The application reports that WebView2 is unavailable | Install the Microsoft Edge WebView2 runtime; the application refuses the legacy MSHTML renderer |
| The bundle reports a model error while the source build works | Check `hiddenimports` and the self-test report's `problems`; a missing adapter module or model file is the usual cause |
| A rebuilt bundle still shows old behaviour | Delete `dist\recogniser` and rebuild with `-Clean` |
| SmartScreen warns on first launch of the installer | The installer is unsigned; see the code-signing limitation in `PACKAGING_PLAN.md` |

The application writes logs, including the self-test report, to
`%LOCALAPPDATA%\recogniser\logs\`, or under `RECOGNISER_DATA_DIR` when that
variable is set.

