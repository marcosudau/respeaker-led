from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


if __package__ in {None, ""}:
    _PROJECT_ROOT = Path(__file__).resolve().parents[2]
    _PROJECT_ROOT_STR = str(_PROJECT_ROOT)
    if _PROJECT_ROOT_STR not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT_STR)
    __package__ = "tools.effect_building"

from .effect_set_builder import build_all_effect_packages
from .effect_set_sources import DEFAULT_PACKAGE_CACHE_ROOT, DEFAULT_SOURCES_ROOT, discover_effect_sets


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover all effect sets and build standalone .lefx packages for every source"
    )
    parser.add_argument("--sources-root", default=str(DEFAULT_SOURCES_ROOT))
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_PACKAGE_CACHE_ROOT),
        help="Common package cache root; one subdirectory is created per set_id",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    sources_root = Path(args.sources_root)
    output_root = Path(args.output_root)
    sets = discover_effect_sets(sources_root)
    all_packages = build_all_effect_packages(
        sources_root=sources_root,
        package_cache_root=output_root,
    )

    set_payloads = {}
    effect_count = 0
    for effect_set in sets:
        packages = all_packages.get(effect_set.set_id, [])
        effect_count += len(packages)
        set_payloads[effect_set.set_id] = {
            "source_id": effect_set.source_id,
            "effect_count": len(packages),
            "effect_ids": [package_path.stem for package_path in packages],
            "packages": [str(package_path) for package_path in packages],
        }

    payload = {
        "ok": True,
        "kind": "lefx_build",
        "sources_root": str(sources_root),
        "output_root": str(output_root),
        "set_count": len(sets),
        "effect_count": effect_count,
        "sets": set_payloads,
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
