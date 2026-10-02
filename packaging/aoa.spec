# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, copy_metadata
from pathlib import Path

project_root = Path(SPECPATH).parent

datas = [
    (str(project_root / "docs"), "docs"),
    (str(project_root / "data" / "sample"), "data/sample"),
    (str(project_root / "src" / "AOA" / "assets"), "AOA/assets"),
]
datas += collect_data_files("customtkinter")
for distribution in ("altair", "customtkinter", "matplotlib", "pandas", "plotly", "scikit-learn", "scipy"):
    try:
        datas += copy_metadata(distribution)
    except Exception:
        pass


analysis = Analysis(
    [str(project_root / "src" / "AOA" / "app.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "matplotlib.backends.backend_tkagg",
        "sklearn.ensemble",
        "sklearn.linear_model",
        "sklearn.metrics",
        "sklearn.model_selection",
        "sklearn.preprocessing",
        "sklearn.tree",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tabpfn", "xgboost"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="AOA",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "src" / "AOA" / "assets" / "brand" / "aoa.ico"),
)

collection = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AOA",
)
