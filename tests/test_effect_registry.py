from __future__ import annotations

import json
from pathlib import Path

import pytest

from respeaker_led.engine.effect_package_builder import build_effect_package, build_effect_set
import respeaker_led.engine.effect_registry as effect_registry_module
from respeaker_led.engine.effect_registry import EffectRegistry, build_default_effect_registry
from respeaker_led.core.effect_schema import (
    DEFAULT_LAYER_PRIORITIES,
    BaseEffect,
    ColorModel,
    DefinitionType,
    EffectCapabilities,
    EffectDefinition,
    EffectInvocation,
    EffectParamDefinition,
    LayerId,
    LayerRule,
    PlaybackMode,
    RenderContext,
)
from tests.build_artifact_helpers import default_effect_set_path
from tests.package_test_utils import write_effect_set_source


class SoftPulseEffect(BaseEffect):
    definition = EffectDefinition(
        id="soft_pulse",
        title="Soft Pulse",
        description="Weiches Pulsieren einer Farbe",
        definition_type=DefinitionType.STATE,
        parameter_schema={
            "color": EffectParamDefinition(name="color", type="color", default="#33AAFF"),
            "brightness": EffectParamDefinition(
                name="brightness",
                type="float",
                default=1.0,
                minimum=0.0,
                maximum=1.0,
            ),
        },
        defaults={"color": "#33AAFF", "brightness": 1.0},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
            restorable=True,
        ),
        layer_rules={
            LayerId.STATE_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.LOOP, PlaybackMode.PERSISTENT),
                requires_indefinite_duration=True,
            ),
        },
        color_model=ColorModel.MONO,
    )

    def render(self, ctx: RenderContext) -> list[int | None]:
        return [None] * ctx.led_count


class WarningFlashEffect(BaseEffect):
    definition = EffectDefinition(
        id="warning_flash",
        title="Warning Flash",
        description="Kurzer Warnblitz",
        definition_type=DefinitionType.EVENT,
        parameter_schema={
            "duration_ms": EffectParamDefinition(name="duration_ms", type="duration_ms", default=250, minimum=1),
        },
        defaults={"duration_ms": 250},
        capabilities=EffectCapabilities(
            playback_modes=(PlaybackMode.SINGLE_RUN,),
            supports_queueing=True,
            preemptible=False,
        ),
        layer_rules={
            LayerId.EVENT_LAYER: LayerRule(
                allowed=True,
                allowed_playback_modes=(PlaybackMode.SINGLE_RUN,),
                requires_finite_duration=True,
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
            definition_type=DefinitionType.STATE,
            layer_rules={
                LayerId.STATE_LAYER: LayerRule(
                    requires_indefinite_duration=True,
                )
            },
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
    configured_default_effect_set = default_effect_set_path()
    assert configured_default_effect_set.is_file()

    registry = build_default_effect_registry()
    sources = {source.source_id: source for source in registry.list_effect_sources()}

    assert {"solid_color", "soft_pulse", "warning_flash"}.issubset(set(registry.list_effect_ids()))
    assert registry.get("default-effects::solid_color").definition.id == "solid_color"
    assert sources["default-effects"].kind == "effect_set"
    assert Path(sources["default-effects"].path) == configured_default_effect_set.resolve()


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
                "layer_name": "STATE_LAYER",
                "color": "#123456",
            }
        ],
    )
    bundle_artifact = tmp_path / "effects" / "default-effects.lefxset"
    bundle_artifact.parent.mkdir(parents=True, exist_ok=True)
    build_effect_set(set_dir, bundle_artifact)
    monkeypatch.setattr(effect_registry_module, "_default_effect_artifact_candidates", lambda: [bundle_artifact, default_effect_set_path()])
    monkeypatch.setattr(effect_registry_module, "_configured_builtin_effect_paths", lambda: [bundle_artifact])

    registry = build_default_effect_registry()
    sources = {source.source_id: source for source in registry.list_effect_sources()}

    assert registry.get("soft_pulse").definition.defaults["color"] == "#123456"
    assert Path(sources["default-effects"].path) == bundle_artifact.resolve()


def test_default_artifact_candidates_prefer_environment_override(tmp_path, monkeypatch):
    override = tmp_path / "default-effects.lefxset"
    monkeypatch.setenv("LED_CONTROLLER_DEFAULT_EFFECT_SET", str(override))
    monkeypatch.setattr(effect_registry_module, "_configured_builtin_effect_paths", lambda: [])

    candidates = effect_registry_module._default_effect_artifact_candidates()

    assert candidates[0] == override


def test_configured_builtin_effect_paths_ignores_invalid_and_missing_entries(tmp_path, monkeypatch):
    effects_root = tmp_path / "effects"
    effects_root.mkdir()
    effect_set = effects_root / "default-effects.lefxset"
    effect_set.write_text("default", encoding="utf-8")
    package_path = effects_root / "soft_pulse.lefx"
    package_path.write_text("package", encoding="utf-8")
    config_path = tmp_path / "build_config.json"
    config_path.write_text(
        json.dumps(
            {
                "builtin-effects-discovery": [
                    str(effect_set),
                    str(effects_root),
                    str(tmp_path / "missing.lefxset"),
                    "",
                    123,
                ]
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(effect_registry_module, "BUILD_CONFIG_PATH", config_path)
    monkeypatch.setattr(effect_registry_module, "PROJECT_ROOT", tmp_path)

    paths = effect_registry_module._configured_builtin_effect_paths()

    assert paths == [effect_set.resolve(), package_path.resolve()]


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


def test_registry_can_register_effect_set_and_resolve_preset(tmp_path):
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
                "layer_name": "STATE_LAYER",
                "presets": {
                    "listening_default": {
                        "params": {"color": "#224466"},
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
    resolved = registry.resolve_target(
        "app.voice_assistant::listening_default",
        expected_type=DefinitionType.STATE,
    )
    assert resolved.kind == "preset"
    assert resolved.effect.definition.id == "listening_blue"
    assert resolved.preset_params == {"color": "#224466"}


def test_registry_rejects_wrong_resolved_definition_type(tmp_path):
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
                "layer_name": "EVENT_LAYER",
            },
        ],
    )
    package_path = tmp_path / "voice_assistant.lefxset"
    build_effect_set(set_dir, package_path)

    registry = EffectRegistry()
    registry.register_effect_source(package_path)

    with pytest.raises(ValueError, match="not a state"):
        registry.resolve_target(
            "app.voice_assistant::listening_blue",
            expected_type=DefinitionType.STATE,
        )


def test_registry_rejects_global_id_collisions_across_sources(tmp_path):
    artifacts = []
    for source_id in ("app.one", "app.two"):
        source = tmp_path / source_id
        write_effect_set_source(
            source,
            source_id=source_id,
            set_id=source_id.replace(".", "_"),
            title=source_id,
            effects=[
                {
                    "dir_name": "shared",
                    "package_id": f"{source_id}.shared",
                    "class_name": "SharedEffect",
                    "effect_id": "shared",
                    "layer_name": "STATE_LAYER",
                }
            ],
        )
        artifact = tmp_path / f"{source_id}.lefxset"
        build_effect_set(source, artifact)
        artifacts.append(artifact)

    registry = EffectRegistry()
    registry.register_effect_source(artifacts[0])
    with pytest.raises(ValueError, match="Global id collision"):
        registry.register_effect_source(artifacts[1])
    assert [source.source_id for source in registry.list_effect_sources()] == ["app.one"]


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
                "layer_name": "STATE_LAYER",
                "presets": {
                    "listening_default": {
                        "params": {"color": "#224466"},
                    }
                },
            }
        ],
    )
    packages_root.mkdir(parents=True, exist_ok=True)
    package_path = packages_root / "voice_assistant.lefxset"
    build_effect_set(set_dir, package_path)

    monkeypatch.setattr(effect_registry_module, "APP_EFFECT_PACKAGES_ROOT", packages_root)
    registry = EffectRegistry()
    registry.reload()

    assert "app.voice_assistant::listening_blue" in registry.list_effect_ids()
    sources = registry.list_effect_sources()
    assert len(sources) == 1
    assert sources[0].autodiscovered is True
    assert sources[0].source_id == "app.voice_assistant"


def test_registry_skips_autodiscovered_duplicate_effect_packages(tmp_path, monkeypatch):
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
                "layer_name": "STATE_LAYER",
            }
        ],
    )
    packages_root.mkdir(parents=True, exist_ok=True)
    set_path = packages_root / "voice_assistant.lefxset"
    package_path = packages_root / "listening_blue.lefx"
    build_effect_set(set_dir, set_path)
    build_effect_package(set_dir / "effects" / "listening", package_path)

    monkeypatch.setattr(effect_registry_module, "APP_EFFECT_PACKAGES_ROOT", packages_root)
    registry = EffectRegistry()
    registry.reload()

    assert registry.list_effect_ids() == ["app.voice_assistant::listening_blue"]
    sources = registry.list_effect_sources()
    assert len(sources) == 1
    assert Path(sources[0].path) == set_path.resolve()
