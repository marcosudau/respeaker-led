from __future__ import annotations

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

from _build_common import (
    BUILD_CONFIG_PATH,
    PROJECT_ROOT,
    VERSION_PATH,
    discover_builtin_artifacts,
    load_python_version,
)


def build_datas() -> list[tuple[str, str]]:
    datas = [
        (str(BUILD_CONFIG_PATH), "build-tools"),
        (str(VERSION_PATH), "build-tools"),
        (str(PROJECT_ROOT / "src" / "python_control" / "xvf_host.py"), "src/python_control"),
        (str(PROJECT_ROOT / "src" / "python_control" / "respeaker_get_doa.py"), "src/python_control"),
    ]
    datas.extend(
        (str(Path(artifact["source_path"])), _artifact_destination(Path(artifact["source_path"])))
        for artifact in discover_builtin_artifacts(BUILD_CONFIG_PATH)
    )
    return datas


def build_hiddenimports() -> list[str]:
    uvicorn_runtime_imports = [
        "uvicorn.lifespan.on",
        "uvicorn.logging",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols.http.h11_impl",
    ]
    return sorted(set([*uvicorn_runtime_imports, *collect_submodules("usb"), "libusb_package"]))


def build_excludes() -> list[str]:
    return [
        "a2wsgi",
        "dotenv",
        "gunicorn",
        "httptools",
        "uvicorn.loops.auto",
        "uvicorn.loops.uvloop",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.protocols.websockets.websockets_sansio_impl",
        "uvicorn.protocols.websockets.wsproto_impl",
        "uvicorn.supervisors.watchfilesreload",
        "uvicorn.workers",
        "uvloop",
        "watchfiles",
        "websockets",
        "wsproto",
    ]


def exe_stem() -> str:
    versioned_default = f"led_controller_service_{load_python_version()}"
    return os.environ.get("LED_CONTROLLER_EXE_NAME", versioned_default)


def _artifact_destination(artifact: Path) -> str:
    try:
        relative = artifact.relative_to(PROJECT_ROOT)
    except ValueError:
        return "external_builtin_effects"
    return relative.parent.as_posix()
