from __future__ import annotations

import json
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


ARTIFACT_SUFFIXES = {".lefx", ".lefxset"}
BUILD_TOOLS_ROOT = Path(SPECPATH).resolve()
PROJECT_ROOT = BUILD_TOOLS_ROOT.parent
BUILD_CONFIG_PATH = BUILD_TOOLS_ROOT / "build_config.json"
VERSION_PATH = BUILD_TOOLS_ROOT / "version.py"


def _load_version() -> str:
    namespace: dict[str, object] = {}
    exec(VERSION_PATH.read_text(encoding="utf-8"), namespace)
    version = namespace.get("__version__", "")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError(f"Invalid __version__ in {VERSION_PATH}")
    return version.strip().lstrip("v")


def _load_build_config() -> dict[str, object]:
    payload = json.loads(BUILD_CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Build config must be an object: {BUILD_CONFIG_PATH}")
    return payload


def _resolve_builtin_artifacts() -> list[Path]:
    entries = _load_build_config().get("builtin-effects-discovery", [])
    if not isinstance(entries, list):
        raise ValueError("build_config.json key 'builtin-effects-discovery' must be a list")

    resolved: list[Path] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, str) or not entry.strip():
            raise ValueError("builtin-effects-discovery entries must be non-empty strings")
        candidate = Path(entry)
        if not candidate.is_absolute():
            candidate = (PROJECT_ROOT / candidate).resolve()
        matches = (
            sorted(path.resolve() for path in candidate.rglob("*") if path.is_file() and path.suffix.lower() in ARTIFACT_SUFFIXES)
            if candidate.is_dir()
            else [candidate.resolve()]
        )
        for match in matches:
            key = str(match)
            if key in seen:
                continue
            seen.add(key)
            resolved.append(match)
    return resolved


def _artifact_destination(artifact: Path) -> str:
    try:
        relative = artifact.relative_to(PROJECT_ROOT)
    except ValueError:
        return "external_builtin_effects"
    return relative.parent.as_posix()


datas = [
    (str(BUILD_CONFIG_PATH), "build-tools"),
    (str(VERSION_PATH), "build-tools"),
    (str(PROJECT_ROOT / "src" / "python_control" / "xvf_host.py"), "src/python_control"),
    (str(PROJECT_ROOT / "src" / "python_control" / "respeaker_get_doa.py"), "src/python_control"),
]
datas.extend((str(path), _artifact_destination(path)) for path in _resolve_builtin_artifacts())

hiddenimports = sorted(
    set(
        collect_submodules("uvicorn")
        + collect_submodules("usb")
        + ["libusb_package"]
    )
)

exe_name = os.environ.get("LED_CONTROLLER_EXE_NAME", f"led_controller_service_{_load_version()}")

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(BUILD_TOOLS_ROOT / "hooks")],
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
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)
