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

from .effect_set_builder import (
    build_all_effect_packages,
    build_all_effect_sets,
    cleanup_effect_build_cache,
)
from .effect_set_sources import (
    DEFAULT_BUILD_CACHE_ROOT,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_PACKAGE_CACHE_ROOT,
    DEFAULT_PUBLISH_ROOT,
    DEFAULT_SOURCES_ROOT,
    discover_effect_sets,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build every discovered .lefxset from prebuilt .lefx packages"
    )
    parser.add_argument("--sources-root", default=str(DEFAULT_SOURCES_ROOT))
    parser.add_argument("--packages-root", default=str(DEFAULT_PACKAGE_CACHE_ROOT))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--publish-root", default=str(DEFAULT_PUBLISH_ROOT))
    parser.add_argument("--rebuild-packages", action="store_true")
    parser.add_argument("--keep-cache", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    sources_root = Path(args.sources_root)
    package_root = Path(args.packages_root)
    output_root = Path(args.output_root)
    publish_root = None if not args.publish_root else Path(args.publish_root)

    if args.rebuild_packages:
        build_all_effect_packages(
            sources_root=sources_root,
            package_cache_root=package_root,
        )

    sets = discover_effect_sets(sources_root)
    built_sets = build_all_effect_sets(
        sources_root=sources_root,
        package_cache_root=package_root,
        output_root=output_root,
        publish_root=publish_root,
    )

    cache_cleaned = False
    if (
        not args.keep_cache
        and package_root.resolve() == DEFAULT_PACKAGE_CACHE_ROOT.resolve()
        and output_root.resolve() == DEFAULT_OUTPUT_ROOT.resolve()
    ):
        cleanup_effect_build_cache(DEFAULT_BUILD_CACHE_ROOT)
        cache_cleaned = True

    set_payloads = {}
    effect_count = 0
    for effect_set in sets:
        effect_set_path = built_sets[effect_set.set_id]
        loaded = None
        set_effect_count = 0
        if effect_set_path.is_file():
            from respeaker_led.engine.effect_package_loader import load_effect_set

            loaded = load_effect_set(effect_set_path)
            set_effect_count = len(loaded.effects)
        effect_count += set_effect_count
        publish_copy = None
        if publish_root is not None:
            candidate = publish_root / f"{effect_set.set_id}.lefxset"
            if candidate.is_file():
                publish_copy = str(candidate)
        set_payloads[effect_set.set_id] = {
            "effect_set": str(effect_set_path),
            "publish_copy": publish_copy,
            "effect_count": set_effect_count,
        }

    payload = {
        "ok": True,
        "kind": "lefxset_build",
        "set_count": len(sets),
        "effect_count": effect_count,
        "sets": set_payloads,
        "cache_cleaned": cache_cleaned,
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
