from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from respeaker_led.engine.effect_package_builder import (
    build_effect_package,
    build_effect_set,
    init_effect_batch,
    init_effect_set_source,
    init_effect_source,
    validate_effect_set_source,
    validate_effect_source,
)
from respeaker_led.engine.effect_package_loader import inspect_effect_source, verify_effect_source


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and inspect packaged LED effect artifacts")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_effect = subparsers.add_parser("init-effect", help="Create a scaffold for a single effect source")
    init_effect.add_argument("target_dir")
    init_effect.add_argument("--effect-id", required=True)
    init_effect.add_argument("--source-id", required=True)
    init_effect.add_argument("--title")
    init_effect.add_argument("--package-id")
    init_effect.add_argument("--class-name")
    init_effect.add_argument("--type", dest="definition_type", choices=("state", "overlay", "event"), default="state")
    init_effect.add_argument("--overlay-mode", choices=("controlled", "timed"))
    init_effect.add_argument("--format", choices=("yaml", "json"), default="yaml")
    init_effect.add_argument("--force", action="store_true")
    init_effect.set_defaults(command_kind="init_effect")

    init_set = subparsers.add_parser("init-effect-set", help="Create a scaffold for an effect set source")
    init_set.add_argument("target_dir")
    init_set.add_argument("--set-id", required=True)
    init_set.add_argument("--source-id", required=True)
    init_set.add_argument("--title")
    init_set.add_argument("--format", choices=("yaml", "json"), default="yaml")
    init_set.add_argument("--force", action="store_true")
    init_set.set_defaults(command_kind="init_effect_set")

    init_batch = subparsers.add_parser("init-effect-batch", help="Create multiple effect source scaffolds from a batch JSON file")
    init_batch.add_argument("batch_file")
    init_batch.add_argument("output_root")
    init_batch.add_argument("--force", action="store_true")
    init_batch.set_defaults(command_kind="init_effect_batch")

    validate_effect = subparsers.add_parser("validate-effect-source", help="Validate an effect source directory")
    validate_effect.add_argument("source_dir")
    validate_effect.set_defaults(command_kind="validate_effect_source")

    validate_set = subparsers.add_parser("validate-effect-set-source", help="Validate an effect set source directory")
    validate_set.add_argument("source_dir")
    validate_set.set_defaults(command_kind="validate_effect_set_source")

    pack_effect = subparsers.add_parser("pack-effect", help="Build a .lefx package from an effect source directory")
    pack_effect.add_argument("source_dir")
    pack_effect.add_argument("output_file")
    pack_effect.set_defaults(command_kind="pack_effect")

    pack_effect_set = subparsers.add_parser("pack-effect-set", help="Build a .lefxset package from an effect set source directory")
    pack_effect_set.add_argument("source_dir")
    pack_effect_set.add_argument("output_file")
    pack_effect_set.set_defaults(command_kind="pack_effect_set")

    inspect_parser = subparsers.add_parser("inspect-effect-package", help="Inspect a .lefx or .lefxset package")
    inspect_parser.add_argument("package_file")
    inspect_parser.set_defaults(command_kind="inspect")

    verify_parser = subparsers.add_parser("verify-effect-package", help="Verify a .lefx or .lefxset package")
    verify_parser.add_argument("package_file")
    verify_parser.set_defaults(command_kind="verify")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command_kind == "init_effect":
        result = init_effect_source(
            args.target_dir,
            effect_id=args.effect_id,
            source_id=args.source_id,
            title=args.title,
            package_id=args.package_id,
            class_name=args.class_name,
            definition_type=args.definition_type,
            overlay_mode=args.overlay_mode,
            format_name=args.format,
            force=args.force,
        )
        print(json.dumps({
            "ok": True,
            "kind": result.kind,
            "target_path": str(result.target_path),
            "created_files": list(result.created_files),
        }, ensure_ascii=True, indent=2, sort_keys=True))
        return 0

    if args.command_kind == "init_effect_set":
        result = init_effect_set_source(
            args.target_dir,
            set_id=args.set_id,
            source_id=args.source_id,
            title=args.title,
            format_name=args.format,
            force=args.force,
        )
        print(json.dumps({
            "ok": True,
            "kind": result.kind,
            "target_path": str(result.target_path),
            "created_files": list(result.created_files),
        }, ensure_ascii=True, indent=2, sort_keys=True))
        return 0

    if args.command_kind == "init_effect_batch":
        results = init_effect_batch(args.batch_file, args.output_root, force=args.force)
        print(json.dumps({
            "ok": True,
            "kind": "effect_batch",
            "count": len(results),
            "results": [
                {
                    "kind": result.kind,
                    "target_path": str(result.target_path),
                    "created_files": list(result.created_files),
                }
                for result in results
            ],
        }, ensure_ascii=True, indent=2, sort_keys=True))
        return 0

    if args.command_kind == "validate_effect_source":
        result = validate_effect_source(args.source_dir)
        print(json.dumps({
            "ok": True,
            "kind": result.kind,
            "identifier": result.identifier,
            "source_id": result.source_id,
            "warnings": list(result.warnings),
            "details": dict(result.details),
        }, ensure_ascii=True, indent=2, sort_keys=True))
        return 0

    if args.command_kind == "validate_effect_set_source":
        result = validate_effect_set_source(args.source_dir)
        print(json.dumps({
            "ok": True,
            "kind": result.kind,
            "identifier": result.identifier,
            "source_id": result.source_id,
            "warnings": list(result.warnings),
            "details": dict(result.details),
        }, ensure_ascii=True, indent=2, sort_keys=True))
        return 0

    if args.command_kind == "pack_effect":
        artifact = build_effect_package(args.source_dir, args.output_file)
        print(json.dumps({
            "ok": True,
            "kind": artifact.kind,
            "identifier": artifact.identifier,
            "output_path": str(artifact.output_path),
            "warnings": list(artifact.warnings),
        }, ensure_ascii=True, indent=2, sort_keys=True))
        return 0

    if args.command_kind == "pack_effect_set":
        artifact = build_effect_set(args.source_dir, args.output_file)
        print(json.dumps({
            "ok": True,
            "kind": artifact.kind,
            "identifier": artifact.identifier,
            "output_path": str(artifact.output_path),
            "warnings": list(artifact.warnings),
        }, ensure_ascii=True, indent=2, sort_keys=True))
        return 0

    if args.command_kind == "inspect":
        print(json.dumps(inspect_effect_source(args.package_file), ensure_ascii=True, indent=2, sort_keys=True))
        return 0

    if args.command_kind == "verify":
        result = verify_effect_source(args.package_file)
        print(json.dumps({
            "ok": result.ok,
            "kind": result.kind,
            "source_id": result.source_id,
            "package_id": result.package_id,
            "set_id": result.set_id,
            "effect_ids": list(result.effect_ids),
            "preset_ids": list(result.preset_ids),
        }, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result.ok else 1

    parser.error(f"Unsupported command kind: {args.command_kind}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
