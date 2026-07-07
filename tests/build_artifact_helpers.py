from __future__ import annotations

import importlib.util
import json
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_CONFIG_PATH = PROJECT_ROOT / "build-tools" / "build_config.json"
BUILD_TOOLS_ROOT = PROJECT_ROOT / "build-tools"


def configured_builtin_paths() -> list[Path]:
    payload = json.loads(BUILD_CONFIG_PATH.read_text(encoding="utf-8"))
    entries = payload.get("builtin-effects-discovery", [])
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
            sorted(path.resolve() for path in candidate.rglob("*") if path.is_file() and path.suffix.lower() in {".lefx", ".lefxset"})
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


def default_effect_set_path() -> Path:
    for path in configured_builtin_paths():
        if path.name == "default-effects.lefxset":
            return path
    raise FileNotFoundError("No configured default-effects.lefxset found in build-tools/build_config.json")


@lru_cache(maxsize=None)
def load_build_tool_module(module_name: str):
    module_path = BUILD_TOOLS_ROOT / "scripts" / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(f"tests.build_tools.{module_name}", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load build tool module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
