from __future__ import annotations

import argparse
import json
from pathlib import Path
from zipfile import ZipFile


REQUIRED_RELATIVE_PATHS = (
    Path("effects") / "default-effects.lefxset",
    Path("docs") / "HOST_APP_INTEGRATION.md",
    Path("docs") / "REFERENCE.md",
    Path("examples") / "led_controller_host.py",
    Path("examples") / "example_usage.py",
    Path("README.md"),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify the assembled release bundle structure and required artifacts.")
    parser.add_argument("bundle_path")
    return parser


def verify_release_bundle(bundle_path: Path) -> dict[str, object]:
    bundle_path = bundle_path.resolve()
    if bundle_path.suffix.lower() == ".zip":
        return _verify_release_bundle_zip(bundle_path)
    if bundle_path.is_dir():
        return _verify_release_bundle_directory(bundle_path)
    raise FileNotFoundError(f"Release bundle path does not exist: {bundle_path}")


def _verify_release_bundle_directory(bundle_root: Path) -> dict[str, object]:
    missing = [path.as_posix() for path in REQUIRED_RELATIVE_PATHS if not (bundle_root / path).exists()]
    exe_paths = list(bundle_root.glob("*.exe"))
    if not exe_paths:
        missing.append("*.exe")
    if missing:
        raise FileNotFoundError(f"Release bundle is missing required files: {', '.join(sorted(missing))}")
    return {
        "ok": True,
        "bundle_root": str(bundle_root),
        "exe_name": exe_paths[0].name,
        "effect_artifacts": sorted(
            path.relative_to(bundle_root).as_posix()
            for path in bundle_root.rglob("*")
            if path.is_file() and path.suffix.lower() in {".lefx", ".lefxset"}
        ),
    }


def _verify_release_bundle_zip(zip_path: Path) -> dict[str, object]:
    if not zip_path.is_file():
        raise FileNotFoundError(f"Release bundle zip does not exist: {zip_path}")
    with ZipFile(zip_path) as archive:
        file_names = [name for name in archive.namelist() if not name.endswith("/")]
    if not file_names:
        raise FileNotFoundError(f"Release bundle zip is empty: {zip_path}")

    top_level = sorted({Path(name).parts[0] for name in file_names})
    if len(top_level) != 1:
        raise ValueError(f"Release bundle zip must contain exactly one top-level directory: {zip_path}")
    root_name = top_level[0]
    normalized = {Path(name).relative_to(root_name).as_posix() for name in file_names}

    missing = [path.as_posix() for path in REQUIRED_RELATIVE_PATHS if path.as_posix() not in normalized]
    exe_names = sorted(path for path in normalized if path.lower().endswith(".exe") and "/" not in path)
    if not exe_names:
        missing.append("*.exe")
    if missing:
        raise FileNotFoundError(f"Release bundle is missing required files: {', '.join(sorted(missing))}")

    return {
        "ok": True,
        "archive_path": str(zip_path),
        "bundle_root": root_name,
        "exe_name": exe_names[0],
        "effect_artifacts": sorted(
            path for path in normalized if path.endswith(".lefx") or path.endswith(".lefxset")
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = verify_release_bundle(Path(args.bundle_path))
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
