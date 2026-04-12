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


BUILD_ROOT = PROJECT_ROOT / "build" / "effect_authoring_smoke"
BATCH_FILE = BUILD_ROOT / "batch.json"
GENERATED_ROOT = BUILD_ROOT / "generated_effects"
SET_ROOT = BUILD_ROOT / "demo_set"
DIST_ROOT = BUILD_ROOT / "dist"
PACKAGE_PATH = DIST_ROOT / "authoring_demo.lefxset"
SOURCE_ID = "app.authoring_demo"


class RecordingAdapter:
    def __init__(self) -> None:
        self.frames: list[list[int]] = []

    def apply_frame(self, frame) -> None:
        self.frames.append(list(frame.leds))

    def close(self) -> None:
        return None


def main() -> int:
    _reset_build_root()
    _write_batch_definition()
    batch_payload = _run_packager("init-effect-batch", str(BATCH_FILE), str(GENERATED_ROOT))
    _customize_generated_effects()

    built_effects: dict[str, str] = {}
    for effect_id in ("state_idle", "overlay_focus", "event_ping"):
        source_dir = GENERATED_ROOT / effect_id
        validate_payload = _run_packager("validate-effect-source", str(source_dir))
        if validate_payload["identifier"] != f"{SOURCE_ID}::{effect_id}":
            raise RuntimeError(f"Unexpected validation identifier for {effect_id}: {validate_payload}")
        output_file = DIST_ROOT / f"{effect_id}.lefx"
        build_payload = _run_packager("pack-effect", str(source_dir), str(output_file))
        built_effects[effect_id] = str(output_file)
        if build_payload["warnings"]:
            raise RuntimeError(f"Unexpected warnings while building {effect_id}: {build_payload['warnings']}")

    _initialize_set_source()
    _populate_set_source()
    set_validation = _run_packager("validate-effect-set-source", str(SET_ROOT))
    pack_set_payload = _run_packager("pack-effect-set", str(SET_ROOT), str(PACKAGE_PATH))
    inspect_payload = _run_packager("inspect-effect-package", str(PACKAGE_PATH))
    verify_payload = _run_packager("verify-effect-package", str(PACKAGE_PATH))

    adapter = RecordingAdapter()
    service = ControllerService(use_device=False, adapter_factory=lambda: adapter)
    summary: dict[str, object] = {
        "batch": batch_payload,
        "built_effects": built_effects,
        "set_validation": set_validation,
        "pack_set": pack_set_payload,
        "inspect": inspect_payload,
        "verify": verify_payload,
        "package": str(PACKAGE_PATH),
        "commands": [],
        "registered_sources": [],
        "registered_effects": [],
        "frame_count": 0,
    }

    try:
        service.start()
        registration = service.register_effect_source(str(PACKAGE_PATH))
        summary["registered_sources"] = registration["items"]
        summary["registered_effects"] = [
            item for item in service.list_effects()
            if item.get("source_id") == SOURCE_ID
        ]
        summary["registered_commands"] = [
            item["command_name"] for item in service.list_effect_commands(SOURCE_ID)
        ]

        state_snapshot = service.invoke_effect_command(SOURCE_ID, "state_idle", state="on")
        time.sleep(0.05)
        state_invocation = service.runtime.store.layer(LayerId.STATE_LAYER).state.active_invocation
        if state_invocation is None:
            raise RuntimeError("state_idle did not activate STATE_LAYER")
        summary["commands"].append(
            {
                "command": "state_idle",
                "phase": "on",
                "layer": LayerId.STATE_LAYER.value,
                "effect_id": state_invocation.effect_id,
                "snapshot_has_frame": state_snapshot["last_frame"] is not None,
            }
        )

        service.invoke_effect_command(SOURCE_ID, "state_idle", state="off")
        time.sleep(0.05)
        if service.runtime.store.layer(LayerId.STATE_LAYER).state.active_invocation is not None:
            raise RuntimeError("state_idle did not clear STATE_LAYER")
        summary["commands"].append(
            {
                "command": "state_idle",
                "phase": "off",
                "layer": LayerId.STATE_LAYER.value,
            }
        )

        overlay_snapshot = service.invoke_effect_command(SOURCE_ID, "overlay_focus", state="on")
        time.sleep(0.05)
        overlay_invocation = service.runtime.store.layer(LayerId.ONGOING_OVERLAY_LAYER).state.active_invocation
        if overlay_invocation is None:
            raise RuntimeError("overlay_focus did not activate ONGOING_OVERLAY_LAYER")
        summary["commands"].append(
            {
                "command": "overlay_focus",
                "phase": "on",
                "layer": LayerId.ONGOING_OVERLAY_LAYER.value,
                "effect_id": overlay_invocation.effect_id,
                "snapshot_has_frame": overlay_snapshot["last_frame"] is not None,
            }
        )

        service.invoke_effect_command(SOURCE_ID, "overlay_focus", state="off")
        time.sleep(0.05)
        if service.runtime.store.layer(LayerId.ONGOING_OVERLAY_LAYER).state.active_invocation is not None:
            raise RuntimeError("overlay_focus did not clear ONGOING_OVERLAY_LAYER")
        summary["commands"].append(
            {
                "command": "overlay_focus",
                "phase": "off",
                "layer": LayerId.ONGOING_OVERLAY_LAYER.value,
            }
        )

        event_snapshot = service.invoke_effect_command(SOURCE_ID, "event_ping")
        time.sleep(0.05)
        event_invocation = service.runtime.store.layer(LayerId.EVENT_LAYER).state.active_invocation
        if event_invocation is None:
            raise RuntimeError("event_ping did not activate EVENT_LAYER")
        summary["commands"].append(
            {
                "command": "event_ping",
                "phase": "trigger",
                "layer": LayerId.EVENT_LAYER.value,
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
    DIST_ROOT.mkdir(parents=True, exist_ok=True)


def _write_batch_definition() -> None:
    payload = {
        "source_id": SOURCE_ID,
        "effects": [
            {"effect_id": "state_idle", "title": "State Idle", "layer": "STATE_LAYER"},
            {"effect_id": "overlay_focus", "title": "Overlay Focus", "layer": "ONGOING_OVERLAY_LAYER"},
            {"effect_id": "event_ping", "title": "Event Ping", "layer": "EVENT_LAYER"},
        ],
    }
    BATCH_FILE.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")


def _customize_generated_effects() -> None:
    _customize_effect_source(
        effect_dir=GENERATED_ROOT / "state_idle",
        class_name="StateIdleEffect",
        effect_id="state_idle",
        title="State Idle",
        layer_name="STATE_LAYER",
        color="#224466",
        mode="state",
    )
    _customize_effect_source(
        effect_dir=GENERATED_ROOT / "overlay_focus",
        class_name="OverlayFocusEffect",
        effect_id="overlay_focus",
        title="Overlay Focus",
        layer_name="ONGOING_OVERLAY_LAYER",
        color="#FF66CC",
        mode="overlay",
    )
    _customize_effect_source(
        effect_dir=GENERATED_ROOT / "event_ping",
        class_name="EventPingEffect",
        effect_id="event_ping",
        title="Event Ping",
        layer_name="EVENT_LAYER",
        color="#33D1FF",
        mode="event",
    )


def _customize_effect_source(
    *,
    effect_dir: Path,
    class_name: str,
    effect_id: str,
    title: str,
    layer_name: str,
    color: str,
    mode: str,
) -> None:
    effect_dir.mkdir(parents=True, exist_ok=True)
    (effect_dir / "effect.py").write_text(
        _effect_code(
            class_name=class_name,
            effect_id=effect_id,
            title=title,
            layer_name=layer_name,
            color=color,
            mode=mode,
        ),
        encoding="utf-8",
    )
    (effect_dir / "effect-presets.yaml").write_text(
        _effect_presets_yaml(
            effect_id=effect_id,
            title=title,
            layer_name=layer_name,
            color=color,
        ),
        encoding="utf-8",
    )
    (effect_dir / "commands.json").write_text(
        json.dumps(
            {"commands": {effect_id: _command_definition(effect_id=effect_id, layer_name=layer_name)}},
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _initialize_set_source() -> None:
    _run_packager(
        "init-effect-set",
        str(SET_ROOT),
        "--set-id",
        "authoring_demo",
        "--source-id",
        SOURCE_ID,
        "--title",
        "Authoring Demo",
    )


def _populate_set_source() -> None:
    effects_root = SET_ROOT / "effects"
    for effect_id in ("state_idle", "overlay_focus", "event_ping"):
        package_path = DIST_ROOT / f"{effect_id}.lefx"
        (effects_root / package_path.name).write_bytes(package_path.read_bytes())

    (SET_ROOT / "set.yaml").write_text(
        "\n".join(
            [
                "set_id: authoring_demo",
                f"source_id: {SOURCE_ID}",
                "title: Authoring Demo",
                "version: 1",
                "min_service_version: 1.0.0",
                "effects:",
                "  - state_idle.lefx",
                "  - overlay_focus.lefx",
                "  - event_ping.lefx",
            ]
        ),
        encoding="utf-8",
    )


def _effect_code(*, class_name: str, effect_id: str, title: str, layer_name: str, color: str, mode: str) -> str:
    if mode == "state":
        playback_modes = "(PlaybackMode.LOOP, PlaybackMode.PERSISTENT)"
        render_lines = [
            "return [base_color] * ctx.led_count",
        ]
        restorable = "True"
        requires_finite_duration = "False"
    elif mode == "overlay":
        playback_modes = "(PlaybackMode.LOOP, PlaybackMode.PERSISTENT)"
        render_lines = [
            "leds = [None] * ctx.led_count",
            "leds[0] = base_color",
            "leds[1 % ctx.led_count] = base_color",
            "return leds",
        ]
        restorable = "True"
        requires_finite_duration = "False"
    else:
        playback_modes = "(PlaybackMode.SINGLE_RUN,)"
        render_lines = [
            "phase = int(ctx.now * 12) % 2",
            "active_color = base_color if phase == 0 else 0",
            "return [active_color] * ctx.led_count",
        ]
        restorable = "False"
        requires_finite_duration = "True"

    return "\n".join(
        [
            "from __future__ import annotations",
            "",
            "from src.core.effect_schema import BaseEffect, EffectCapabilities, EffectDefinition, LayerId, LayerRule, PlaybackMode, RenderContext",
            "from src.core.effect_schema import EffectParamDefinition",
            "",
            "",
            f"class {class_name}(BaseEffect):",
            "    definition = EffectDefinition(",
            f'        id="{effect_id}",',
            f'        title="{title}",',
            '        description="Generated by the authoring smoke test.",',
            "        parameter_schema={",
            f'            "color": EffectParamDefinition(name="color", type="color", default="{color}"),',
            "        },",
            f'        defaults={{"color": "{color}"}},',
            "        capabilities=EffectCapabilities(",
            f"            playback_modes={playback_modes},",
            f"            restorable={restorable},",
            "        ),",
            "        layer_rules={",
            f"            LayerId.{layer_name}: LayerRule(",
            "                allowed=True,",
            f"                allowed_playback_modes={playback_modes},",
            f"                requires_finite_duration={requires_finite_duration},",
            "            ),",
            "        },",
            "    )",
            "",
            "    def render(self, ctx: RenderContext) -> list[int | None]:",
            f'        raw_color = str(ctx.params.get("color", "{color}")).replace("#", "0x")',
            "        base_color = int(raw_color, 16)",
            *[f"        {line}" for line in render_lines],
            "",
        ]
    )


def _effect_presets_yaml(*, effect_id: str, title: str, layer_name: str, color: str) -> str:
    category = _preset_category_for_layer(layer_name)
    target_layer = layer_name
    lines = [
        "presets:",
        f"  {effect_id}_default:",
        f"    title: {json.dumps(f'{title} Default', ensure_ascii=True)}",
        f"    category: {category}",
        f"    target_layer: {target_layer}",
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


def _command_definition(*, effect_id: str, layer_name: str) -> dict[str, object]:
    category = _preset_category_for_layer(layer_name)
    on_payload: dict[str, object] = {"preset": f"{effect_id}_default"}
    if category == "event":
        return {
            "kind": "event",
            "on": on_payload,
        }
    return {
        "kind": "state_toggle",
        "on": on_payload,
        "off": {
            "action": "clear_layer",
            "target_layer": layer_name,
        },
    }


def _preset_category_for_layer(layer_name: str) -> str:
    if layer_name in {"STATE_LAYER", "BACKGROUND_STATE_LAYER"}:
        return "state"
    if layer_name in {"ONGOING_OVERLAY_LAYER", "TEMP_OVERLAY_LAYER"}:
        return "overlay"
    if layer_name == "EVENT_LAYER":
        return "event"
    return "effect"


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


if __name__ == "__main__":
    raise SystemExit(main())
