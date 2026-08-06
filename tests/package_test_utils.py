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
    layer_name: str = "STATE_LAYER",
    color: str = "0x224466",
    presets: dict | None = None,
    commands: dict | None = None,
) -> None:
    if layer_name in {"BACKGROUND_STATE_LAYER", "STATE_LAYER"}:
        definition_type = "DefinitionType.STATE"
        overlay_mode = ""
        duration_param = ""
        duration_default = ""
        finite_rule = "requires_indefinite_duration=True,"
    elif layer_name == "EVENT_LAYER":
        definition_type = "DefinitionType.EVENT"
        overlay_mode = ""
        duration_param = '"duration_ms": EffectParamDefinition(name="duration_ms", type="duration_ms", default=250, minimum=1),'
        duration_default = ', "duration_ms": 250'
        finite_rule = "requires_finite_duration=True,"
    else:
        definition_type = "DefinitionType.OVERLAY"
        mode = "TIMED" if layer_name == "TEMP_OVERLAY_LAYER" else "CONTROLLED"
        overlay_mode = f"overlay_mode=OverlayMode.{mode},"
        duration_param = (
            '"total_ms": EffectParamDefinition(name="total_ms", type="duration_ms", default=1000, minimum=1),'
            if mode == "TIMED"
            else ""
        )
        duration_default = ', "total_ms": 1000' if mode == "TIMED" else ""
        finite_rule = (
            "requires_finite_duration=True,"
            if mode == "TIMED"
            else "requires_indefinite_duration=True,"
        )
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
            from respeaker_led.core.effect_schema import BaseEffect, ColorModel, DefinitionType, EffectDefinition, EffectParamDefinition, LayerId, LayerRule, OverlayMode, PlaybackMode, EffectCapabilities, RenderContext


            class {class_name}(BaseEffect):
                definition = EffectDefinition(
                    id="{effect_id}",
                    title="{class_name}",
                    description="Generated for tests",
                    definition_type={definition_type},
                    {overlay_mode}
                    parameter_schema={{
                        "color": EffectParamDefinition(name="color", type="color", default="{color}"),
                        "brightness": EffectParamDefinition(name="brightness", type="float", default=1.0, minimum=0.0, maximum=1.0),
                        {duration_param}
                    }},
                    defaults={{"color": "{color}", "brightness": 1.0{duration_default}}},
                    capabilities=EffectCapabilities(
                        playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                        restorable=True,
                    ),
                    layer_rules={{
                        LayerId.{layer_name}: LayerRule(
                            allowed=True,
                            allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                            {finite_rule}
                        ),
                    }},
                    color_model=ColorModel.MONO,
                )

                def render(self, ctx: RenderContext) -> list[int | None]:
                    return [int(str(ctx.params.get("color", "{color}")).replace("#", "0x"), 16)] * ctx.led_count
            """
        ),
        encoding="utf-8",
    )
    if presets is not None:
        (root / "presets.yaml").write_text(
            _dump_simple_yaml({"presets": presets}),
            encoding="utf-8",
        )
    if commands is not None:
        (root / "commands.json").write_text(
            json.dumps({"commands": commands}, ensure_ascii=True, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def write_effect_set_source(
    root: Path,
    *,
    source_id: str,
    set_id: str,
    title: str,
    effects: list[dict],
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
            layer_name=effect.get("layer_name", "STATE_LAYER"),
            color=effect.get("color", "0x224466"),
            presets=effect.get("presets"),
            commands=effect.get("commands"),
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


def _dump_simple_yaml(payload: dict) -> str:
    lines: list[str] = []

    def _render(value, indent: int, key: str | None = None) -> None:
        prefix = " " * indent
        if isinstance(value, dict):
            if key is not None:
                lines.append(f"{prefix}{key}:")
            for nested_key, nested_value in value.items():
                _render(nested_value, indent + (2 if key is not None else 0), str(nested_key))
            return
        if isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, dict):
                    raise ValueError("List of mappings is not supported in test YAML helper")
                lines.append(f"{prefix}  - {_scalar(item)}")
            return
        lines.append(f"{prefix}{key}: {_scalar(value)}")

    for payload_key, payload_value in payload.items():
        _render(payload_value, 0, str(payload_key))
    return "\n".join(lines) + "\n"


def _scalar(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if any(ch in text for ch in '#:[]"\''):
        return json.dumps(text, ensure_ascii=True)
    return text
