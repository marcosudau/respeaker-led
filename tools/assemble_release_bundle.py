from __future__ import annotations

import argparse
import json
import os
import stat
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_TEMPLATE_ROOT = PROJECT_ROOT / "release" / "led_controller_service_release_1"
SOURCE_EFFECTS_ROOT = PROJECT_ROOT / "src" / "led_effects" / "effects"
SOURCE_PACKAGES_ROOT = PROJECT_ROOT / "src" / "led_effects" / "packages"
ARTIFACT_SUFFIXES = {".lefx", ".lefxset"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assemble the distributable release bundle from the release template and a built EXE.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--exe", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--force", action="store_true")
    return parser


def _copy_effect_artifacts(source_root: Path, target_root: Path) -> list[str]:
    if not source_root.exists():
        return []

    copied: list[str] = []
    for source_path in sorted(source_root.rglob("*")):
        if not source_path.is_file() or source_path.suffix.lower() not in ARTIFACT_SUFFIXES:
            continue
        relative_path = source_path.relative_to(source_root)
        target_path = target_root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        copied.append(target_path.as_posix())
    return copied


def _remove_readonly(func, path, excinfo) -> None:
    del excinfo
    os.chmod(path, stat.S_IWRITE)
    func(path)


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
        shutil.rmtree(bundle_root, onexc=_remove_readonly)

    shutil.copytree(
        RELEASE_TEMPLATE_ROOT,
        bundle_root,
        ignore=shutil.ignore_patterns("led_controller_service.exe", "*.zip"),
    )
    shutil.copy2(exe_path, bundle_root / "led_controller_service.exe")

    copied_effects = _copy_effect_artifacts(SOURCE_EFFECTS_ROOT, bundle_root / "effects")
    copied_packages = _copy_effect_artifacts(SOURCE_PACKAGES_ROOT, bundle_root / "packages")
    default_effect_set_path = bundle_root / "effects" / "default-effects.lefxset"
    if not default_effect_set_path.is_file():
        raise FileNotFoundError(
            "Release bundle is missing effects/default-effects.lefxset. "
            "Run tools/effect_building/build_lefxset.py before assembling the release bundle."
        )

    manifest = {
        "version": normalized_version,
        "bundle_root": str(bundle_root),
        "effect_artifacts": [
            str(Path(path).relative_to(bundle_root).as_posix()) for path in [*copied_effects, *copied_packages]
        ],
    }
    (bundle_root / "bundle_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )
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
    manifest_path = bundle_root / "bundle_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(json.dumps({"ok": True, **manifest}, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())