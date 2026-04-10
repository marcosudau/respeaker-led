from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core.effect_schema import LayerId, parse_layer_id


_COMMAND_KINDS = {"state_toggle", "event"}
_ACTION_KINDS = {"apply_effect", "clear_layer"}


@dataclass(slots=True, frozen=True)
class CommandAction:
    action: str
    target_layer: LayerId
    effect_id: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    replace_existing: bool = True


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


def parse_command_definitions(source_id: str, payload: dict[str, Any]) -> list[EffectCommandDefinition]:
    if not isinstance(payload, dict):
        raise ValueError("commands.json must contain a JSON object")

    raw_commands = payload.get("commands")
    if not isinstance(raw_commands, dict) or not raw_commands:
        raise ValueError("commands.json must define a non-empty 'commands' object")

    commands: list[EffectCommandDefinition] = []
    seen: set[str] = set()
    for command_name, raw_definition in raw_commands.items():
        normalized_name = str(command_name or "").strip()
        if not normalized_name:
            raise ValueError("Command names must be non-empty")
        if normalized_name in seen:
            raise ValueError(f"Duplicate command name detected: {normalized_name!r}")
        seen.add(normalized_name)
        commands.append(parse_command_definition(source_id, normalized_name, raw_definition))
    return commands


def parse_command_definition(source_id: str, command_name: str, raw_definition: Any) -> EffectCommandDefinition:
    if not isinstance(raw_definition, dict):
        raise ValueError(f"Command {command_name!r} must be a JSON object")

    kind = str(raw_definition.get("kind", "")).strip()
    if kind not in _COMMAND_KINDS:
        raise ValueError(f"Command {command_name!r} has unsupported kind: {kind!r}")

    on_action = parse_command_action(command_name, "on", raw_definition.get("on"))
    off_action = None
    if "off" in raw_definition and raw_definition.get("off") is not None:
        off_action = parse_command_action(command_name, "off", raw_definition.get("off"))

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


def parse_command_action(command_name: str, label: str, raw_action: Any) -> CommandAction:
    if not isinstance(raw_action, dict):
        raise ValueError(f"Command {command_name!r} action {label!r} must be a JSON object")

    action_name = str(raw_action.get("action", "")).strip()
    effect_id = raw_action.get("effect")
    if effect_id:
        action_name = action_name or "apply_effect"
    if action_name not in _ACTION_KINDS:
        raise ValueError(
            f"Command {command_name!r} action {label!r} must declare one of {_ACTION_KINDS}, got {action_name!r}"
        )

    if "target_layer" not in raw_action:
        raise ValueError(f"Command {command_name!r} action {label!r} must define 'target_layer'")
    target_layer = parse_layer_id(raw_action["target_layer"])

    params = raw_action.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise ValueError(f"Command {command_name!r} action {label!r} field 'params' must be a JSON object")

    normalized_effect_id = None if effect_id is None else str(effect_id).strip()
    if action_name == "apply_effect" and not normalized_effect_id:
        raise ValueError(f"Command {command_name!r} action {label!r} must define an effect id")
    if action_name == "clear_layer" and normalized_effect_id is not None:
        raise ValueError(f"Command {command_name!r} action {label!r} must not define an effect id")

    return CommandAction(
        action=action_name,
        target_layer=target_layer,
        effect_id=normalized_effect_id,
        params=dict(params),
        replace_existing=bool(raw_action.get("replace_existing", True)),
    )


def _serialize_action(action: CommandAction) -> dict[str, Any]:
    payload = {
        "action": action.action,
        "target_layer": action.target_layer.value,
        "replace_existing": action.replace_existing,
        "params": dict(action.params),
    }
    if action.effect_id is not None:
        payload["effect"] = action.effect_id
    return payload
