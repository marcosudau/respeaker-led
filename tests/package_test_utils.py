from __future__ import annotations

import json
import textwrap
from pathlib import Path


def write_effect_source(
    root: Path,
    *,
    package_id: str,
    source_id: str,
    class_name: str,
    effect_id: str,
    layer_name: str = "MAIN_LAYER",
    color: str = "0x224466",
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "effect.yaml").write_text(
        "\n".join(
            [
                f"package_id: {package_id}",
                f"source_id: {source_id}",
                f"entry_class: {class_name}",
                "min_service_version: 1.0.0",
            ]
        ),
        encoding="utf-8",
    )
    (root / "effect.py").write_text(
        textwrap.dedent(
            f"""
            from src.core.effect_schema import BaseEffect, EffectDefinition, LayerId, LayerRule, PlaybackMode, EffectCapabilities, RenderContext


            class {class_name}(BaseEffect):
                definition = EffectDefinition(
                    id="{effect_id}",
                    title="{class_name}",
                    description="Generated for tests",
                    defaults={{"color": "{color}"}},
                    capabilities=EffectCapabilities(
                        playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                        restorable=True,
                    ),
                    layer_rules={{
                        LayerId.{layer_name}: LayerRule(
                            allowed=True,
                            allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                        ),
                    }},
                )

                def render(self, ctx: RenderContext) -> list[int | None]:
                    return [int(str(ctx.params.get("color", "{color}")).replace("#", "0x"), 16)] * ctx.led_count
            """
        ),
        encoding="utf-8",
    )


def write_effect_set_source(
    root: Path,
    *,
    source_id: str,
    set_id: str,
    title: str,
    effects: list[dict],
    commands: dict,
) -> None:
    effects_root = root / "effects"
    effects_root.mkdir(parents=True, exist_ok=True)
    for effect in effects:
        write_effect_source(
            effects_root / effect["dir_name"],
            package_id=effect["package_id"],
            source_id=source_id,
            class_name=effect["class_name"],
            effect_id=effect["effect_id"],
            layer_name=effect.get("layer_name", "MAIN_LAYER"),
            color=effect.get("color", "0x224466"),
        )
    (root / "set.yaml").write_text(
        "\n".join(
            [
                f"set_id: {set_id}",
                f"source_id: {source_id}",
                f"title: {title}",
                "version: 1",
                "min_service_version: 1.0.0",
                "effects:",
                *[f"  - {effect['dir_name']}" for effect in effects],
            ]
        ),
        encoding="utf-8",
    )
    (root / "commands.json").write_text(
        json.dumps({"commands": commands}, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )
