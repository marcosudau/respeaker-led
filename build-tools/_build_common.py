from __future__ import annotations

import json
from pathlib import Path


ARTIFACT_SUFFIXES = {".lefx", ".lefxset"}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_TOOLS_ROOT = PROJECT_ROOT / "build-tools"
BUILD_CONFIG_PATH = BUILD_TOOLS_ROOT / "build_config.json"
VERSION_PATH = BUILD_TOOLS_ROOT / "version.py"
DEFAULT_TEMPLATE_ROOT = BUILD_TOOLS_ROOT / "template_release_bundle"
DEFAULT_RELEASE_BUNDLE_DIR = PROJECT_ROOT / "dist" / "release_bundle"


def load_python_version(version_path: Path = VERSION_PATH) -> str:
    namespace: dict[str, object] = {}
    exec(version_path.read_text(encoding="utf-8"), namespace)
    version = namespace.get("__version__", "")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError(f"Invalid __version__ in {version_path}")
    return version.strip().lstrip("v")


def load_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def load_build_config(config_path: Path = BUILD_CONFIG_PATH) -> dict[str, object]:
    if not config_path.is_file():
        raise FileNotFoundError(f"Build config not found: {config_path}")
    return load_json_object(config_path)


def resolve_project_path(value: str | Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate.resolve()
    return (PROJECT_ROOT / candidate).resolve()


def versioned_exe_name(*, version: str, include_version: bool) -> str:
    return f"led_controller_service_{version}.exe" if include_version else "led_controller_service.exe"


def bundle_directory_name(*, version: str, include_version: bool) -> str:
    return (
        f"led_controller_service_{version}_windows_x64"
        if include_version
        else "led_controller_service_windows_x64"
    )


def bundle_archive_name(*, version: str, include_version: bool) -> str:
    return f"{bundle_directory_name(version=version, include_version=include_version)}.zip"


def discover_builtin_artifacts(config_path: Path = BUILD_CONFIG_PATH) -> list[dict[str, object]]:
    config = load_build_config(config_path)
    entries = config.get("builtin-effects-discovery", [])
    if not isinstance(entries, list):
        raise ValueError("build_config.json key 'builtin-effects-discovery' must be a list")

    discovered: list[dict[str, object]] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, str) or not entry.strip():
            raise ValueError("builtin-effects-discovery entries must be non-empty strings")
        root = resolve_project_path(entry)
        if root.is_dir():
            matches = sorted(
                path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in ARTIFACT_SUFFIXES
            )
            for match in matches:
                _append_artifact(discovered, seen, source_path=match.resolve(), relative_path=match.relative_to(root))
            continue
        _append_artifact(discovered, seen, source_path=root.resolve(), relative_path=Path(root.name))
    return discovered


def _append_artifact(
    target: list[dict[str, object]],
    seen: set[str],
    *,
    source_path: Path,
    relative_path: Path,
) -> None:
    key = str(source_path)
    if key in seen:
        return
    seen.add(key)
    suffix = source_path.suffix.lower()
    if suffix not in ARTIFACT_SUFFIXES:
        return
    target.append(
        {
            "source_path": source_path,
            "relative_path": relative_path,
            "kind": "effect_set" if suffix == ".lefxset" else "effect_package",
        }
    )
