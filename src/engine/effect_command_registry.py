from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core.effect_schema import LayerId, parse_layer_id
from .effect_preset_registry import EffectPresetDefinition


_COMMAND_KINDS = {"state_toggle", "event"}
_ACTION_KINDS = {"apply_effect", "apply_preset", "clear_layer"}
_KIND_CATEGORY_RULES = {
    "state_toggle": {"state", "effect", "overlay"},
    "event": {"event"},
}


@dataclass(slots=True, frozen=True)
class CommandAction:
    action: str
    target_layer: LayerId
    effect_id: str | None = None
    preset_id: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    replace_existing: bool = True
    duration_ms: int | None = None
    priority: int | None = None
    enqueue: bool = False


@dataclass(slots=True, frozen=True)
class EffectCommandDefinition:
    source_id: str
    command_name: str
    kind: str
    on_action: CommandAction
    off_action: CommandAction | None = None

    def supports_off(self) -> bool:
        return self.off_action is not None

    def serialize(self) -> dict[str, Any]:
        data = {
            "source_id": self.source_id,
            "command_name": self.command_name,
            "kind": self.kind,
            "supports_off": self.supports_off(),
            "on": _serialize_action(self.on_action),
        }
        if self.off_action is not None:
            data["off"] = _serialize_action(self.off_action)
        return data


class EffectCommandRegistry:
    def __init__(self) -> None:
        self._commands_by_source: dict[str, dict[str, EffectCommandDefinition]] = {}

    def register_many(self, source_id: str, commands: list[EffectCommandDefinition]) -> None:
        scoped = self._commands_by_source.setdefault(source_id, {})
        for command in commands:
            if command.command_name in scoped:
                raise ValueError(f"Duplicate command name detected for source {source_id!r}: {command.command_name!r}")
            scoped[command.command_name] = command

    def remove_source(self, source_id: str) -> None:
        self._commands_by_source.pop(source_id, None)

    def get(self, source_id: str, command_name: str) -> EffectCommandDefinition:
        return self._commands_by_source[source_id][command_name]

    def list_commands(self, source_id: str | None = None) -> list[EffectCommandDefinition]:
        if source_id is not None:
            return sorted(self._commands_by_source.get(source_id, {}).values(), key=lambda item: item.command_name)

        commands: list[EffectCommandDefinition] = []
        for scoped_source in sorted(self._commands_by_source):
            commands.extend(sorted(self._commands_by_source[scoped_source].values(), key=lambda item: item.command_name))
        return commands


def parse_command_definitions(
    source_id: str,
    payload: dict[str, Any],
    *,
    presets: list[EffectPresetDefinition] | None = None,
    default_effect_id: str | None = None,
    source_effect_ids: set[str] | None = None,
) -> list[EffectCommandDefinition]:
    if not isinstance(payload, dict):
        raise ValueError("commands.json must contain a JSON object")

    raw_commands = payload.get("commands")
    if not isinstance(raw_commands, dict) or not raw_commands:
        raise ValueError("commands.json must define a non-empty 'commands' object")

    preset_map = {preset.preset_id: preset for preset in presets or []}
    normalized_effect_ids = set(source_effect_ids or set())
    if default_effect_id is not None:
        normalized_effect_ids.add(_qualify_effect_id(source_id, default_effect_id))

    commands: list[EffectCommandDefinition] = []
    seen: set[str] = set()
    for command_name, raw_definition in raw_commands.items():
        normalized_name = str(command_name or "").strip()
        if not normalized_name:
            raise ValueError("Command names must be non-empty")
        if normalized_name in seen:
            raise ValueError(f"Duplicate command name detected: {normalized_name!r}")
        seen.add(normalized_name)
        commands.append(
            parse_command_definition(
                source_id,
                normalized_name,
                raw_definition,
                presets=preset_map,
                default_effect_id=default_effect_id,
                source_effect_ids=normalized_effect_ids,
            )
        )
    return commands


def parse_command_definition(
    source_id: str,
    command_name: str,
    raw_definition: Any,
    *,
    presets: dict[str, EffectPresetDefinition] | None = None,
    default_effect_id: str | None = None,
    source_effect_ids: set[str] | None = None,
) -> EffectCommandDefinition:
    if not isinstance(raw_definition, dict):
        raise ValueError(f"Command {command_name!r} must be a JSON object")

    kind = str(raw_definition.get("kind", "")).strip()
    if kind not in _COMMAND_KINDS:
        raise ValueError(f"Command {command_name!r} has unsupported kind: {kind!r}")

    on_action = parse_command_action(
        source_id,
        command_name,
        "on",
        raw_definition.get("on"),
        presets=presets or {},
        default_effect_id=default_effect_id,
        source_effect_ids=source_effect_ids or set(),
        command_kind=kind,
    )
    off_action = None
    if "off" in raw_definition and raw_definition.get("off") is not None:
        off_action = parse_command_action(
            source_id,
            command_name,
            "off",
            raw_definition.get("off"),
            presets=presets or {},
            default_effect_id=default_effect_id,
            source_effect_ids=source_effect_ids or set(),
            command_kind=kind,
        )

    if kind == "state_toggle" and off_action is None:
        raise ValueError(f"Command {command_name!r} of kind 'state_toggle' must define an 'off' action")
    if kind == "event" and off_action is not None:
        raise ValueError(f"Command {command_name!r} of kind 'event' must not define an 'off' action")

    return EffectCommandDefinition(
        source_id=source_id,
        command_name=command_name,
        kind=kind,
        on_action=on_action,
        off_action=off_action,
    )


def parse_command_action(
    source_id: str,
    command_name: str,
    label: str,
    raw_action: Any,
    *,
    presets: dict[str, EffectPresetDefinition],
    default_effect_id: str | None,
    source_effect_ids: set[str],
    command_kind: str,
) -> CommandAction:
    if not isinstance(raw_action, dict):
        raise ValueError(f"Command {command_name!r} action {label!r} must be a JSON object")

    action_name = str(raw_action.get("action", "")).strip()
    preset_id = raw_action.get("preset")
    effect_id = raw_action.get("effect")

    if preset_id is not None:
        action_name = action_name or "apply_preset"
    elif effect_id is not None or action_name == "apply_effect":
        action_name = action_name or "apply_effect"

    if action_name not in _ACTION_KINDS:
        raise ValueError(
            f"Command {command_name!r} action {label!r} must declare one of {_ACTION_KINDS}, got {action_name!r}"
        )

    params = raw_action.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise ValueError(f"Command {command_name!r} action {label!r} field 'params' must be a JSON object")

    if action_name == "clear_layer":
        if "target_layer" not in raw_action:
            raise ValueError(f"Command {command_name!r} action {label!r} must define 'target_layer'")
        if preset_id is not None or effect_id is not None:
            raise ValueError(f"Command {command_name!r} action {label!r} clear_layer must not reference preset or effect")
        return CommandAction(
            action=action_name,
            target_layer=parse_layer_id(raw_action["target_layer"]),
            replace_existing=bool(raw_action.get("replace_existing", True)),
        )

    if action_name == "apply_preset":
        normalized_preset_id = str(preset_id or "").strip()
        if not normalized_preset_id:
            raise ValueError(f"Command {command_name!r} action {label!r} must define a preset id")
        if normalized_preset_id not in presets:
            raise ValueError(
                f"Command {command_name!r} action {label!r} references unknown preset {normalized_preset_id!r}"
            )
        if params:
            raise ValueError(f"Command {command_name!r} action {label!r} must not override params for preset actions")
        preset = presets[normalized_preset_id]
        _validate_command_kind_matches_preset(command_name, command_kind, preset)
        return CommandAction(
            action=action_name,
            target_layer=preset.target_layer,
            preset_id=normalized_preset_id,
            replace_existing=bool(raw_action.get("replace_existing", preset.replace_existing)),
            duration_ms=None if raw_action.get("duration_ms") is None else int(raw_action["duration_ms"]),
            priority=None if raw_action.get("priority") is None else int(raw_action["priority"]),
            enqueue=bool(raw_action.get("enqueue", preset.enqueue)),
        )

    normalized_effect_id = _normalize_effect_reference(source_id, effect_id, default_effect_id)
    if normalized_effect_id is None:
        raise ValueError(f"Command {command_name!r} action {label!r} must define an effect id")
    if source_effect_ids and normalized_effect_id not in source_effect_ids:
        raise ValueError(
            f"Command {command_name!r} action {label!r} references unknown effect {normalized_effect_id!r}"
        )
    if "target_layer" not in raw_action:
        raise ValueError(f"Command {command_name!r} action {label!r} must define 'target_layer'")

    return CommandAction(
        action=action_name,
        target_layer=parse_layer_id(raw_action["target_layer"]),
        effect_id=normalized_effect_id,
        params=dict(params),
        replace_existing=bool(raw_action.get("replace_existing", True)),
        duration_ms=None if raw_action.get("duration_ms") is None else int(raw_action["duration_ms"]),
        priority=None if raw_action.get("priority") is None else int(raw_action["priority"]),
        enqueue=bool(raw_action.get("enqueue", False)),
    )


def _normalize_effect_reference(source_id: str, effect_id: Any, default_effect_id: str | None) -> str | None:
    if effect_id is None:
        if default_effect_id is None:
            return None
        return _qualify_effect_id(source_id, default_effect_id)
    normalized = str(effect_id).strip()
    if not normalized:
        return None
    return _qualify_effect_id(source_id, normalized)


def _qualify_effect_id(source_id: str, effect_id: str) -> str:
    return effect_id if "::" in effect_id else f"{source_id}::{effect_id}"


def _validate_command_kind_matches_preset(command_name: str, command_kind: str, preset: EffectPresetDefinition) -> None:
    allowed_categories = _KIND_CATEGORY_RULES[command_kind]
    if preset.category not in allowed_categories:
        allowed = ", ".join(sorted(allowed_categories))
        raise ValueError(
            f"Command {command_name!r} of kind {command_kind!r} cannot target preset {preset.preset_id!r} with category {preset.category!r}. Allowed: {allowed}"
        )


def _serialize_action(action: CommandAction) -> dict[str, Any]:
    payload = {
        "action": action.action,
        "target_layer": action.target_layer.value,
        "replace_existing": action.replace_existing,
        "enqueue": action.enqueue,
    }
    if action.effect_id is not None:
        payload["effect"] = action.effect_id
    if action.preset_id is not None:
        payload["preset"] = action.preset_id
    if action.params:
        payload["params"] = dict(action.params)
    if action.duration_ms is not None:
        payload["duration_ms"] = action.duration_ms
    if action.priority is not None:
        payload["priority"] = action.priority
    return payload
