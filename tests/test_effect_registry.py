from __future__ import annotations

from pathlib import Path

import pytest

from src.engine.effect_package_builder import build_effect_set
import src.engine.effect_registry as effect_registry_module
from src.engine.effect_registry import EffectRegistry, build_default_effect_registry
from src.core.effect_schema import (
    DEFAULT_LAYER_PRIORITIES,
    BaseEffect,
    EffectCapabilities,
    EffectDefinition,
    EffectInvocation,
    EffectParamDefinition,
    LayerId,
    LayerRule,
    PlaybackMode,
    RenderContext,
)
from src.infrastructure.paths import DEFAULT_EFFECT_SET_PATH
from tests.package_test_utils import write_effect_set_source


class SoftPulseEffect(BaseEffect):
    definition = EffectDefinition(
        id="soft_pulse",
        title="Soft Pulse",
        description="Weiches Pulsieren einer Farbe",
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
        },
        defaults={"color": "#33AAFF"},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules={
            LayerId.STATE_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            ),
        },
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        return [None] * ctx.led_count


class WarningFlashEffect(BaseEffect):
    definition = EffectDefinition(
        id="warning_flash",
        title="Warning Flash",
        description="Kurzer Warnblitz",
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_queueing=True,
            preemptible=False,
        ),
        layer_rules={
            LayerId.EVENT_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
            ),
        },
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        return [0xFFAA00] * ctx.led_count


def test_effect_invocation_uses_layer_priority_as_default():
    invocation = EffectInvocation(
        invocation_id="inv-1",
        effect_id="soft_pulse",
        target_layer=LayerId.ONGOING_OVERLAY_LAYER,
    )

    assert invocation.effective_priority() == DEFAULT_LAYER_PRIORITIES[LayerId.ONGOING_OVERLAY_LAYER]


def test_effect_invocation_prefers_explicit_priority():
    invocation = EffectInvocation(
        invocation_id="inv-2",
        effect_id="warning_flash",
        target_layer=LayerId.EVENT_LAYER,
        priority=777,
    )

    assert invocation.effective_priority() == 777


def test_registry_registers_effect_classes_and_lists_sorted_ids():
    registry = EffectRegistry([WarningFlashEffect, SoftPulseEffect])

    assert registry.list_effect_ids() == ["soft_pulse", "warning_flash"]
    assert registry.get("soft_pulse").effect_class is SoftPulseEffect
    assert registry.get("warning_flash").definition.capabilities.preemptible is False


def test_registry_rejects_duplicate_effect_ids():
    class DuplicateSoftPulse(BaseEffect):
        definition = EffectDefinition(
            id="soft_pulse",
            title="Duplicate Soft Pulse",
            description="Duplikat",
        )

        def render(self, ctx: RenderContext) -> list[int | None]:
            return [None] * ctx.led_count

    registry = EffectRegistry([SoftPulseEffect])

    with pytest.raises(ValueError, match="Duplicate effect id"):
        registry.register(DuplicateSoftPulse)


def test_registry_rejects_invalid_effect_id():
    class InvalidEffect(BaseEffect):
        definition = EffectDefinition(
            id="Not-Valid",
            title="Broken",
            description="Kaputt",
        )

        def render(self, ctx: RenderContext) -> list[int | None]:
            return [None] * ctx.led_count

    with pytest.raises(ValueError, match="snake_case"):
        EffectRegistry([InvalidEffect])


def test_default_registry_registers_builtin_effects():
    assert DEFAULT_EFFECT_SET_PATH.is_file()

    registry = build_default_effect_registry()
    sources = {source.source_id: source for source in registry.list_effect_sources()}

    assert {"off", "solid_color", "soft_pulse", "warning_flash"}.issubset(set(registry.list_effect_ids()))
    assert registry.get("off").source_id == "default-effects"
    assert registry.get("default-effects::solid_color").definition.id == "solid_color"
    assert sources["default-effects"].kind == "effect_set"
    assert Path(sources["default-effects"].path) == DEFAULT_EFFECT_SET_PATH.resolve()


def test_default_registry_prefers_first_available_artifact_candidate(tmp_path, monkeypatch):
    set_dir = tmp_path / "default_effects_src"
    write_effect_set_source(
        set_dir,
        source_id="default-effects",
        set_id="default_effects_bundle",
        title="Default Effects Bundle",
        effects=[
            {
                "dir_name": "soft_pulse",
                "package_id": "default.soft_pulse",
                "class_name": "BundledSoftPulseEffect",
                "effect_id": "soft_pulse",
                "layer_name": "MAIN_LAYER",
                "color": "#123456",
            }
        ],
    )
    bundle_artifact = tmp_path / "effects" / "default-effects.lefxset"
    bundle_artifact.parent.mkdir(parents=True, exist_ok=True)
    build_effect_set(set_dir, bundle_artifact)
    monkeypatch.setattr(effect_registry_module, "_default_effect_artifact_candidates", lambda: [bundle_artifact, DEFAULT_EFFECT_SET_PATH])

    registry = build_default_effect_registry()
    sources = {source.source_id: source for source in registry.list_effect_sources()}

    assert registry.get("soft_pulse").definition.defaults["color"] == "#123456"
    assert Path(sources["default-effects"].path) == bundle_artifact.resolve()


def test_default_registry_raises_when_default_artifact_is_missing(monkeypatch):
    monkeypatch.setattr(effect_registry_module, "_default_effect_artifact_candidates", lambda: [])

    with pytest.raises(FileNotFoundError, match="Default effect set artifact not found"):
        build_default_effect_registry()


def test_default_registry_raises_when_default_artifact_is_invalid(tmp_path, monkeypatch):
    broken_artifact = tmp_path / "default-effects.lefxset"
    broken_artifact.write_text("broken", encoding="utf-8")
    monkeypatch.setattr(effect_registry_module, "_default_effect_artifact_candidates", lambda: [broken_artifact])

    with pytest.raises(RuntimeError, match="Failed to load the default effect set artifact"):
        build_default_effect_registry()


def test_registry_can_register_effect_set_and_commands(tmp_path):
    set_dir = tmp_path / "voice_assistant_src"
    write_effect_set_source(
        set_dir,
        source_id="app.voice_assistant",
        set_id="voice_assistant",
        title="Voice Assistant",
        effects=[
            {
                "dir_name": "listening",
                "package_id": "voice.listening",
                "class_name": "ListeningBlueEffect",
                "effect_id": "listening_blue",
                "layer_name": "MAIN_LAYER",
                "presets": {
                    "effect_listening_default": {
                        "category": "effect",
                        "target_layer": "MAIN_LAYER",
                        "params": {"color": "#224466"},
                    }
                },
                "commands": {
                    "listening": {
                        "kind": "state_toggle",
                        "on": {"preset": "effect_listening_default"},
                        "off": {
                            "action": "clear_layer",
                            "target_layer": "MAIN_LAYER",
                        },
                    }
                },
            },
            {
                "dir_name": "idle",
                "package_id": "voice.idle",
                "class_name": "IdleBlueEffect",
                "effect_id": "idle_blue",
                "layer_name": "STATE_LAYER",
            },
        ],
    )
    package_path = tmp_path / "voice_assistant.lefxset"
    build_effect_set(set_dir, package_path)

    registry = EffectRegistry([SoftPulseEffect])
    source = registry.register_effect_source(package_path)

    assert source.kind == "effect_set"
    assert "app.voice_assistant::listening_blue" in registry.list_effect_ids()
    commands = registry.list_effect_commands("app.voice_assistant")
    assert commands[0]["command_name"] == "listening"
    assert commands[0]["on"]["preset"] == "effect_listening_default"


def test_registry_lists_effect_commands_via_registry_model_instead_of_service_filtering(tmp_path):
    set_dir = tmp_path / "voice_assistant_src"
    write_effect_set_source(
        set_dir,
        source_id="app.voice_assistant",
        set_id="voice_assistant",
        title="Voice Assistant",
        effects=[
            {
                "dir_name": "listening",
                "package_id": "voice.listening",
                "class_name": "ListeningBlueEffect",
                "effect_id": "listening_blue",
                "layer_name": "MAIN_LAYER",
                "presets": {
                    "effect_listening_default": {
                        "category": "effect",
                        "target_layer": "MAIN_LAYER",
                        "params": {"color": "#224466"},
                    }
                },
                "commands": {
                    "listening": {
                        "kind": "state_toggle",
                        "on": {"preset": "effect_listening_default"},
                        "off": {
                            "action": "clear_layer",
                            "target_layer": "MAIN_LAYER",
                        },
                    }
                },
            },
            {
                "dir_name": "idle",
                "package_id": "voice.idle",
                "class_name": "IdleBlueEffect",
                "effect_id": "idle_blue",
                "layer_name": "STATE_LAYER",
                "commands": {
                    "idle-direct": {
                        "kind": "state_toggle",
                        "on": {
                            "action": "apply_effect",
                            "effect": "idle_blue",
                            "target_layer": "STATE_LAYER",
                            "params": {"color": "#335577"},
                        },
                        "off": {
                            "action": "clear_layer",
                            "target_layer": "STATE_LAYER",
                        },
                    }
                },
            },
        ],
    )
    package_path = tmp_path / "voice_assistant.lefxset"
    build_effect_set(set_dir, package_path)

    registry = EffectRegistry()
    registry.register_effect_source(package_path)

    listening_commands = registry.list_effect_commands_for_effect("app.voice_assistant", "listening_blue")
    idle_commands = registry.list_effect_commands_for_effect("app.voice_assistant", "idle_blue")

    assert [command["command_name"] for command in listening_commands] == ["listening"]
    assert [command["command_name"] for command in idle_commands] == ["idle-direct"]


def test_registry_autodiscovers_effect_packages_from_package_root(tmp_path, monkeypatch):
    packages_root = tmp_path / "packages"
    set_dir = tmp_path / "voice_assistant_src"
    write_effect_set_source(
        set_dir,
        source_id="app.voice_assistant",
        set_id="voice_assistant",
        title="Voice Assistant",
        effects=[
            {
                "dir_name": "listening",
                "package_id": "voice.listening",
                "class_name": "ListeningBlueEffect",
                "effect_id": "listening_blue",
                "layer_name": "MAIN_LAYER",
                "presets": {
                    "effect_listening_default": {
                        "category": "effect",
                        "target_layer": "MAIN_LAYER",
                        "params": {"color": "#224466"},
                    }
                },
                "commands": {
                    "listening": {
                        "kind": "state_toggle",
                        "on": {"preset": "effect_listening_default"},
                        "off": {
                            "action": "clear_layer",
                            "target_layer": "MAIN_LAYER",
                        },
                    }
                },
            }
        ],
    )
    packages_root.mkdir(parents=True, exist_ok=True)
    package_path = packages_root / "voice_assistant.lefxset"
    build_effect_set(set_dir, package_path)

    monkeypatch.setattr(effect_registry_module, "EFFECT_PACKAGES_ROOT", packages_root)
    registry = EffectRegistry()
    registry.reload()

    assert "app.voice_assistant::listening_blue" in registry.list_effect_ids()
    sources = registry.list_effect_sources()
    assert len(sources) == 1
    assert sources[0].autodiscovered is True
    assert sources[0].source_id == "app.voice_assistant"
