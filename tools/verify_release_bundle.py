from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_RELATIVE_PATHS = (
    Path("led_controller_service.exe"),
    Path("effects") / "default-effects.lefxset",
    Path("docs") / "HOST_APP_INTEGRATION.md",
    Path("docs") / "REFERENCE.md",
    Path("examples") / "led_controller_host.py",
    Path("examples") / "example_usage.py",
    Path("README.md"),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify the assembled release bundle structure and required artefacts.")
    parser.add_argument("bundle_root")
    return parser


def verify_release_bundle(bundle_root: Path) -> dict:
    root = bundle_root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Release bundle directory does not exist: {root}")

    missing = [path.as_posix() for path in REQUIRED_RELATIVE_PATHS if not (root / path).exists()]
    if missing:
        joined = ", ".join(missing)
        raise FileNotFoundError(f"Release bundle is missing required files: {joined}")

    effect_artifacts = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".lefx", ".lefxset"}
    )
    return {
        "ok": True,
        "bundle_root": str(root),
        "effect_artifacts": effect_artifacts,
        "required_paths": [path.as_posix() for path in REQUIRED_RELATIVE_PATHS],
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    result = verify_release_bundle(Path(args.bundle_root))
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())