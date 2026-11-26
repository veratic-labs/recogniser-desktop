# recogniser — Windows Packaging Plan

Status: **Stages 1–6 accepted and committed.** The onedir bundle and the per-user
Inno Setup installer are built and verified on this machine, and the user accepted
the installed application after installing it, launching it from the Start menu,
recognising an uploaded image and a drawing, and checking the icons. This
revision reconciles the plan with what was actually built and records the
commits made on explicit request: `2f9c70f`, `1c88f65`, `baa1c51`, and the
documentation commit that carries this revision. Nothing has been pushed.

Date: 24 November 2026; Stage 3 corrections 25 November 2026; reconciled with the
accepted implementation 26 November 2026. Source requirements: `PLAN.md`
(requirements draft v0.8) and `AGENTS.md` (workflow policy).

Packaging is an authorised separate track. `PLAN.md` section 9 lists installer
packaging as outside the first release; `PLAN.md` is deliberately not rewritten
by this work.

## 1. Goal and boundaries

Package the current `recogniser` application as a Windows x64 desktop
application using:

- **PyInstaller onedir** for the application bundle.
- **Inno Setup** for a conventional Windows installer.

The packaged application must preserve the existing behaviour:

- `python -m backend.main` remains the source entry point.
- The frozen executable starts the same pywebview window and binds the same
  `backend.api.Api` object.
- The frontend is loaded from bundled files, never from the working directory
  or a development server.
- `model_0_numbers.py` and `model_0_numbers.onnx` are shipped unchanged as real
  files in `models/0-numbers/` and loaded through the existing dynamic
  `importlib.util` mechanism.
- Upload and drawing recognition work end to end.
- Resource resolution stays independent of the process working directory.
- No new runtime service, local HTTP server, database, or updater is added.

Out of scope for this packaging track: model, preprocessing, threshold, or UI
behaviour changes; onefile/portable builds; macOS or Linux; native ARM64 builds;
code signing; publishing, releases, or pushes; bundling WebView2 or the VC++
redistributable.

Work proceeds one stage at a time (section 6). Each stage ends with a report and
a full stop until the user approves the next stage.

## 2. Environment

### 2.1 Current verified state (re-checked 26 November 2026)

| Item | Verified value |
| --- | --- |
| Virtual-environment interpreter | `C:\Users\Simon\veratic\recogniser\venv\Scripts\python.exe` |
| Virtual-environment directory | `venv\`. No `.venv\` directory exists, so every document uses `.\venv\Scripts\python.exe` for that interpreter |
| Python | `3.10.3`, 64-bit, AMD64 |
| PyInstaller | `6.22.3` |
| pyinstaller-hooks-contrib | `2026.10` |
| Inno Setup | `7.1.1`, installed in `C:\Program Files\Inno Setup 7` |
| Inno Setup compiler | `C:\Program Files\Inno Setup 7\ISCC.exe` |
| `ISCC.exe` on `PATH` | No (`Get-Command ISCC.exe` finds nothing) |
| `pywebview` | `6.2.1` |
| `pythonnet` | `3.1.0` |
| `clr_loader` | `0.3.1` |
| `onnxruntime` | `1.23.2` |
| `numpy` | `2.2.6` |
| `Pillow` | `12.3.0` |
| Host OS | Windows 11, `10.0.26200.9974` (`cmd /c ver`), x64 |
| .NET Framework | `Release=0x82405` (533509) under `HKLM\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full` |
| WebView2 Runtime | `pv=158.0.4370.33` under `HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}` |
| Per-user WebView2 record | Absent (`HKCU\Software\Microsoft\EdgeUpdate\Clients\...` not found) |

How these were checked:

```powershell
.\venv\Scripts\python.exe -m PyInstaller --version          # 6.22.3
.\venv\Scripts\python.exe -c "import sys; print(sys.executable, sys.version)"
.\venv\Scripts\python.exe -m pip list --format=freeze
& 'C:\Program Files\Inno Setup 7\ISCC.exe'                  # banner: Inno Setup 7 Command-Line Compiler
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"   # DisplayVersion 7.1.1
```

`ISCC.exe` carries no usable version resource (`FileVersion 0.0.0.0`), so its
banner text and the uninstall registry entry `Inno Setup 7.1.1` are the
authoritative version evidence.

Re-checked read-only on 26 November 2026 for this reconciliation:
`.\venv\Scripts\python.exe -m PyInstaller --version` → `6.22.3`; the virtual
environment reports `3.10.3` (MSC v.1929, 64-bit); `reg query` reports
`Inno Setup 7.1.1`; `C:\Program Files\Inno Setup 7\ISCC.exe` exists (2136992
bytes). Every value in the table above is unchanged.

`requirements.txt` lists only the runtime dependencies (`pywebview`, `numpy`,
`onnxruntime`, `Pillow`); `pythonnet` and `clr_loader` arrive with `pywebview`.
PyInstaller and `pyinstaller-hooks-contrib` are build tooling installed into the
existing virtual environment and are deliberately not added to
`requirements.txt`, because the application does not import them. A fresh clone
therefore needs both installed before a build; `docs/BUILDING.md` states this.

### 2.2 Superseded Stage 1 snapshot

The Stage 1 report stated that PyInstaller was absent from `venv` and that
`ISCC.exe` could not be found, and recorded WebView2 as `157.0.4341.60`. Those
statements described the environment before both tools were installed and are
now obsolete. All "install the build tool" steps from the earlier draft are
removed. WebView2 was subsequently updated by Windows to the version above.

### 2.3 Tool-availability checks (no installation)

Every build stage starts with these read-only checks and stops if one fails:

```powershell
.\venv\Scripts\python.exe -m PyInstaller --version        # expect 6.x
& 'C:\Program Files\Inno Setup 7\ISCC.exe'                # expect "Inno Setup 7 Command-Line Compiler"
```

No dependency is installed, upgraded, downgraded, or downloaded by this plan.
The verified installed versions are used as they are. If a check fails, the
exact command and the missing requirement are reported and the stage stops.

### 2.4 Repository state

| Item | Verified value (26 November 2026) |
| --- | --- |
| Branch | `main` |
| HEAD | `1c88f65 build: fix packaging checks and include dynamically loaded adapter` |
| Earlier packaging commit | `2f9c70f build: add Windows packaging configuration and frozen-safe runtime paths` |
| Committed packaging work | `.gitignore` (`build/`, `dist/`), `PACKAGING_PLAN.md`, `images/icon.png`, `backend/paths.py`, `backend/diagnostics.py`, the `backend/main.py` and `backend/adapters/numbers.py` changes, `tests/test_paths_and_diagnostics.py`, and `packaging/` (`launcher.py`, `recogniser.spec`, `prepare_build.py`, `build.ps1`, `version.txt`, `assets/recogniser.ico`) |
| Uncommitted at the start of Stage 6 | Modified `packaging/build.ps1` (numeric version comparison and post-compile manifest re-check), untracked `packaging/recogniser.iss`, and a working-tree `PACKAGING_PLAN.md` that was an **older Stage 1 revision**, superseded by the committed copy |
| Uncommitted before the Stage 5–6 commits | Modified `packaging/build.ps1`, `PACKAGING_PLAN.md` and `README.md`; untracked `packaging/recogniser.iss` and `docs/` |
| `build/` and `dist/` | Present and ignored: `build\bundle-manifest.json` (239 files, created `2026-11-25T14:24:01Z`), `build\pyinstaller\`, `build\version_info.txt`, `dist\recogniser\` (239 files, 97.0 MB), `dist\installer\recogniser-1.0.0-setup.exe` (28.1 MB) with its `.sha256` |
| Backend tests | `Ran 36 tests in 0.043s — OK` (26 November 2026) |
| `models/0-numbers/__pycache__/model_0_numbers.cpython-310.pyc` | Present in the working tree, already ignored by `*.py[cod]`, and not in the bundle (no `__pycache__` anywhere under `_internal\models\`) |

The uncommitted plan revision was preserved byte-for-byte at
`.tmp\stage6\PACKAGING_PLAN.worktree.md` before this document was reconciled, and
the committed revision at `.tmp\stage6\PACKAGING_PLAN.HEAD.md`. Comparing the two
showed the working-tree copy contained nothing that the committed copy lacks: it
predates the Stage 3 corrections, the bundle/installer contract, and the
diagnostics design. Reconciliation therefore starts from the committed revision
and adds what Stages 4–6 actually produced.

## 3. Required resource inventory

Files that must reach the bundle as real files:

| Source | Bundle destination | Purpose |
| --- | --- | --- |
| `frontend/index.html` | `frontend/index.html` | Window entry point loaded by `file://` URL |
| `frontend/css/themes.css`, `frontend/css/style.css` | `frontend/css/` | Relative stylesheet references |
| `frontend/js/bridge.js`, `main.js`, `settings.js` | `frontend/js/` | Relative script references |
| `frontend/categories/numbers.js` | `frontend/categories/` | Category view |
| `models/0-numbers/model_0_numbers.py` | `models/0-numbers/` | Inference script, executed by path |
| `models/0-numbers/model_0_numbers.onnx` | `models/0-numbers/` | Weights, opened via `Path(__file__).parent` |
| `images/icon.png` | Not bundled as data | Authorised icon source; converted to `packaging/assets/recogniser.ico` |

Runtime files expected to come from the installed packages' own PyInstaller
hooks (see section 4.6), not from hand-maintained lists:

| Package | Expected bundle content |
| --- | --- |
| `webview` | `webview/lib` (`Microsoft.Web.WebView2.Core.dll`, `Microsoft.Web.WebView2.WinForms.dll`, `runtimes/win-x64/native/WebView2Loader.dll`) and `webview/js/*.js` |
| `pythonnet` | `Python.Runtime.dll` beside the `clr` extension |
| `clr_loader` | `clr_loader/ffi/dlls/amd64/ClrLoader.dll` |
| `onnxruntime` | `onnxruntime/capi/` with `onnxruntime.dll`, `onnxruntime_providers_shared.dll`, `onnxruntime_pybind11_state.pyd` |
| `Pillow` | Image plugins via PyInstaller's `hook-PIL.Image.py` |

Every row in the second table was confirmed in the accepted bundle, so the
expectations are now observations. Verified on 26 November 2026 against
`dist\recogniser` (239 files, 97.0 MB):

| Path under `dist\recogniser\_internal` | Result |
| --- | --- |
| `frontend\index.html`, `frontend\js\bridge.js` | present |
| `models\0-numbers\model_0_numbers.py`, `model_0_numbers.onnx` | present, side by side, no `__pycache__` anywhere under `models\` |
| `webview\lib`, `webview\js` | present |
| `pythonnet\runtime\Python.Runtime.dll` | present |
| `clr_loader\ffi\dlls\amd64` | present |
| `onnxruntime\capi\onnxruntime.dll` | present |
| `tkinter` | absent (excluded in the spec) |

Only `recogniser.exe` and `_internal\` sit at the bundle root. Application code
is packed into the PyInstaller archive inside the executable, so no `backend\`
directory appears in the bundle; the frontend and model files are the only
readable resources that must stay as real files.

## 4. Packaging design

### 4.1 Bundle layout (onedir)

```
dist/recogniser/
  recogniser.exe
  _internal/            <- contents directory
    backend/...
    frontend/...
    models/0-numbers/...
    webview/..., onnxruntime/..., clr_loader/...
```

`_internal` is set explicitly on `EXE()` via `contents_directory="_internal"`;
`COLLECT` is left without that argument. `sys._MEIPASS` then resolves to
`dist/recogniser/_internal`, which is the resource root in frozen mode.

### 4.2 Entry-point contract

`packaging/launcher.py` is a thin entry module:

```python
import sys

sys.dont_write_bytecode = True

from backend.main import main

if __name__ == "__main__":
    raise SystemExit(main())
```

- It imports the same `backend` package that `python -m backend.main` imports,
  so `backend.main.main()` is the single launch path for source and frozen runs.
- It performs no `os.chdir()`, so resource resolution may not depend on the
  working directory.
- `backend.main.main(argv=None) -> int` keeps its current responsibility and adds
  argument handling (`--self-test`), the renderer guard, and error logging
  (section 4.5). It returns the process exit code, because a failing self-test
  must fail the build and the launcher passes the value to `SystemExit`.

### 4.3 Resource resolution (minimal source change)

New module `backend/paths.py`:

```python
def resource_root() -> Path:
    """Root for read-only bundled resources, independent of CWD."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)


def model_resource_path(resource_dir: str, *parts: str) -> Path:
    """Resolve a registered model directory, stored relative to the project root."""
    return resource_path(*PurePosixPath(resource_dir).parts, *parts)


def data_dir() -> Path:
    """Writable per-user directory, outside the install directory."""
    override = os.environ.get("RECOGNISER_DATA_DIR")
    if override:
        base = Path(override)
        if not base.is_absolute():
            raise ValueError(
                f"RECOGNISER_DATA_DIR must be an absolute path, but it is {override!r}."
            )
    else:
        base = Path(os.environ["LOCALAPPDATA"]) / "recogniser"
    base.mkdir(parents=True, exist_ok=True)
    return base
```

`RECOGNISER_DATA_DIR` is accepted only as an **absolute** path. A relative
override is a configuration error and fails loudly instead of silently creating
a directory relative to whatever the working directory happens to be. Automated
checks therefore always pass an absolute path inside the project's `.tmp`
directory, for example
`RECOGNISER_DATA_DIR=C:\Users\<user>\veratic\recogniser\.tmp\selftest`.

Where each path is actually resolved — verified against the current code in
Stage 3, which corrects the earlier draft (section 11.1):

| Resolution | Current code | Change |
| --- | --- | --- |
| Frontend entry point | `backend/main.py`: `PROJECT_ROOT / "frontend" / "index.html"` | built from `resource_path("frontend", "index.html")` |
| pywebview storage | `backend/main.py`: `PROJECT_ROOT / ".webview-data"` | `data_dir() / "webview-data"` |
| Model directory | `backend/adapters/numbers.py`: `PROJECT_ROOT / model.resource_dir / filename` (`_model_resource`) | `model_resource_path(model.resource_dir, filename)`; the module-level `PROJECT_ROOT` is removed |

`backend/model_registry.py` is **not** modified. `ModelRegistration.resource_dir`
stays relative registration metadata (`"models/0-numbers"`), which the existing
registry test asserts and which keeps a display-name change from renaming a
directory. `models/0-numbers/model_0_numbers.py` is **not** modified either: it
resolves `model_0_numbers.onnx` from its own `__file__`, which is correct because
both files ship side by side as real files in the same bundle directory.

### 4.4 PyInstaller specification

`packaging/recogniser.spec` (analysed from `packaging/`, so `SPECPATH` is the
absolute path of `packaging/`):

```python
from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).resolve().parent

datas = [
    (str(PROJECT_ROOT / "frontend"), "frontend"),
    (str(PROJECT_ROOT / "models" / "0-numbers" / "model_0_numbers.py"),
     "models/0-numbers"),
    (str(PROJECT_ROOT / "models" / "0-numbers" / "model_0_numbers.onnx"),
     "models/0-numbers"),
]

a = Analysis(
    [str(PROJECT_ROOT / "packaging" / "launcher.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "backend.adapters.numbers",
        "onnxruntime",
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "_pytest", "tests"],
    noarchive=False,
)

pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="recogniser", debug=False, strip=False, upx=False,
    console=False,
    icon=str(PROJECT_ROOT / "packaging" / "assets" / "recogniser.ico"),
    version=str(PROJECT_ROOT / "build" / "version_info.txt"),
    contents_directory="_internal",
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="recogniser")
```

Rationale for each non-obvious choice:

- **Explicit model files, not the directory**: a directory tree would also
  capture `__pycache__`. Two explicit entries keep the bundle minimal and
  verifiable.
- **`backend.adapters.numbers`**: adapters are named in
  `backend/model_registry.py` (`adapter="backend.adapters.numbers"`) and loaded
  by `backend/api.py` with `importlib.import_module(model.adapter)`, which static
  analysis cannot follow. Without this entry the frozen application raises
  `ModuleNotFoundError` when it loads the model; it was added in `1c88f65` after
  the first bundle exposed the omission, and the bundle was rebuilt and
  re-reviewed.
- **`hiddenimports`**: `webview.guilib` selects platform modules dynamically, so
  static analysis cannot see `webview.platforms.winforms` / `edgechromium`.
  `onnxruntime` is imported by the model script, which ships as a data file and
  is never analysed, so it must be named explicitly.
- **Platform modules are not excluded**: `mshtml`/`cef` stay available so
  pywebview's renderer selection behaves exactly as in source and the startup
  assertion in section 4.7 can report the real selected renderer.
- **`console=False`** because the app is a GUI; runtime diagnostics go to a log
  file.
- **`upx=False`** to keep output reproducible and avoid corrupting onnxruntime
  and .NET assemblies.
- **No `collect_data_files` for `webview`/`pythonnet`**: their own hooks already
  provide `webview/lib`, `webview/js`, and `Python.Runtime.dll` (section 4.6).
  Adding them again would duplicate files.

### 4.5 Minimal source changes

| File | Change | Reason |
| --- | --- | --- |
| `backend/paths.py` (new) | `resource_root()`, `resource_path()`, `model_resource_path()`, `data_dir()` | CWD-independent resource root, per-user data directory, absolute-only override |
| `backend/diagnostics.py` (new) | log-file configuration, renderer detection, `--self-test` | A `console=False` build has no console, and Stage 4 needs a non-interactive check |
| `backend/main.py` | `resource_path()` for the frontend; pywebview storage under `data_dir()`; renderer guard; `--self-test`; error logging | Frozen-safe paths, actionable prerequisite error, testability |
| `backend/adapters/numbers.py` | `_model_resource()` uses `model_resource_path()`; the module-level `PROJECT_ROOT` is removed | This is where model paths are actually resolved, not the registry |
| `backend/model_registry.py` | **Unchanged** | `resource_dir` stays relative registration metadata |
| `models/0-numbers/*` | **Unchanged** | Model behaviour preserved; script and ONNX file stay side by side |

`backend/diagnostics.py` is the one module beyond the earlier draft's list, and
is justified here before it is created: the self-test has to be importable and
testable without importing `webview`, which imports pythonnet and .NET. Putting
it in `backend/main.py` would make the GUI layer a test dependency, and
`backend/paths.py` would then hold unrelated concerns. This is the final set:
`backend/api.py`, `backend/model_registry.py`, the frontend, and
`models/0-numbers/*` are unchanged by packaging.

### 4.6 Hook and collection status (verified against the installed versions)

| Concern | Evidence | Action |
| --- | --- | --- |
| Hook precedence | `PyInstaller/depend/analysis.py` assigns priorities: built-in `-2000`, hooks-contrib `-1000`, package-provided entry-point hooks `0`, user hooks `1000`; `build_main.discover_hook_directories()` puts contrib last | Package-provided hooks win, so no shadowing surprises |
| `hook-webview.py` | `webview/__pyinstaller/hook-webview.py` collects `webview/lib` data, `webview` dynamic libs, and `webview/js` data | Bundled automatically, including the JS bridge assets the contrib hook alone would omit |
| `hook-clr.py` | `pythonnet/_pyinstaller/hook-clr.py` collects `pythonnet` binaries and data (`Python.Runtime.dll`) | Bundled automatically |
| `hook-clr_loader.py` | Provided by hooks-contrib 2026.10 | `ClrLoader.dll` bundled automatically |
| `hook-onnxruntime.py` | Provided by hooks-contrib 2026.10 | `onnxruntime/capi` DLL/PYD bundled automatically |
| `hook-PIL.Image.py` | Built-in hook collects image plugin submodules | PNG/JPEG plugins available |

Consequence, confirmed by the accepted bundle: **no custom hooks and no
hand-written `binaries` entries**. Every native file listed in section 3 arrived
through those package and contrib hooks. The only analysis entry added after the
first build was the `backend.adapters.numbers` hidden import (section 4.4); it is
a dynamically imported pure-Python module, not a hook or a binary entry, and it
was required for the frozen model load to work at all.

### 4.7 Runtime prerequisites

- **WebView2** is required for the EdgeChromium renderer. The installer only
  documents it; it does not run a second detector.
- **VC++ 2015-2022 x64 runtime** is required by onnxruntime. It is present on
  the verified host; the installer documents it and does not bundle it.
- **.NET Framework 4.8** is required by pythonnet/WinForms. It ships with
  supported Windows 10/11 releases.

Application-level startup check (implemented and accepted): before creating the
window, `backend/main.py` initialises pywebview's GUI layer and reads its
renderer:

```python
from webview.guilib import initialize

renderer = initialize().renderer  # 'edgechromium' on a supported machine
```

The detected renderer is written to the log. If it is not `edgechromium`, the
application shows a message box naming the missing WebView2 Runtime, its
download URL, and the detected renderer, then exits with a non-zero code instead
of silently falling back to the deprecated MSHTML engine. This is a small
behaviour change for machines without WebView2. The guard was accepted in Stage 3,
so warn-and-continue in MSHTML is no longer an option: an affected machine sees
`recogniser cannot start` with the download URL and a non-zero exit code, and
nothing else in the application is reachable.

Verified against the installed pywebview 6.2.1 sources: `initialize()` returns the
platform module, `winforms.renderer` is assigned at import time from
`_is_chromium()`, `setup_app()` is guarded by an `_already_set_up_app` flag, and
`webview.start()` itself calls `initialize()` then reads `guilib.renderer`. The
guard therefore observes the same decision the real window will use, and calling
`initialize()` before `create_window()` is safe.

### 4.8 Writable user data

Facts about the current implementation:

- Nothing is persisted: the theme preference is intentionally in-memory only
  (`frontend/js/settings.js`), and uploads/drawings are never written to disk.
- The only writable path today is pywebview's storage directory, currently
  `<project>/.webview-data` (`WEBVIEW_STORAGE` in `backend/main.py`), which is
  already ignored by `.gitignore`.

Packaging rule:

- The install directory is treated as read-only; nothing is written beside the
  executable. `WEBVIEW_STORAGE` therefore moves under
  `%LOCALAPPDATA%\recogniser\webview-data` (section 4.3).
- Future persisted preferences belong in `%LOCALAPPDATA%\recogniser\`, not in the
  install directory; deciding whether preferences persist at all remains an open
  product decision and is out of scope here.
- The uninstaller must never delete anything under `%LOCALAPPDATA%\recogniser`.

### 4.9 Diagnostics

`backend/api.py` and the adapters already log through module loggers, but no
handler was configured, so a windowed frozen build would discard those records.
Stage 3 added the minimum needed to see failures:

| Item | Behaviour |
| --- | --- |
| Log file | A file handler on the root logger writing `%LOCALAPPDATA%\recogniser\logs\recogniser.log`; captures startup, renderer selection, resource root, and model load/recognition errors already logged by `backend.api` |
| `--self-test` flag | Writes `%LOCALAPPDATA%\recogniser\logs\self-test.json` (same directory as the log) with the frozen state, resource root, `frontend/index.html` presence, model directory contents, renderer, and the result of `Api().get_categories()` plus one `Api().recognise_category_upload(category_id, model_id, data_url)` call, built from the first category whose `input_modes` include `upload`, that category's first model, and a synthetic PNG data URL; exit code 0 on success, 1 on any failure |

`--self-test` is the only practical way to validate a frozen build
non-interactively, which is why it is in scope. Because the executable is built
with `console=False`, `sys.stdout` may be `None`, so the self-test reports
through a JSON file and the exit code rather than printing; the build script
reads that file. `RECOGNISER_DATA_DIR` redirects both the log and the report
into `.tmp\` during automated checks, and it must be an absolute path
(section 4.3).

Self-test contracts (corrected in Stage 3 — these follow the methods' actual
return types, not a guessed envelope):

| Check | Rule |
| --- | --- |
| `Api.get_categories()` | Must be a **category list** per `PLAN.md` section 7.4: a non-empty list of objects with `id`, `label`, `description`, `guidance`, `frontend_view`, `input_modes` (objects with `id`, `label`, `hint`), and `models` (objects with `id`, `category_id`, `series`, `display_name`, `description`, `instructions`, `input_label`). A recognition status envelope (`{"status": ...}`) is itself a failure |
| Recognition call | `Api().recognise_category_upload(category_id, model_id, data_url)` for the first category whose `input_modes` include `upload` and that category's first model. `ok` **and** `uncertain` are both passes; `error`, `invalid_input`, an exception, or a malformed result (`status` missing or not in that set, fields missing, non-text message, non-numeric confidence) are failures. `uncertain` is expected to be reachable, so it must not fail the build |
| Fixture | A deterministic in-memory PNG data URL drawn with Pillow (white 64 x 64 canvas, black "1" stroke). It must pass source-mode upload preprocessing, which is asserted by a regression test. The model's answer is never asserted beyond the accepted statuses |
| Renderer | Recorded, and must equal `edgechromium`, because the startup guard refuses any other renderer |
| Resources | Records the frozen state, resource root, data directory, `frontend/index.html` presence, and the file names found in every registered model directory |

The self-test never shows a dialog and never opens a window: `--self-test` must
be safe to run from a build script. Startup error dialogs are suppressed when
`--self-test` is present.

### 4.10 Icons

- Authorised source: `images/icon.png` (currently untracked; to be added as an
  asset without moving or renaming it). Verified in Stage 3 with Pillow: PNG,
  RGBA, `1254 x 1254`. The ICO entries are generated from that actual image.
- Generated asset: `packaging/assets/recogniser.ico` containing 16, 24, 32, 48,
  64, 128, and 256 px entries, produced from the PNG by
  `packaging/prepare_build.py` (invoked by `packaging/build.ps1`) using Pillow's
  multi-size ICO writer, which resizes each entry with LANCZOS.
- The ICO is committed; the PNG is not modified, moved, or renamed.
- The earlier draft's `image/icon.png` path was wrong.

Icon verification is done in four independent steps, because they are separate
resources:

| Surface | How it is set | Verified by |
| --- | --- | --- |
| Executable file icon | `icon=` in `EXE()` | `[System.Drawing.Icon]::ExtractAssociatedIcon()` on `recogniser.exe` |
| Window title-bar icon | `webview/platforms/winforms.py` falls back to `ExtractIconW(GetModuleHandleW(None), sys.executable, 0)` when no `icon=` is passed to `start()` | Manual user inspection |
| Taskbar icon | Same source as the window icon | Manual user inspection |
| Installer / shortcut icons | `SetupIconFile` and `[Icons]` `IconFilename` | `ExtractAssociatedIcon()` on the setup file, then manual user inspection |

### 4.11 Version

- Single source: `packaging/version.txt` containing `1.0.0`, the accepted
  first-release version; change it there and rebuild to publish a new version.
- The build script expands it into `build/version_info.txt` (four-part
  `1.0.0.0`) for `EXE(version=...)`, and passes `1.0.0` / `1.0.0.0` to ISCC as
  `AppVersion` / `AppVersion4`.
- Before compiling the installer, the build script compares the built
  executable's **numeric** PE version fields (`FileMajorPart` to `FilePrivatePart`)
  with `packaging\version.txt`, so the app and the installer cannot drift. The
  first version of that check compared the display string, which reads `1.0.0`
  for a correct `1.0.0.0` resource and would have rejected a valid executable;
  the numeric comparison replaced it before the installer was accepted.
- After ISCC returns, the script re-checks `dist\recogniser` against the manifest.
  A compile that changed a bundled file is reported as unreviewed rather than
  distributed, because the setup would no longer wrap the accepted bytes.
- Publisher, company, and copyright fields stay empty/neutral until the user
  supplies them.

### 4.12 Architecture and install scope

- Verified target: Windows x64 on Windows 11. Only that combination is tested.
- `SetupArchitecture=x64` builds a 64-bit installer.
- `ArchitecturesAllowed=x64compatible and not arm64` denies Windows on ARM and
  32-bit Windows, and accepts x64 Windows. `x64compatible` would otherwise also
  permit ARM64, where no build has been tested.
- `ArchitecturesInstallIn64BitMode=x64compatible`.
- `PrivilegesRequired=lowest` with `DefaultDirName={autopf}\recogniser` gives a
  per-user install requiring no elevation. All-users installs are deferred (they
  would need `PrivilegesRequiredOverridesAllowed` and a second uninstall path).

### 4.13 Installer (implemented)

`packaging\recogniser.iss`, compiled **only** by `packaging\build.ps1 -Installer`:

| Item | Value |
| --- | --- |
| `AppId` | `{76658801-C6D0-4BEF-BCF2-2093DB21D42E}` — generated once and never changed; a new value makes Windows treat a release as a different product and leaves the old version installed beside it |
| Display name | `recogniser 1.0.0` (`AppVerName`, also `UninstallDisplayName`) |
| Install directory | `{autopf}\recogniser`, which resolves to `%LOCALAPPDATA%\Programs\recogniser` because `PrivilegesRequired=lowest` |
| Shortcuts | Start menu `recogniser`; optional desktop shortcut (`desktopicon` task, unchecked by default) |
| Uninstaller | `unins000.exe` in the install directory, listed in Settings → Apps as `recogniser 1.0.0` |
| Writes outside the install directory | None at install time. There is no `[UninstallDelete]`, the application never writes into `{app}`, and nothing under `%LOCALAPPDATA%\recogniser` is removed on uninstall |
| Prerequisites | Documented on the wizard's welcome page (`[Messages] WelcomeLabel2` names WebView2 and the VC++ 2015-2022 x64 redistributable) and reported by the application's own renderer guard; the installer runs no second detection pass |
| Output | `dist\installer\recogniser-1.0.0-setup.exe` plus `recogniser-1.0.0-setup.exe.sha256` |
| Compression | `lzma2/max`, solid |
| Version metadata | Supplied by `build.ps1` as `/DAppVersion=1.0.0` and `/DAppVersion4=1.0.0.0`; the `.iss` file has no version of its own and refuses to compile without both defines |

The setup file's own version resource is `1.0.0` (`ProductVersion 1.0.0.0`), which
is how the compiled installer is matched to `packaging\version.txt` after the
fact.

## 5. Output locations and Git hygiene

| Path | Content | Tracked? |
| --- | --- | --- |
| `build/` | PyInstaller work directory, generated `version_info.txt`, temporary test data | Ignored (Stage 2) |
| `build/bundle-manifest.json` | Reviewed-bundle manifest: every file in `dist/recogniser` with its SHA-256, stored **outside** that directory | Ignored (Stage 2) |
| `dist/recogniser/` | Frozen onedir bundle | Ignored (Stage 2) |
| `dist/installer/` | Compiled setup executable and checksum file | Ignored (Stage 2) |
| `packaging/` | `launcher.py`, `recogniser.spec`, `build.ps1`, `prepare_build.py`, `version.txt`, `recogniser.iss`, `assets/recogniser.ico` | Tracked (`recogniser.iss` not yet committed) |
| `images/icon.png` | Icon source, never modified by the build | Tracked |
| `docs/` | `BUILDING.md` and `INSTALL.md` (Stage 6) | Tracked |
| `.tmp/` | Scratch space for the build scripts: `TEMP`/`TMP`, `PYTHONPYCACHEPREFIX`, `PYINSTALLER_CONFIG_DIR`, the logs `build-tests.log`, `prepare-build.log`, `pyinstaller.log`, `iscc.log`, and the self-test data directories `selftest-project`, `selftest-cwd-data`, `selftest-cwd` | Ignored (existing rule) |

- Stage 2 added exactly two ignore entries, `build/` and `dist/`, before any
  build output existed. `git check-ignore -v` confirms that `build\probe`,
  `dist\probe`, and `dist\installer\probe` match those rules, while
  `packaging\recogniser.spec`, `packaging\recogniser.iss`, and `images\icon.png`
  print nothing.
- No broad `*.exe`, `*.dll`, `*.spec`, `*.iss`, or `*.ico` patterns were added;
  those would silently hide deliverables or the icon source.
- `images/icon.png` and `PACKAGING_PLAN.md` are tracked as normal project files.
- `AGENTS.md` rule 3 applies: a stage's approval is not commit approval, and no
  commit or push happens unless the user explicitly asks for it.

## 6. Stage plan

Each stage below was reported with files changed, checks and actual results,
manual inspection steps, limitations, and the proposed next stage, then stopped
for explicit approval. Stages 1–5 are accepted and their outcomes are recorded in
place; Stage 6 is the current revision and awaits acceptance.

### Stage 1 — Inspect and plan (accepted)

Deliverable: a packaging plan that matches the installed tooling, the actual
project layout, and the agreed stage order.

Files: `PACKAGING_PLAN.md` (this document, rewritten).

Checks performed for this revision:

| Check | Actual result |
| --- | --- |
| `.\venv\Scripts\python.exe -m PyInstaller --version` | `6.22.3` |
| `.\venv\Scripts\python.exe -c "import sys; print(sys.executable); print(sys.version)"` | venv interpreter, `3.10.3`, AMD64 |
| `pyinstaller-hooks-contrib`, `pywebview`, `pythonnet`, `clr_loader`, `onnxruntime`, `numpy`, `Pillow` versions | as listed in section 2.1 |
| Inno Setup installation and version | `7.1.1`, `C:\Program Files\Inno Setup 7\ISCC.exe`, banner verified, not on `PATH` |
| PyInstaller `EXE`/`COLLECT` signature, `contents_directory` | present on `EXE`, absent from `COLLECT` |
| Package hooks present (`webview`, `pythonnet`, contrib `onnxruntime`/`clr_loader`) | confirmed by reading the installed hook files |
| Hook precedence | package hooks (`0`) outrank contrib (`-1000`) |
| PyInstaller `SPECPATH` available inside spec files | `PyInstaller/building/build_main.py` injects it |
| Icon source | `images\icon.png` exists; earlier `image/icon.png` path was wrong |
| `git status`, `git log -1`, branch | at the time: untracked `PACKAGING_PLAN.md` and `images/`; `main` at `eedcc00` |
| `.gitignore` contents | at the time: no `build/` or `dist/` rules yet; Stage 2 added them at lines 21–22 |

Checks not performed in that revision: no build, no installer compilation, and no
test run, because it was a document-only change. Those checks belong to Stages 3–5
and were run there.

Manual inspection: read this document and confirm the stage split, the icon
source path, and the decisions recorded in section 9.

Limitations at the time: everything about the produced bundle was an expectation;
the hook inventory and native library paths were unverified until Stage 4.
Section 3 now records the confirmed inventory.

Next: Stage 2 — `.gitignore` only. **Approved and completed.**

### Stage 2 — Ignore build outputs (`.gitignore` only, accepted)

Deliverable: `build/` and `dist/` are ignored before anything is generated, so no
build artifact can be staged accidentally in later stages.

Files: `.gitignore` (two added entries, nothing removed or reorganised).

Checks:

```powershell
git check-ignore -v build\probe dist\probe dist\installer\probe   # each must match
git check-ignore -v packaging\recogniser.spec images\icon.png      # must print nothing
git status --short                                                # only .gitignore modified
```

Actual results: the three probes report `.gitignore:21:build/` and
`.gitignore:22:dist/`; the deliverable probes print nothing. Both entries were
committed in `2f9c70f`.

Manual inspection: confirm the diff contains only `build/` and `dist/`.

Limitations: none functional.

Next: Stage 3 — icons, spec, entry module, build script, minimal source changes.
**Approved and completed.**

### Stage 3 — Packaging assets and build inputs (accepted)

Deliverable: all packaging inputs exist and are reviewable without producing a
bundle.

Files created:

| File | Purpose |
| --- | --- |
| `packaging/launcher.py` | Frozen entry point; imports and calls `backend.main.main` |
| `packaging/recogniser.spec` | PyInstaller onedir configuration (section 4.4) |
| `packaging/version.txt` | `1.0.0` version source, accepted for the first release |
| `packaging/prepare_build.py` | Validates the version, writes `build/version_info.txt`, generates the ICO when missing or stale |
| `packaging/build.ps1` | Tests, PyInstaller run, bundle inventory, manifest, self-test, optional ISCC |
| `packaging/assets/recogniser.ico` | Multi-resolution icon derived from `images/icon.png` |
| `backend/paths.py` | Frozen-aware resource root, model directory, data directory |
| `backend/diagnostics.py` | Log file, renderer detection, `--self-test` |

Files modified: `backend/main.py` (resource path, pywebview storage, renderer
guard, logging, `--self-test`), `backend/adapters/numbers.py` (`_model_resource`
uses `model_resource_path`), plus a new `tests/test_paths_and_diagnostics.py` for
the paths helper and the self-test rules. `backend/model_registry.py` and
`models/0-numbers/*` are unchanged.

Build script contract (also serves Stage 4 and Stage 5):

- Resolves the project root from `$PSScriptRoot`; every path is absolute and
  inside the project.
- Redirects `TEMP`, `TMP`, `PYTHONPYCACHEPREFIX`, and `PYINSTALLER_CONFIG_DIR`
  into `.tmp\` so no cache lands outside the project.
- Verifies the venv interpreter and PyInstaller version, runs the backend tests,
  and generates `build/version_info.txt` plus the ICO through
  `packaging/prepare_build.py`.
- Runs `python -m PyInstaller --noconfirm --distpath dist --workpath build\pyinstaller packaging\recogniser.spec`
  (`--clean` only with `-Clean`) and stops on any non-zero exit code.
- Verifies the produced inventory, runs `dist\recogniser\recogniser.exe
  --self-test` from two different working directories with an absolute
  `RECOGNISER_DATA_DIR` under `.tmp`, and then writes
  `build\bundle-manifest.json` (relative path and SHA-256 for every file in
  `dist\recogniser`).
- With `-Installer`: refuses to run unless `dist\recogniser` matches the
  manifest exactly, so the installer can only wrap the bundle reviewed in
  Stage 4. It locates ISCC (explicit `-IsccPath`, then
  `C:\Program Files\Inno Setup 7\ISCC.exe`, then `Get-Command`), verifies the
  built executable's file version, compiles the installer with
  `/DAppVersion=... /DAppVersion4=...`, and prints its SHA-256. It never invokes
  PyInstaller.

Checks:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v      # all tests pass
.\venv\Scripts\python.exe -m py_compile backend\paths.py backend\diagnostics.py backend\main.py backend\adapters\numbers.py packaging\launcher.py packaging\prepare_build.py
.\venv\Scripts\python.exe -c "import packaging; print(packaging.__file__)"   # site-packages, not ..\packaging
.\venv\Scripts\python.exe packaging\prepare_build.py
# source-mode self-test: exits 0 and writes the JSON report
$env:RECOGNISER_DATA_DIR = "C:\Users\<user>\veratic\recogniser\.tmp\selftest"   # absolute, per section 4.3
.\venv\Scripts\python.exe -m backend.main --self-test
```

The `packaging` import check guards against the new `packaging\` directory
shadowing the installed `packaging` library.

Manual inspection: run the application from source as before
(`.\venv\Scripts\python.exe -m backend.main`), confirm the window, upload, and
recognition are unchanged, and open `packaging\assets\recogniser.ico` in an image
viewer to confirm it looks like the intended icon. Source runs now keep
pywebview data and the log under `%LOCALAPPDATA%\recogniser`; set
`RECOGNISER_DATA_DIR` to an absolute path to keep them elsewhere.

Limitations: nothing is built yet, so no claim is made about bundle contents.
The renderer guard, the moved writable data directory, and `--self-test` are new
behaviour and need explicit user acceptance.

Outcome (accepted): every file above exists and was committed in `2f9c70f`. The
checks in that stage ran as written, and the artefacts they left in `.tmp\` and
`build\` are still present:

| Check | Actual result |
| --- | --- |
| `python -m unittest discover -s tests -v` | 36 tests, `OK`; re-run in Stage 6 as `Ran 36 tests in 0.036s` |
| `python packaging\prepare_build.py` | `Version: 1.0.0 (file version 1.0.0.0)`, `Icon entries: [16, 24, 32, 48, 64, 128, 256]` (`.tmp\prepare-build.log`) |
| `import packaging` | resolves into `venv\Lib\site-packages\packaging`, so the new `packaging\` directory does not shadow it; `build.ps1` re-checks this on every build |
| Source-mode `--self-test` | exit code 0 with an absolute `RECOGNISER_DATA_DIR` under `.tmp\` |
| Renderer guard | accepted; a non-`edgechromium` renderer shows `recogniser cannot start` and exits 1 |

Next: Stage 4 — build and verify the onedir bundle. **Approved and completed.**

### Stage 4 — Build and verify the onedir bundle (accepted)

Deliverable: `dist\recogniser\recogniser.exe` runs the application with bundled
frontend and model, independent of the working directory.

Commands:

```powershell
.\packaging\build.ps1 -Clean
```

Checks specified for this stage (actual results are recorded in the outcome block
below):

| Check | Expected result |
| --- | --- |
| PyInstaller exit code | `0`, `dist\recogniser\recogniser.exe` exists |
| Bundle inventory | `frontend/index.html`, both CSS files and all four JS files, `models/0-numbers/model_0_numbers.py` and `.onnx`, `webview/lib`, `webview/js`, `pythonnet` runtime, `clr_loader` `ClrLoader.dll`, `onnxruntime/capi` native files |
| Exclusions | `frontend` and `models` exist only under `_internal`, no `__pycache__` under `models/`, no `tests` package, no `tkinter` |
| `--self-test` from the project root | exit code `0`, JSON report written |
| `--self-test` with the working directory set to `.tmp` | exit code `0` (proves CWD independence) |
| PE icon resource | `[System.Drawing.Icon]::ExtractAssociatedIcon()` returns a non-null icon whose size matches an embedded entry |
| Log file | written to the recorded `%LOCALAPPDATA%\recogniser\logs\` path (or the redirected test directory) |
| Working tree | `git status --short` shows no build outputs (ignored) |
| Bundle manifest | `build\bundle-manifest.json` exists outside `dist\recogniser` and lists a relative path plus SHA-256 for **every** file in the bundle; re-verifying immediately after the build reports no added, missing, or modified files |

The bundle produced in this stage is the **reviewed bundle**. Its manifest is the
record of exactly which bytes the user accepted, and Stage 5 refuses to build an
installer from anything else. If a bundle file changes after review — a rebuilt
bundle, a hand-edited config, a stray log — the manifest no longer matches and
the installer step fails until the bundle is rebuilt, reverified, and reviewed
again.

Outcome (accepted): the bundle was built, the tests in section 6 ran inside
`build.ps1`, and the user reviewed the bundle. The first build omitted the
dynamically loaded adapter, so `1c88f65` added `backend.adapters.numbers` to
`hiddenimports` and the bundle was rebuilt and re-reviewed. Evidence from the
accepted run, re-checked on 26 November 2026:

| Check | Actual result |
| --- | --- |
| Bundle inventory | 239 files, 97.0 MB. `frontend\index.html`, `css\style.css`, `css\themes.css`, `js\bridge.js`, `js\main.js`, `js\settings.js`, `categories\numbers.js`, both `model_0_numbers` files, `webview\lib`, `webview\js`, `pythonnet\runtime\Python.Runtime.dll`, `clr_loader\ffi\dlls\amd64`, and `onnxruntime\capi\onnxruntime.dll` are present; `tkinter` is absent and there is no `__pycache__` under `models\` |
| Frozen `--self-test` from the project root | exit code 0; report `frozen=True`, `renderer='edgechromium'`, `passed=True`, recognition status `ok` (`.tmp\selftest-project\logs\self-test.json`) |
| Frozen `--self-test` from `.tmp\selftest-cwd` | exit code 0 with the same report values (`.tmp\selftest-cwd-data\logs\self-test.json`), which is what proves working-directory independence |
| Bundle manifest | `build\bundle-manifest.json` lists 239 files with a relative path and SHA-256 each, created `2026-11-25T14:24:01Z`; recomputing every hash now reports 0 added, missing, or modified files |
| Working tree | `git status --short` lists no `build\` or `dist\` content |
| User review | the bundle launched from Explorer, showed the styled window with no error dialog, recognised an uploaded image and a drawing, and the executable, title-bar, and taskbar icons were accepted |

Manual inspection:

1. Launch `dist\recogniser\recogniser.exe` from Explorer.
2. Confirm the window loads styled content and no error dialog appears.
3. Upload a number image and draw a digit; both must produce the same result as
   the source build.
4. Confirm the executable file icon, the title-bar icon, and the taskbar icon.
5. Switch themes and toggle the settings that exist today.

Limitations: only this Windows 11 x64 machine is tested. Native library paths are
confirmed only to the extent the self-test and manual run exercise them.
Clean-machine behaviour, ARM64, and machines without WebView2 remain untested.

Next: Stage 5 — Inno Setup installer. **Approved and completed.**

### Stage 5 — Inno Setup installer (accepted)

Deliverable: `dist\installer\recogniser-1.0.0-setup.exe` compiled from
`packaging\recogniser.iss`.

Script shape:

```ini
; Version comes from packaging\version.txt through build.ps1:
;   ISCC.exe /DAppVersion=1.0.0 /DAppVersion4=1.0.0.0 packaging\recogniser.iss
#ifndef AppVersion
  #error AppVersion must be supplied by packaging\build.ps1
#endif

[Setup]
AppId={{76658801-C6D0-4BEF-BCF2-2093DB21D42E}
AppName=recogniser
AppVersion={#AppVersion}
AppVerName=recogniser {#AppVersion}
UninstallDisplayName=recogniser {#AppVersion}
DefaultDirName={autopf}\recogniser
DisableProgramGroupPage=yes
DisableWelcomePage=no
SetupIconFile=assets\recogniser.ico
UninstallDisplayIcon={app}\recogniser.exe
VersionInfoVersion={#AppVersion4}
VersionInfoProductVersion={#AppVersion4}
VersionInfoTextVersion={#AppVersion}
VersionInfoProductName=recogniser
VersionInfoDescription=recogniser Setup
SetupArchitecture=x64
ArchitecturesAllowed=x64compatible and not arm64
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
OutputDir=..\dist\installer
OutputBaseFilename=recogniser-{#AppVersion}-setup

[Files]
Source: "..\dist\recogniser\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\recogniser"; Filename: "{app}\recogniser.exe"; IconFilename: "{app}\recogniser.exe"
Name: "{autodesktop}\recogniser"; Filename: "{app}\recogniser.exe"; IconFilename: "{app}\recogniser.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\recogniser.exe"; Description: "Launch recogniser"; Flags: nowait postinstall skipifsilent
```

- The build script passes `AppVersion` and `AppVersion4` from
  `packaging\version.txt`, so there is exactly one version source and the
  installer never parses version strings itself.
- **Bundle guard**: before compiling, `build.ps1 -Installer` recomputes the
  SHA-256 of every file under `dist\recogniser` and compares the set and hashes
  with `build\bundle-manifest.json`. Added, missing, or modified files abort the
  compile with a message telling the user to rebuild and re-verify the bundle;
  a missing manifest aborts too, because there would be nothing proving which
  bundle was reviewed. `-Installer` never invokes PyInstaller, so it cannot
  silently replace the reviewed bundle with a new build.
- The `AppId` GUID `{76658801-C6D0-4BEF-BCF2-2093DB21D42E}` was generated once
  with `[guid]::NewGuid()` during this stage and is now fixed in section 4.13 and
  in `packaging\recogniser.iss`. Every future version reuses it.
- No `[UninstallDelete]`, no `{app}` writes, no `{localappdata}` deletion.
- No `[Code]` prerequisite detection. The app's own startup guard reports a
  missing WebView2 with an actionable message; duplicating the detection in the
  installer risks contradictory results. WebView2 and VC++ requirements are
  documented in the installer's info page text and in `docs/`.

Commands (run only after Stage 4's reviewed bundle is accepted; this never
rebuilds the application):

```powershell
.\packaging\build.ps1 -Installer
```

Checks:

| Check | Actual result |
| --- | --- |
| ISCC exit code | `0`; `.tmp\iscc.log` ends with `Successful compile (11.781 sec)` and names `dist\installer\recogniser-1.0.0-setup.exe` |
| Output file | `dist\installer\recogniser-1.0.0-setup.exe` exists (28.1 MB) with SHA-256 `dddda0833dcaf96625648eb036de3fc1f4f540e4e655e18d77b35198a298715f` recorded in `recogniser-1.0.0-setup.exe.sha256` |
| Setup architecture | PE `e_machine` of the setup executable is `0x8664` |
| Version metadata | setup file version `1.0.0`, product version `1.0.0.0`, product name `recogniser` |
| Icon resource | `[System.Drawing.Icon]::ExtractAssociatedIcon()` returns a non-null icon for both the setup file and `recogniser.exe` |
| Uninstall entry name | `recogniser 1.0.0`, from `AppVerName` / `UninstallDisplayName`; the script contains no Python or virtual-environment path |
| Repo state | at the time: `dist\installer\` ignored; `packaging\recogniser.iss` and the `build.ps1` corrections uncommitted. Both were committed later in `baa1c51` |
| Bundle guard | not re-run in Stage 6, because breaking the bundle to test it would modify the reviewed bundle and `-Installer` would recompile the accepted setup. The guard's comparison is the same function the build path uses, and re-checking the accepted bundle today reported 0 differences |

User verification record (performed by the user on 26 November 2026, accepted,
because running the installer writes outside this project's boundary): the user
ran `dist\installer\recogniser-1.0.0-setup.exe`, completed the installation, and
confirmed that the installed application launched from the Start-menu shortcut and
recognised both an uploaded image and a freehand drawing, and that the shortcut
and application icons were acceptable. The installation completed as the per-user
install the script requests.

Not separately recorded in this document: the exact install directory contents,
the state of `%LOCALAPPDATA%\recogniser` after the uninstall, and whether the
uninstaller removed the install directory and shortcuts. The script has no
`[UninstallDelete]` and nothing writes into `{app}`, which is why user data cannot
be removed by the uninstaller, but this is a property of the script rather than an
observation.

Limitations: the agent does not install or uninstall the package, so install-time
behaviour is verified by the user only. No clean-machine, ARM64, or no-WebView2
machine is tested.

Next: Stage 6 — installation verification and documentation.
**Approved and completed.**

### Stage 6 — Installation verification and documentation (this revision)

Deliverable: the build and install process is documented so that someone else can
reproduce the bundle and the installer, and the accepted user verification is
recorded.

Files created or changed in this stage:

| File | Change |
| --- | --- |
| `docs/BUILDING.md` (new) | Prerequisites, including the note that the environment directory is `venv\` rather than `.venv\`, one-command bundle build, outputs and logs, frozen and source self-test, installer packaging and the manifest guard, version and icon changes, bundle contents (`hiddenimports`), troubleshooting |
| `docs/INSTALL.md` (new) | Requirements (WebView2, VC++ redistributable), hash verification, install/unattended install, launch, data locations, upgrade, uninstall and what it leaves behind, troubleshooting, what is not included |
| `README.md` | New “Build and install” section linking both documents; project layout lists `packaging/`, `docs/`, `build/`, `dist/`, and both test modules; adding a model now says to extend the spec's `datas` and `hiddenimports` for the packaged build; the limitation that there was no installer is replaced by an accurate installer limitation |
| `PACKAGING_PLAN.md` | Stages 1–5 marked accepted with their actual results; this stage records the documentation and the user's install verification |

Checks, run from the project root on 26 November 2026 exactly as the documents
write them:

| Check | Actual result |
| --- | --- |
| `.\venv\Scripts\python.exe -m unittest discover -s tests -v` | exit code 0, `Ran 36 tests in 0.036s`, `OK` (`.tmp\stage6-unittest.txt`) |
| `.\venv\Scripts\python.exe packaging\prepare_build.py` (BUILDING.md, icon section) | exit code 0; `Version: 1.0.0 (file version 1.0.0.0)`, `Icon up to date`, `Icon entries: [16, 24, 32, 48, 64, 128, 256]` |
| Source self-test (BUILDING.md): `RECOGNISER_DATA_DIR=.tmp\source-selftest`, `python -m backend.main --self-test` | exit code 0, report `frozen=False`, `passed=True` |
| Frozen self-test (BUILDING.md): `RECOGNISER_DATA_DIR=.tmp\manual-selftest`, `Start-Process … --self-test -Wait` | exit code 0, report `frozen=True`, `renderer=edgechromium`, `passed=True`, recognition status `ok` |
| Installer hash (INSTALL.md): `Get-FileHash … -Algorithm SHA256` | `dddda0833dcaf96625648eb036de3fc1f4f540e4e655e18d77b35198a298715f`, identical to `.sha256` |
| Every path the documents reference | all present: `README.md`, `PACKAGING_PLAN.md`, `images\icon.png`, `docs\BUILDING.md`, `docs\INSTALL.md`, both packaging scripts, the spec, the `.iss`, `version.txt`, the ICO, and `dist\recogniser\recogniser.exe` |
| Markdown links between the documents | `docs/BUILDING.md` ↔ `docs/INSTALL.md` ↔ `README.md` resolve to existing files; a scripted check of every relative `.md` link in `README.md`, `PACKAGING_PLAN.md`, and both `docs/` files reports all targets present |
| Commands re-checked after the final document edits | `Ran 36 tests in 0.181s`, `OK` (`.tmp\stage6-unittest-recheck.txt`); the slower time comes from the check's own `PYTHONPYCACHEPREFIX`; the source and frozen self-tests were re-run after the edits with the same results |

Checks not performed: `.\packaging\build.ps1`, `-Clean`, and `-Installer` were not
re-run in this stage, because they would rebuild or recompile the accepted
artefacts. Their behaviour was exercised in Stages 4 and 5, and today's
`prepare_build.py` and self-test runs confirm the inputs they consume are intact.

Manual verification steps for the user (visual and install acceptance is theirs):

1. Read `docs/BUILDING.md` and `docs/INSTALL.md` and confirm the commands match
   what you would run.
2. Optionally re-run `.\packaging\build.ps1` and `.\packaging\build.ps1 -Installer`
   to confirm the documents from a clean `dist\`.
3. Confirm the uninstall behaviour described in `docs/INSTALL.md`: the
   uninstaller removes the install directory and shortcuts but leaves
   `%LOCALAPPDATA%\recogniser`.

Known limitations and unresolved items:

- Install behaviour is recorded from the user's acceptance and is not
  reproducible by the agent, which does not write outside the project.
- Not verified: a clean Windows 11 machine, Windows 10 1809, ARM64, machines
  without WebView2, code signing, and SmartScreen reputation.
- The installation-time details the user did not report (install directory
  contents, data directory after uninstall) are marked as not separately
  recorded rather than asserted.

Next: packaging is complete. Remaining work proceeds only on user request.
**STOP for explicit approval.**

## 7. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Missing or duplicate native dependency in the bundle | Rely on package hooks; verify inventory and run `--self-test`; add one targeted entry only for an observed failure |
| CWD-dependent resource bug | `resource_path()` plus self-test from two working directories |
| Model loaded from the wrong location | Model files ship as real files beside their script; self-test asserts the ONNX path |
| Missing WebView2 on a target machine | Documented prerequisite plus the startup renderer guard |
| Deprecated MSHTML renderer used silently | Guard exits with an actionable message; confirmed in Stage 4, and documented in `docs/INSTALL.md` |
| Installer deleting user data on uninstall | No `[UninstallDelete]`; all writable data under `%LOCALAPPDATA%` |
| Build artifacts entering Git | `build/` and `dist/` ignored before the first build (Stage 2) |
| Writing outside the project during build | `TEMP`, `TMP`, `PYTHONPYCACHEPREFIX`, `PYINSTALLER_CONFIG_DIR` redirected to `.tmp\`; the only exception is the app's own `%LOCALAPPDATA%` data at runtime, which can be overridden with `RECOGNISER_DATA_DIR` |
| Unverified Windows 10/ARM64 claims | Recorded as untested, not asserted |

## 8. Deferred items (not in this track)

- Code signing, SmartScreen reputation, publishing, releases, and remote pushes.
- Bundling or downloading the WebView2 Runtime and the VC++ redistributable.
- Onefile/portable distribution, MSI, or Windows Store packaging.
- All-users installs and machine-wide data.
- Windows 10 1809 compatibility claims, ARM64 builds, ARM64 testing.
- Python or dependency upgrades, lock files, or reproducible-build hashes.
- Installer-time prerequisite pages and `[Code]` checks.

## 9. Decisions to confirm

All four decisions were confirmed during implementation and are now settled by the
accepted stages:

1. Renderer guard: exit with a message when the renderer is not `edgechromium`
   (chosen and implemented; MSHTML is refused rather than used).
2. Version `1.0.0` from `packaging/version.txt` (chosen; still the current value,
   change it there and rebuild).
3. Per-user install only for the first release (chosen and implemented with
   `PrivilegesRequired=lowest`).
4. `images/icon.png`, `PACKAGING_PLAN.md`, and the `docs/` files to be tracked as
   normal project files (chosen and done).

## 10. Stage approval and Git policy

- One stage at a time; each report ends with a stop for explicit approval.
- Approval of a stage is not authorisation to commit it.
- No commits, amends, resets, branch changes, or pushes unless the user asks.
  When asked, only that stage's files are staged.
- Actual commit history for this work. Stages were implemented one at a time, but
  the user approved commits in two batches:

| Commit | Subject | Covers |
| --- | --- | --- |
| `2f9c70f` | `build: add Windows packaging configuration and frozen-safe runtime paths` | Stages 1–3: this plan, `.gitignore`, `images/icon.png`, the frozen-safe backend changes, tests, and the `packaging/` assets and build script |
| `1c88f65` | `build: fix packaging checks and include dynamically loaded adapter` | The Stage 4 correction that added `backend.adapters.numbers` to `hiddenimports` and tightened `build.ps1` |
| `baa1c51` | `build: add Inno Setup installer for per-user x64 install` | Stage 5: `packaging/recogniser.iss` and the `build.ps1` installer corrections (numeric version comparison, post-compile manifest re-check) |

- Committed after explicit instruction once Stages 5 and 6 were accepted:
  `packaging/build.ps1` and `packaging/recogniser.iss` in `baa1c51`, then this
  document, `README.md`, `docs/BUILDING.md`, and `docs/INSTALL.md` under the
  subject `docs: document building and installing the packaged application`.
- No generated output was committed: `build/`, `dist/`, and `.tmp/` stay ignored,
  and no file outside those two sets was staged.
- Nothing has been pushed, and the accepted bundle and installer were not rebuilt
  or recompiled to make these commits.

## 11. Corrections applied to the earlier draft

- Removed every "install PyInstaller / Inno Setup" instruction; both are
  installed and only availability checks remain.
- Replaced the Inno Setup 6.11.1 reference with the installed 7.1.1 and its
  `ISCC.exe` path.
- Corrected the icon path from `image/icon.png` to `images/icon.png`.
- Split icon verification into executable, window, taskbar, and installer
  surfaces instead of treating "the icon" as one check.
- Replaced speculative per-library `binaries` lists with verified hook coverage
  and an inventory check in Stage 4.
- Marked all native-library paths as expectations until the first build.
- Corrected hook precedence facts (package hooks beat hooks-contrib).
- Fixed the WebView2 registry example that stopped at the first non-empty value,
  and removed the duplicated installer prerequisite detection, so the installer
  and the app cannot disagree.
- Corrected `x64compatible`: it also allows ARM64, so `not arm64` is added and
  ARM64 is recorded as untested.
- Reduced the stage plan from a long narrative to six stages matching the agreed
  workflow, each with files, checks, manual steps, limitations, and a stop.
- Restricted Stage 2 to `.gitignore` and excluded broad artifact patterns.
- Removed all compatibility claims for clean machines and Windows 10 pending
  actual testing.
- Specified that `--self-test` reports through a JSON file and exit code, because
  a `console=False` build has no usable `sys.stdout`.
- Made `packaging/version.txt` the single version source for both the executable
  and the installer.

### 11.1 Corrections applied before Stage 3 implementation

The Stage 1 plan was accepted in principle, but these four findings were agreed
before any Stage 3 code was written. All of them are now reflected above.

1. **Model resource paths.** The earlier draft said `backend/model_registry.py`
   builds the model directory with `resource_path(...)`. Reading the current
   code showed the real resolution is
   `PROJECT_ROOT / model.resource_dir / filename` in
   `backend/adapters/numbers.py:_model_resource`. That function now uses the
   shared `model_resource_path()` helper from `backend/paths.py`; the registry
   keeps `resource_dir` as relative registration metadata and is not modified;
   `model_0_numbers.py` and `model_0_numbers.onnx` stay unchanged and side by
   side.
2. **Test data directory.** `RECOGNISER_DATA_DIR` must be an absolute path, and
   automated checks use absolute paths inside the project's `.tmp` directory.
   A relative override now fails with a clear `ValueError` instead of creating a
   directory relative to the working directory.
3. **Self-test contracts.** `Api.get_categories()` is validated as a category
   list per its real contract (`PLAN.md` section 7.4), never as a recognition
   status envelope. The recognition call accepts `ok` **or** `uncertain` and
   fails on `error`, `invalid_input`, exceptions, or malformed results. The
   fixture is a deterministic in-memory PNG that is asserted to pass
   source-mode preprocessing.
4. **Reviewed bundle.** Stage 5 must package the exact `dist\recogniser`
   directory reviewed in Stage 4. `build\bundle-manifest.json` records a
   relative path and SHA-256 for every file in that directory, and the installer
   step rejects added, missing, or modified files until the bundle is rebuilt,
   reverified, and accepted. The installer command never invokes PyInstaller.

## 12. Completion criteria and status

| Criterion | Status |
| --- | --- |
| One command builds the bundle from a prepared checkout | Met; `.\packaging\build.ps1` (Stage 4) |
| The frozen application runs from any working directory | Met; frozen self-test from two working directories (Stage 4) |
| Model resources are real files and load in the frozen build | Met; the dynamically imported adapter was added to `hiddenimports` in `1c88f65` |
| The test suite passes as part of the build | Met; 36 tests, `build.ps1` stops on failure (Stages 4 and 6) |
| A reviewed bundle can be packaged but never silently altered | Met; `build\bundle-manifest.json` and the `-Installer` guard (Stage 5) |
| The installer is per-user, x64, versioned, and carries the icon | Met; verified metadata and PE header (Stage 5) |
| User data survives uninstall | Met by design: no `[UninstallDelete]`, all writable data outside `{app}`. The user confirmed the install and run; the post-uninstall data state was not separately recorded |
| Build and install processes are documented | Met; `docs/BUILDING.md` and `docs/INSTALL.md`, with their commands re-run as written (Stage 6) |
| No build artefact enters Git | Met; `build/` and `dist/` ignored before the first build (Stage 2) |
| Clean Windows 11 machine, Windows 10 1809, ARM64, no-WebView2 machine | Not tested; recorded as limitations, not claimed |
| Code signing and SmartScreen reputation | Not done; deferred by section 8 |

Packaging is complete within this scope. Anything beyond this list — signing,
publishing, portable builds, additional models, or Windows 10 verification —
needs a new decision from the user.

