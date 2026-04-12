from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_TEMPLATE_ROOT = PROJECT_ROOT / "release" / "led_controller_service_release_1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assemble the distributable release bundle from the release template and a built EXE.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--exe", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--force", action="store_true")
    return parser


def assemble_release_bundle(*, version: str, exe_path: Path, output_dir: Path, force: bool = False) -> Path:
    if not RELEASE_TEMPLATE_ROOT.exists():
        raise FileNotFoundError(f"Release template directory does not exist: {RELEASE_TEMPLATE_ROOT}")
    if not exe_path.exists():
        raise FileNotFoundError(f"Built executable does not exist: {exe_path}")

    normalized_version = str(version).strip().lstrip("v")
    bundle_root = output_dir.resolve() / f"led_controller_service_{normalized_version}_windows_x64"
    if bundle_root.exists():
        if not force:
            raise FileExistsError(f"Release bundle directory already exists: {bundle_root}")
        shutil.rmtree(bundle_root)

    shutil.copytree(
        RELEASE_TEMPLATE_ROOT,
        bundle_root,
        ignore=shutil.ignore_patterns("led_controller_service.exe", "*.zip"),
    )
    shutil.copy2(exe_path, bundle_root / "led_controller_service.exe")
    return bundle_root


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    bundle_root = assemble_release_bundle(
        version=args.version,
        exe_path=Path(args.exe),
        output_dir=Path(args.output_dir),
        force=args.force,
    )
    print(json.dumps({"ok": True, "bundle_root": str(bundle_root)}, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())