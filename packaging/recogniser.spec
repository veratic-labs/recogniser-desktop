# PyInstaller onedir specification for recogniser (Windows x64).
#
# Analyse from the project root with:
#
#   python -m PyInstaller --noconfirm --distpath dist --workpath build\pyinstaller packaging\recogniser.spec
#
# No custom hooks and no hand-written binaries: the package-provided hooks for
# webview and pythonnet, plus the hooks-contrib onnxruntime/clr_loader hooks,
# provide the native dependencies. Add an entry only for an observed failure.

from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).resolve().parent

# Two explicit model files rather than the directory tree, which would also copy
# __pycache__ into the bundle.
datas = [
    (str(PROJECT_ROOT / "frontend"), "frontend"),
    (
        str(PROJECT_ROOT / "models" / "0-numbers" / "model_0_numbers.py"),
        "models/0-numbers",
    ),
    (
        str(PROJECT_ROOT / "models" / "0-numbers" / "model_0_numbers.onnx"),
        "models/0-numbers",
    ),
]

a = Analysis(
    [str(PROJECT_ROOT / "packaging" / "launcher.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
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
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="recogniser",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(PROJECT_ROOT / "packaging" / "assets" / "recogniser.ico"),
    version=str(PROJECT_ROOT / "build" / "version_info.txt"),
    contents_directory="_internal",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="recogniser",
)
