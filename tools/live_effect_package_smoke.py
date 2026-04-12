from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from src.core.effect_schema import LayerId
from src.services.service import ControllerService


BUILD_ROOT = PROJECT_ROOT / "build" / "live_effect_package_smoke"
SOURCE_ROOT = BUILD_ROOT / "source"
PACKAGE_PATH = BUILD_ROOT / "live_demo.lefxset"


class RecordingAdapter:
    def __init__(self) -> None:
        self.frames: list[list[int]] = []
        self.closed = False

    def apply_frame(self, frame) -> None:
        self.frames.append(list(frame.leds))

    def close(self) -> None:
        self.closed = True


def main() -> int:
    _reset_build_root()
    _write_demo_source_tree()
    _run_packager("pack-effect-set", str(SOURCE_ROOT), str(PACKAGE_PATH))
    inspect_payload = _run_packager("inspect-effect-package", str(PACKAGE_PATH))
    verify_payload = _run_packager("verify-effect-package", str(PACKAGE_PATH))

    adapter = RecordingAdapter()
    service = ControllerService(use_device=False, adapter_factory=lambda: adapter)
    summary: dict[str, object] = {
        "package": str(PACKAGE_PATH),
        "inspect": inspect_payload,
        "verify": verify_payload,
        "commands": [],
        "sources": [],
        "effects": [],
        "frame_count": 0,
    }

    try:
        service.start()
        registration = service.register_effect_source(str(PACKAGE_PATH))
        summary["sources"] = registration["items"]
        summary["effects"] = service.list_effects()
        commands = service.list_effect_commands("app.live_demo")
        summary["registered_command_names"] = [item["command_name"] for item in commands]

        state_commands = [
            ("state_idle", LayerId.STATE_LAYER),
            ("state_recording", LayerId.STATE_LAYER),
            ("state_processing", LayerId.STATE_LAYER),
        ]
        overlay_commands = [
            ("overlay_direction", LayerId.ONGOING_OVERLAY_LAYER),
            ("overlay_focus", LayerId.ONGOING_OVERLAY_LAYER),
            ("overlay_warning", LayerId.ONGOING_OVERLAY_LAYER),
        ]
        event_commands = [
            ("event_ping", LayerId.EVENT_LAYER),
            ("event_error", LayerId.EVENT_LAYER),
            ("event_timeout", LayerId.EVENT_LAYER),
        ]

        for command_name, layer_id in state_commands + overlay_commands:
            on_snapshot = service.invoke_effect_command("app.live_demo", command_name, state="on")
            time.sleep(0.05)
            on_invocation = service.runtime.store.layer(layer_id).state.active_invocation
            if on_invocation is None:
                raise RuntimeError(f"Command {command_name!r} did not activate layer {layer_id.value}")
            summary["commands"].append(
                {
                    "command": command_name,
                    "phase": "on",
                    "layer": layer_id.value,
                    "effect_id": on_invocation.effect_id,
                    "snapshot_has_frame": on_snapshot["last_frame"] is not None,
                }
            )

            off_snapshot = service.invoke_effect_command("app.live_demo", command_name, state="off")
            time.sleep(0.05)
            off_invocation = service.runtime.store.layer(layer_id).state.active_invocation
            if off_invocation is not None:
                raise RuntimeError(f"Command {command_name!r} did not clear layer {layer_id.value}")
            summary["commands"].append(
                {
                    "command": command_name,
                    "phase": "off",
                    "layer": layer_id.value,
                    "effect_id": None,
                    "snapshot_has_frame": off_snapshot["last_frame"] is not None,
                }
            )

        for command_name, layer_id in event_commands:
            event_snapshot = service.invoke_effect_command("app.live_demo", command_name)
            time.sleep(0.05)
            event_invocation = service.runtime.store.layer(layer_id).state.active_invocation
            if event_invocation is None:
                raise RuntimeError(f"Event command {command_name!r} did not activate the event layer")
            summary["commands"].append(
                {
                    "command": command_name,
                    "phase": "trigger",
                    "layer": layer_id.value,
                    "effect_id": event_invocation.effect_id,
                    "snapshot_event": event_snapshot["event_overlay"]["current"]["name"] if event_snapshot["event_overlay"]["current"] else None,
                }
            )

        summary["frame_count"] = len(adapter.frames)
        summary["last_frame"] = adapter.frames[-1] if adapter.frames else []
    finally:
        service.stop()

    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


def _reset_build_root() -> None:
    if BUILD_ROOT.exists():
        shutil.rmtree(BUILD_ROOT)
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)


def _run_packager(*args: str) -> dict:
    process = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "tools" / "effect_packager.py"), *args],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(PROJECT_ROOT),
    )
    text = process.stdout.strip()
    return {} if not text else json.loads(text)


def _write_demo_source_tree() -> None:
    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    effects_root = SOURCE_ROOT / "effects"
    effects_root.mkdir(parents=True, exist_ok=True)

    state_effects = [
        ("state_idle", "STATE_LAYER", "0x224466", 0),
        ("state_recording", "STATE_LAYER", "0x11AA55", 1),
        ("state_processing", "STATE_LAYER", "0xDD9933", 2),
    ]
    overlay_effects = [
        ("overlay_direction", "ONGOING_OVERLAY_LAYER", "0x55CCFF", 0),
        ("overlay_focus", "ONGOING_OVERLAY_LAYER", "0xFF66CC", 3),
        ("overlay_warning", "ONGOING_OVERLAY_LAYER", "0xFFFFFF", 6),
    ]
    event_effects = [
        ("event_ping", "EVENT_LAYER", "0x33D1FF", 0),
        ("event_error", "EVENT_LAYER", "0xFF3B30", 1),
        ("event_timeout", "EVENT_LAYER", "0xFF9F1A", 2),
    ]

    for effect_id, layer_name, color, marker_offset in state_effects + overlay_effects + event_effects:
        _write_effect_source(
            effects_root / effect_id,
            effect_id=effect_id,
            layer_name=layer_name,
            color=color,
            marker_offset=marker_offset,
        )

    (SOURCE_ROOT / "set.yaml").write_text(
        "\n".join(
            [
                "set_id: live_demo",
                "source_id: app.live_demo",
                "title: Live Demo Package",
                "version: 1",
                "min_service_version: 1.0.0",
                "effects:",
                *[f"  - {effect_id}" for effect_id, _, _, _ in state_effects + overlay_effects + event_effects],
            ]
        ),
        encoding="utf-8",
    )


def _write_effect_source(root: Path, *, effect_id: str, layer_name: str, color: str, marker_offset: int) -> None:
    class_name = "".join(part.capitalize() for part in effect_id.split("_")) + "Effect"
    root.mkdir(parents=True, exist_ok=True)
    (root / "effect.yaml").write_text(
        "\n".join(
            [
                f"package_id: live_demo.{effect_id}",
                "source_id: app.live_demo",
                f"entry_class: {class_name}",
                "min_service_version: 1.0.0",
            ]
        ),
        encoding="utf-8",
    )
    (root / "effect.py").write_text(
        _effect_code(
            class_name=class_name,
            effect_id=effect_id,
            layer_name=layer_name,
            color=color,
            marker_offset=marker_offset,
        ),
        encoding="utf-8",
    )
    (root / "effect-presets.yaml").write_text(
        _effect_presets_yaml(
            effect_id=effect_id,
            layer_name=layer_name,
            color=color,
        ),
        encoding="utf-8",
    )
    (root / "commands.json").write_text(
        json.dumps({"commands": {effect_id: _command_payload(effect_id=effect_id, layer_name=layer_name)}}, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _effect_code(*, class_name: str, effect_id: str, layer_name: str, color: str, marker_offset: int) -> str:
    if layer_name == "STATE_LAYER":
        render_body = "return [base_color] * ctx.led_count"
        playback_modes = "(PlaybackMode.LOOP, PlaybackMode.PERSISTENT)"
    elif layer_name == "ONGOING_OVERLAY_LAYER":
        render_body = "\n".join(
            [
                "leds = [None] * ctx.led_count",
                f"leds[{marker_offset} % ctx.led_count] = base_color",
                f"leds[({marker_offset} + 1) % ctx.led_count] = base_color",
                "return leds",
            ]
        )
        playback_modes = "(PlaybackMode.LOOP, PlaybackMode.PERSISTENT)"
    else:
        render_body = "\n".join(
            [
                f"phase = int(ctx.now * 12 + {marker_offset}) % 2",
                "current = base_color if phase == 0 else 0",
                "return [current] * ctx.led_count",
            ]
        )
        playback_modes = "(PlaybackMode.SINGLE_RUN,)"

    return "\n".join(
        [
            "from src.core.effect_schema import BaseEffect, EffectCapabilities, EffectDefinition, EffectParamDefinition, LayerId, LayerRule, PlaybackMode, RenderContext",
            "",
            "",
            f"class {class_name}(BaseEffect):",
            "    definition = EffectDefinition(",
            f'        id="{effect_id}",',
            f'        title="{class_name}",',
            '        description="Live smoke-test effect",',
            "        parameter_schema={",
            f'            "color": EffectParamDefinition(name="color", type="color", default="{color}"),',
            "        },",
            f'        defaults={{"color": "{color}"}},',
            "        capabilities=EffectCapabilities(",
            f"            playback_modes={playback_modes},",
            f'            restorable={str(layer_name != "EVENT_LAYER")},',
            "        ),",
            "        layer_rules={",
            f"            LayerId.{layer_name}: LayerRule(",
            "                allowed=True,",
            f"                allowed_playback_modes={playback_modes},",
            f'                requires_finite_duration={str(layer_name == "EVENT_LAYER")},',
            "            ),",
            "        },",
            "    )",
            "",
            "    def render(self, ctx: RenderContext) -> list[int | None]:",
            f'        raw_color = str(ctx.params.get("color", "{color}")).replace("#", "0x")',
            "        base_color = int(raw_color, 16)",
            *[f"        {line}" for line in render_body.splitlines()],
            "",
        ]
    )


def _effect_presets_yaml(*, effect_id: str, layer_name: str, color: str) -> str:
    category = _preset_category_for_layer(layer_name)
    lines = [
        "presets:",
        f"  {effect_id}_default:",
        f"    title: {json.dumps(effect_id.replace('_', ' ').title(), ensure_ascii=True)}",
        f"    category: {category}",
        f"    target_layer: {layer_name}",
    ]
    if category == "event":
        lines.append("    duration_ms: 450")
    lines.extend(
        [
            "    params:",
            f"      color: {json.dumps(color, ensure_ascii=True)}",
            "    tags:",
            f"      - {category}",
            "",
        ]
    )
    return "\n".join(lines)


def _preset_category_for_layer(layer_name: str) -> str:
    if layer_name in {"STATE_LAYER", "BACKGROUND_STATE_LAYER"}:
        return "state"
    if layer_name in {"ONGOING_OVERLAY_LAYER", "TEMP_OVERLAY_LAYER"}:
        return "overlay"
    if layer_name == "EVENT_LAYER":
        return "event"
    return "effect"


def _toggle_command(preset_id: str, target_layer: str) -> dict:
    return {
        "kind": "state_toggle",
        "on": {
            "preset": preset_id,
        },
        "off": {
            "action": "clear_layer",
            "target_layer": target_layer,
        },
    }


def _event_command(preset_id: str) -> dict:
    return {
        "kind": "event",
        "on": {
            "preset": preset_id,
        },
    }


def _command_payload(*, effect_id: str, layer_name: str) -> dict:
    category = _preset_category_for_layer(layer_name)
    preset_id = f"{effect_id}_default"
    if category == "event":
        return _event_command(preset_id)
    return _toggle_command(preset_id, layer_name)


if __name__ == "__main__":
    raise SystemExit(main())
