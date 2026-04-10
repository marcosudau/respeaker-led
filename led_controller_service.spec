from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


project_root = Path(SPECPATH).resolve()

datas = collect_data_files("led_effects", include_py_files=True)
datas += [
    (str(project_root / "python_control" / "xvf_host.py"), "python_control"),
    (str(project_root / "python_control" / "respeaker_get_doa.py"), "python_control"),
]

hiddenimports = sorted(
    set(
        collect_submodules("led_effects")
        + collect_submodules("uvicorn")
        + collect_submodules("usb")
        + ["libusb_package"]
    )
)


a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="led_controller_service",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)