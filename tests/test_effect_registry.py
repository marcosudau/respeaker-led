from __future__ import annotations

import textwrap

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


def test_registry_can_add_library_path_and_reload_effects(tmp_path):
    library_dir = tmp_path / "custom_effects"
    library_dir.mkdir()
    (library_dir / "my_effects.py").write_text(
        textwrap.dedent(
            """
            from src.core.effect_schema import BaseEffect, EffectDefinition, RenderContext


            class LibraryGlowEffect(BaseEffect):
                definition = EffectDefinition(
                    id="library_glow",
                    title="Library Glow",
                    description="Aus Bibliothek geladen",
                )

                def render(self, ctx: RenderContext) -> list[int | None]:
                    return [0x112233] * ctx.led_count
            """
        ),
        encoding="utf-8",
    )

    registry = EffectRegistry([SoftPulseEffect])
    source = registry.add_library_path(library_dir)

    assert registry.list_effect_ids() == ["soft_pulse"]
    assert source.kind == "library_path"

    registry.reload()

    assert registry.list_effect_ids() == ["library_glow", "soft_pulse"]
    assert registry.get("library_glow").source_id == source.source_id


def test_registry_deduplicates_library_paths(tmp_path):
    registry = EffectRegistry()

    first = registry.add_library_path(tmp_path)
    second = registry.add_library_path(tmp_path, enabled=False)

    assert first.source_id == second.source_id
    assert len(registry.list_library_sources()) == 1
    assert registry.list_library_sources()[0].enabled is False


def test_default_registry_registers_builtin_effects():
    registry = build_default_effect_registry()

    assert {"off", "solid_color", "soft_pulse", "warning_flash"}.issubset(set(registry.list_effect_ids()))
    assert registry.get("off").source_id == "default-effects"


def test_disabled_library_source_is_not_loaded_on_reload(tmp_path):
    library_dir = tmp_path / "custom_effects"
    library_dir.mkdir()
    (library_dir / "hidden_effect.py").write_text(
        textwrap.dedent(
            """
            from src.core.effect_schema import BaseEffect, EffectDefinition, RenderContext


            class HiddenEffect(BaseEffect):
                definition = EffectDefinition(
                    id="hidden_effect",
                    title="Hidden Effect",
                    description="Soll nur bei aktiviertem Source geladen werden",
                )

                def render(self, ctx: RenderContext) -> list[int | None]:
                    return [0x123456] * ctx.led_count
            """
        ),
        encoding="utf-8",
    )

    registry = EffectRegistry([SoftPulseEffect])
    registry.add_library_path(library_dir, enabled=False)
    registry.reload()

    assert "hidden_effect" not in registry.list_effect_ids()


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
            },
            {
                "dir_name": "idle",
                "package_id": "voice.idle",
                "class_name": "IdleBlueEffect",
                "effect_id": "idle_blue",
                "layer_name": "STATE_LAYER",
            },
        ],
        commands={
            "listening": {
                "kind": "state_toggle",
                "on": {
                    "effect": "app.voice_assistant::listening_blue",
                    "target_layer": "MAIN_LAYER",
                    "params": {},
                },
                "off": {
                    "action": "clear_layer",
                    "target_layer": "MAIN_LAYER",
                },
            }
        },
    )
    package_path = tmp_path / "voice_assistant.lefxset"
    build_effect_set(set_dir, package_path)

    registry = EffectRegistry([SoftPulseEffect])
    source = registry.register_effect_source(package_path)

    assert source.kind == "effect_set"
    assert "app.voice_assistant::listening_blue" in registry.list_effect_ids()
    commands = registry.list_effect_commands("app.voice_assistant")
    assert commands[0]["command_name"] == "listening"
    assert commands[0]["on"]["effect"] == "app.voice_assistant::listening_blue"


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
            }
        ],
        commands={
            "listening": {
                "kind": "state_toggle",
                "on": {
                    "effect": "app.voice_assistant::listening_blue",
                    "target_layer": "MAIN_LAYER",
                    "params": {},
                },
                "off": {
                    "action": "clear_layer",
                    "target_layer": "MAIN_LAYER",
                },
            }
        },
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
