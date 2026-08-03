from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import sys


SCRIPT_ROOT = Path(__file__).resolve().parent
BUILD_TOOLS_ROOT = SCRIPT_ROOT.parent
if str(BUILD_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(BUILD_TOOLS_ROOT))

from _build_common import PROJECT_ROOT  # noqa: E402


DEFAULT_CONFIG_PATH = SCRIPT_ROOT / "cleanup_paths.json"
DEFAULT_CONFIG = {
    "artifacts": {
        "build_dir": "build",
        "dist_dir": "dist",
        "release_bundle_dir": "dist/release_bundle",
        "release_bundle_staging_dir": "dist/release_bundle/_staging",
    },
    "cleanup_after_build": {
        "default": [
            "build",
            ".pytest_tmp*",
            "tests/.cache",
            "docs/effect_examples/.cache",
            "tools/PySide6TestApp/.cache",
            "tools/effect_building/build/.cache",
            "tools/effect_building/build/_generated",
            "tools/effect_building/build/build_lefx",
            "tools/effect_building/build/build_lefxset",
            "tools/effect_building/build/sources",
            "__pycache__",
            "src/**/__pycache__",
            "tests/**/__pycache__",
            "tools/**/__pycache__",
            "build-tools/**/__pycache__",
            "dist/release_bundle/_staging",
            "dist/*.log",
            "dist/logs",
            "dist/release_bundle/*.log",
            "logs",
        ],
        "complete": [
            "dist/*.exe",
            "dist/release_bundle/*.zip",
        ],
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Remove generated build artifacts while preserving the deliverables by default.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--complete", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def cleanup_after_build(
    *,
    config_path: Path,
    complete: bool,
    dry_run: bool,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, object]:
    project_root = project_root.resolve()
    created_config = False
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")
        created_config = True

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Cleanup config must be a JSON object: {config_path}")

    cleanup_section = payload.get("cleanup_after_build", {})
    if not isinstance(cleanup_section, dict):
        raise ValueError("cleanup_after_build section must be a JSON object")

    patterns = list(_coerce_patterns(cleanup_section.get("default", [])))
    if complete:
        patterns.extend(_coerce_patterns(cleanup_section.get("complete", [])))

    targets = _collect_targets(project_root, patterns)
    removed: list[str] = []
    if not dry_run:
        for target in sorted(targets, key=lambda path: (path.is_file(), len(path.parts)), reverse=True):
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=False)
            else:
                target.unlink(missing_ok=True)
            removed.append(target.relative_to(project_root).as_posix())

    return {
        "ok": True,
        "created_config": created_config,
        "mode": "dry-run" if dry_run else ("complete" if complete else "default"),
        "config_path": str(config_path),
        "targets": [path.relative_to(project_root).as_posix() for path in targets],
        "removed": removed,
    }


def _coerce_patterns(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("cleanup path lists must be arrays of strings")
    patterns: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("cleanup path entries must be non-empty strings")
        patterns.append(item)
    return patterns


def _collect_targets(project_root: Path, patterns: list[str]) -> list[Path]:
    targets: list[Path] = []
    seen: set[str] = set()
    for pattern in patterns:
        matches = sorted(project_root.glob(pattern))
        if not matches:
            candidate = project_root / pattern
            matches = [candidate] if candidate.exists() else []
        for match in matches:
            resolved = match.resolve()
            if project_root not in resolved.parents and resolved != project_root:
                raise ValueError(f"Refusing to delete path outside the project root: {resolved}")
            key = str(resolved)
            if key in seen:
                continue
            seen.add(key)
            targets.append(resolved)
    return targets


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = cleanup_after_build(
        config_path=Path(args.config).resolve(),
        complete=args.complete,
        dry_run=args.dry_run,
    )
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
