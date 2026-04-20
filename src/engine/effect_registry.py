from __future__ import annotations

import json
import hashlib
import inspect
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ..core.effect_schema import BaseEffect, EffectCapabilities, EffectDefinition, EffectParamDefinition, LayerRule
from ..infrastructure.paths import (
    APP_DEFAULT_EFFECT_SET_PATH,
    APP_EFFECT_PACKAGES_ROOT,
    BUILD_CONFIG_PATH,
    DEFAULT_EFFECT_SOURCE_ID,
    DEFAULT_EFFECT_SET_FILENAME,
    PROJECT_ROOT,
)
from .effect_command_registry import EffectCommandRegistry
from .effect_package_loader import (
    LoadedEffectPackage,
    LoadedEffectSet,
    inspect_effect_source,
    load_effect_package,
    load_effect_set,
)
from .effect_preset_registry import EffectPresetRegistry


_EFFECT_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
logger = logging.getLogger("led_controller.effect_registry")


def _default_effect_artifact_candidates() -> list[Path]:
    candidates = [APP_DEFAULT_EFFECT_SET_PATH]
    candidates.extend(
        path for path in _configured_builtin_effect_paths() if path.name == DEFAULT_EFFECT_SET_FILENAME
    )
    deduplicated: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if key in seen:
            continue
        deduplicated.append(candidate)
        seen.add(key)
    return deduplicated


def _configured_builtin_effect_paths() -> list[Path]:
    if not BUILD_CONFIG_PATH.is_file():
        return []

    payload = json.loads(BUILD_CONFIG_PATH.read_text(encoding="utf-8"))
    entries = payload.get("builtin-effects-discovery", [])
    if not isinstance(entries, list):
        logger.warning("Ignoring non-list build_config.json builtin-effects-discovery section")
        return []

    resolved: list[Path] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, str) or not entry.strip():
            logger.warning("Ignoring invalid build_config.json builtin-effects-discovery entry: %r", entry)
            continue
        candidate = Path(entry)
        if not candidate.is_absolute():
            candidate = (PROJECT_ROOT / candidate).resolve()
        if candidate.is_dir():
            matches = sorted(
                path.resolve()
                for path in candidate.rglob("*")
                if path.is_file() and path.suffix.lower() in {".lefx", ".lefxset"}
            )
        else:
            if not candidate.exists():
                logger.warning("Ignoring missing build_config.json builtin effect path: %s", candidate)
                continue
            matches = [candidate.resolve()]
        for match in matches:
            key = str(match)
            if key in seen:
                continue
            seen.add(key)
            resolved.append(match)
    return resolved


@dataclass(slots=True)
class EffectLibrarySource:
    source_id: str
    path: str
    kind: str
    enabled: bool = True
    autodiscovered: bool = False
    package_id: str | None = None
    package_version: int | None = None
    preset_count: int = 0
    command_count: int = 0


@dataclass(slots=True)
class RegisteredEffectType:
    registered_id: str
    definition: EffectDefinition
    effect_class: type[BaseEffect]
    source_id: str
    source_kind: str
    origin_path: str | None = None
    package_id: str | None = None
    package_version: int | None = None

    @property
    def qualified_effect_id(self) -> str:
        if "::" in self.registered_id:
            return self.registered_id
        return f"{self.source_id}::{self.definition.id}"

    @property
    def local_effect_id(self) -> str:
        return self.definition.id


class EffectRegistry:
    def __init__(self, effect_classes: Iterable[type[BaseEffect]] | None = None) -> None:
        self._manual_registrations: list[tuple[str, type[BaseEffect]]] = []
        self._configured_sources: list[EffectLibrarySource] = []
        self._discovered_sources: list[EffectLibrarySource] = []
        self._blocked_source_paths: set[str] = set()
        self._effects_by_id: dict[str, RegisteredEffectType] = {}
        self._effect_aliases: dict[str, str] = {}
        self._preset_registry = EffectPresetRegistry()
        self._command_registry = EffectCommandRegistry()

        for effect_class in effect_classes or ():
            self.register(effect_class)

    def register(self, effect_class: type[BaseEffect], source_id: str = "builtin") -> None:
        self._validate_effect_class(effect_class)
        self._manual_registrations.append((source_id, effect_class))
        self._rebuild_registry()

    def get(self, effect_id: str) -> RegisteredEffectType:
        return self._effects_by_id[self._effect_aliases.get(effect_id, effect_id)]

    def get_command(self, source_id: str, command_name: str):
        return self._command_registry.get(source_id, command_name)

    def get_preset(self, source_id: str, preset_id: str):
        return self._preset_registry.get(source_id, preset_id)

    def list_effect_ids(self) -> list[str]:
        return sorted(self._effects_by_id)

    def register_effect_source(
        self,
        path: str | Path,
        *,
        enabled: bool = True,
        source_id: str | None = None,
    ) -> EffectLibrarySource:
        suffix = Path(path).suffix.lower()
        if suffix == ".lefx":
            return self.register_effect_package(path, enabled=enabled, source_id=source_id)
        if suffix == ".lefxset":
            return self.register_effect_set(path, enabled=enabled, source_id=source_id)
        raise ValueError(f"Unsupported effect source format: {path}")

    def register_effect_package(
        self,
        path: str | Path,
        *,
        enabled: bool = True,
        source_id: str | None = None,
    ) -> EffectLibrarySource:
        source = self._upsert_effect_source(path, kind="effect_package", enabled=enabled, source_id=source_id)
        self._blocked_source_paths.discard(source.path)
        self._rebuild_registry()
        return source

    def register_effect_set(
        self,
        path: str | Path,
        *,
        enabled: bool = True,
        source_id: str | None = None,
    ) -> EffectLibrarySource:
        source = self._upsert_effect_source(path, kind="effect_set", enabled=enabled, source_id=source_id)
        self._blocked_source_paths.discard(source.path)
        self._rebuild_registry()
        return source

    def remove_source(self, source_id: str) -> None:
        retained: list[EffectLibrarySource] = []
        for source in self._configured_sources:
            if source.source_id == source_id:
                self._blocked_source_paths.add(source.path)
                continue
            retained.append(source)
        self._configured_sources = retained
        for source in self._discovered_sources:
            if source.source_id == source_id:
                self._blocked_source_paths.add(source.path)
        self._rebuild_registry()

    def list_effect_sources(self) -> list[EffectLibrarySource]:
        return sorted(
            [*self._configured_sources, *self._discovered_sources],
            key=lambda item: (item.source_id, item.path),
        )

    def list_registered_effects(self, source_id: str | None = None) -> list[RegisteredEffectType]:
        effects = list(self._effects_by_id.values())
        if source_id is not None:
            effects = [effect for effect in effects if effect.source_id == source_id]
        return sorted(effects, key=lambda item: (item.source_id, item.local_effect_id, item.registered_id))

    def get_for_source(self, source_id: str, effect_id: str) -> RegisteredEffectType:
        for effect in self.list_registered_effects(source_id):
            if effect_id in {effect.local_effect_id, effect.registered_id, effect.qualified_effect_id}:
                return effect
        raise KeyError(f"{source_id}::{effect_id}")

    def list_effect_presets(self, source_id: str | None = None, effect_id: str | None = None) -> list[dict]:
        return [preset.serialize() for preset in self._preset_registry.list_presets(source_id, effect_id)]

    def list_effect_commands(self, source_id: str | None = None) -> list[dict]:
        return [command.serialize() for command in self._command_registry.list_commands(source_id)]

    def list_effect_commands_for_effect(self, source_id: str, effect_id: str) -> list[dict]:
        registered = self.get_for_source(source_id, effect_id)
        presets = {
            preset.preset_id: preset
            for preset in self._preset_registry.list_presets(source_id, registered.local_effect_id)
        }
        items = []
        for command in self._command_registry.list_commands(source_id):
            on_action = command.on_action
            if on_action.preset_id is not None and on_action.preset_id in presets:
                items.append(command)
                continue
            if on_action.effect_id == registered.qualified_effect_id:
                items.append(command)
        return [command.serialize() for command in items]

    def reload(self) -> None:
        self._rebuild_registry()

    def _upsert_effect_source(
        self,
        path: str | Path,
        *,
        kind: str,
        enabled: bool,
        source_id: str | None,
    ) -> EffectLibrarySource:
        resolved = self._path_key(path)
        existing = self._find_configured_source_by_path(resolved)
        if existing is not None:
            existing.enabled = enabled
            existing.kind = kind
            if source_id is not None:
                existing.source_id = source_id
            return existing

        source = EffectLibrarySource(
            source_id=source_id or f"pending:{hashlib.sha1(resolved.encode('utf-8')).hexdigest()[:12]}",
            path=resolved,
            kind=kind,
            enabled=enabled,
        )
        self._configured_sources.append(source)
        return source

    def _find_configured_source_by_path(self, resolved_path: str) -> EffectLibrarySource | None:
        for source in self._configured_sources:
            if self._path_key(source.path) == resolved_path:
                return source
        return None

    def _rebuild_registry(self) -> None:
        rebuilt: dict[str, RegisteredEffectType] = {}
        presets = EffectPresetRegistry()
        commands = EffectCommandRegistry()
        discovered_sources: list[EffectLibrarySource] = []

        for source_id, effect_class in self._manual_registrations:
            self._register_effect_class(
                rebuilt,
                effect_class,
                source_id,
                source_kind="manual",
            )

        configured_paths: set[str] = set()
        for source in self._configured_sources:
            configured_paths.add(self._path_key(source.path))
            if not source.enabled:
                continue
            self._load_source_into_registry(
                source,
                rebuilt,
                presets,
                commands,
            )

        for source in self._discover_autodiscovered_sources():
            path_key = self._path_key(source.path)
            if path_key in configured_paths or path_key in self._blocked_source_paths:
                continue
            if self._source_is_already_registered(source, rebuilt):
                continue
            self._load_source_into_registry(
                source,
                rebuilt,
                presets,
                commands,
            )
            discovered_sources.append(source)

        self._effects_by_id = rebuilt
        self._effect_aliases = self._build_effect_aliases(rebuilt)
        self._preset_registry = presets
        self._command_registry = commands
        self._discovered_sources = discovered_sources

    def _load_source_into_registry(
        self,
        source: EffectLibrarySource,
        target: dict[str, RegisteredEffectType],
        preset_registry: EffectPresetRegistry,
        command_registry: EffectCommandRegistry,
    ) -> None:
        if source.kind == "effect_package":
            loaded = load_effect_package(source.path)
            self._apply_loaded_effect_package_source(source, target, preset_registry, command_registry, loaded)
            return

        if source.kind == "effect_set":
            loaded = load_effect_set(source.path)
            self._apply_loaded_effect_set_source(source, target, preset_registry, command_registry, loaded)
            return

        raise ValueError(f"Unsupported source kind: {source.kind}")

    def _apply_loaded_effect_package_source(
        self,
        source: EffectLibrarySource,
        target: dict[str, RegisteredEffectType],
        preset_registry: EffectPresetRegistry,
        command_registry: EffectCommandRegistry,
        loaded: LoadedEffectPackage,
    ) -> None:
        self._reconcile_source_identity(source, loaded.manifest.source_id)
        source.package_id = loaded.manifest.package_id
        source.package_version = loaded.manifest.version
        source.preset_count = len(loaded.presets)
        source.command_count = len(loaded.commands)
        self._register_effect_class(
            target,
            loaded.effect_class,
            loaded.manifest.source_id,
            registration_id=self._loaded_registration_id(
                loaded.manifest.source_id,
                loaded.manifest.effect_id,
                loaded.manifest.qualified_effect_id,
            ),
            source_kind=source.kind,
            origin_path=loaded.origin_path,
            package_id=loaded.manifest.package_id,
            package_version=loaded.manifest.version,
        )
        self._validate_loaded_source_bindings(
            loaded.manifest.source_id,
            {loaded.manifest.qualified_effect_id},
            loaded.presets,
            loaded.commands,
        )
        preset_registry.register_many(loaded.manifest.source_id, list(loaded.presets))
        command_registry.register_many(loaded.manifest.source_id, list(loaded.commands))

    def _apply_loaded_effect_set_source(
        self,
        source: EffectLibrarySource,
        target: dict[str, RegisteredEffectType],
        preset_registry: EffectPresetRegistry,
        command_registry: EffectCommandRegistry,
        loaded: LoadedEffectSet,
    ) -> None:
        self._reconcile_source_identity(source, loaded.manifest.source_id)
        source.package_id = loaded.manifest.set_id
        source.package_version = loaded.manifest.version
        source.preset_count = len(loaded.presets)
        source.command_count = len(loaded.commands)
        for effect in loaded.effects:
            self._register_effect_class(
                target,
                effect.effect_class,
                loaded.manifest.source_id,
                registration_id=self._loaded_registration_id(
                    loaded.manifest.source_id,
                    effect.manifest.effect_id,
                    effect.manifest.qualified_effect_id,
                ),
                source_kind=source.kind,
                origin_path=effect.origin_path,
                package_id=effect.manifest.package_id,
                package_version=effect.manifest.version,
            )
        self._validate_loaded_source_bindings(
            loaded.manifest.source_id,
            {effect.manifest.qualified_effect_id for effect in loaded.effects},
            loaded.presets,
            loaded.commands,
        )
        preset_registry.register_many(loaded.manifest.source_id, list(loaded.presets))
        command_registry.register_many(loaded.manifest.source_id, list(loaded.commands))

    def _source_is_already_registered(
        self,
        source: EffectLibrarySource,
        target: dict[str, RegisteredEffectType],
    ) -> bool:
        try:
            metadata = inspect_effect_source(source.path)
        except Exception:
            return False

        if metadata.get("kind") == "effect_package":
            effect_ids = {str(metadata.get("qualified_effect_id", "")).strip()}
        else:
            effect_ids = {str(item).strip() for item in metadata.get("effects", [])}
        effect_ids.discard("")
        if not effect_ids:
            return False

        registered = {effect.qualified_effect_id for effect in target.values()}
        if effect_ids.issubset(registered):
            logger.warning("Skipping duplicate built-in effect source %s", source.path)
            return True
        return False

    def _reconcile_source_identity(self, source: EffectLibrarySource, actual_source_id: str) -> None:
        if source.source_id.startswith("pending:"):
            source.source_id = actual_source_id
            return
        if source.source_id != actual_source_id:
            raise ValueError(
                f"Configured source id {source.source_id!r} does not match package source id {actual_source_id!r}"
            )

    def _discover_autodiscovered_sources(self) -> list[EffectLibrarySource]:
        sources: list[EffectLibrarySource] = []
        seen_paths: set[str] = set()
        for root in (Path(APP_EFFECT_PACKAGES_ROOT),):
            if not root.exists():
                continue
            discovered_paths = sorted(
                root.rglob("*"),
                key=lambda item: (item.suffix.lower() != ".lefxset", str(item).lower()),
            )
            for path in discovered_paths:
                if not path.is_file():
                    continue
                if path.suffix.lower() not in {".lefx", ".lefxset"}:
                    continue
                resolved_path = self._path_key(path)
                if resolved_path in seen_paths:
                    continue
                seen_paths.add(resolved_path)
                sources.append(
                    EffectLibrarySource(
                        source_id=f"pending:{hashlib.sha1(str(path.resolve()).encode('utf-8')).hexdigest()[:12]}",
                        path=resolved_path,
                        kind="effect_package" if path.suffix.lower() == ".lefx" else "effect_set",
                        enabled=True,
                        autodiscovered=True,
                    )
                )
        return sources

    def _validate_loaded_source_bindings(
        self,
        source_id: str,
        source_effect_ids: set[str],
        presets,
        commands,
    ) -> None:
        preset_map = {preset.preset_id: preset for preset in presets}
        for preset in presets:
            if preset.qualified_effect_id not in source_effect_ids:
                raise ValueError(
                    f"Preset {preset.preset_id!r} references unknown effect {preset.qualified_effect_id!r} in source {source_id!r}"
                )
        for command in commands:
            for action in (command.on_action, command.off_action):
                if action is None or action.action == "clear_layer":
                    continue
                if action.preset_id is not None:
                    preset = preset_map.get(action.preset_id)
                    if preset is None:
                        raise ValueError(
                            f"Command {command.command_name!r} references unknown preset {action.preset_id!r} in source {source_id!r}"
                        )
                    if preset.qualified_effect_id not in source_effect_ids:
                        raise ValueError(
                            f"Command {command.command_name!r} targets preset {action.preset_id!r} for unknown effect {preset.qualified_effect_id!r}"
                        )
                    continue
                if action.effect_id is not None and action.effect_id not in source_effect_ids:
                    raise ValueError(
                        f"Command {command.command_name!r} references unknown effect {action.effect_id!r} in source {source_id!r}"
                    )

    def _loaded_registration_id(self, source_id: str, local_effect_id: str, qualified_effect_id: str) -> str:
        if source_id == DEFAULT_EFFECT_SOURCE_ID:
            return local_effect_id
        return qualified_effect_id

    def _build_effect_aliases(self, registered: dict[str, RegisteredEffectType]) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for registered_id, effect in registered.items():
            if "::" in registered_id:
                continue
            qualified_id = effect.qualified_effect_id
            if qualified_id == registered_id:
                continue
            if qualified_id in registered:
                continue
            existing = aliases.get(qualified_id)
            if existing is not None and existing != registered_id:
                raise ValueError(
                    f"Duplicate effect alias detected: {qualified_id} (registrations: {existing}, {registered_id})"
                )
            aliases[qualified_id] = registered_id
        return aliases

    def _register_effect_class(
        self,
        target: dict[str, RegisteredEffectType],
        effect_class: type[BaseEffect],
        source_id: str,
        *,
        registration_id: str | None = None,
        source_kind: str,
        origin_path: str | None = None,
        package_id: str | None = None,
        package_version: int | None = None,
    ) -> None:
        self._validate_effect_class(effect_class)
        definition = effect_class.get_definition()
        registered_id = registration_id or definition.id
        if registered_id in target:
            existing = target[registered_id]
            raise ValueError(
                f"Duplicate effect id detected: {registered_id} "
                f"(sources: {existing.source_id}, {source_id})"
            )
        target[registered_id] = RegisteredEffectType(
            registered_id=registered_id,
            definition=definition,
            effect_class=effect_class,
            source_id=source_id,
            source_kind=source_kind,
            origin_path=origin_path,
            package_id=package_id,
            package_version=package_version,
        )

    def _validate_effect_class(self, effect_class: type[BaseEffect]) -> None:
        if not inspect.isclass(effect_class) or not issubclass(effect_class, BaseEffect):
            raise TypeError(f"{effect_class!r} is not a BaseEffect subclass")

        definition = effect_class.get_definition()
        if not _EFFECT_ID_RE.match(definition.id):
            raise ValueError(f"Effect id must be snake_case, got {definition.id!r}")

        if not isinstance(definition.capabilities, EffectCapabilities):
            raise TypeError(f"Effect {definition.id!r} capabilities are invalid")

        for key, value in definition.parameter_schema.items():
            if not isinstance(value, EffectParamDefinition):
                raise TypeError(f"Effect {definition.id!r} parameter {key!r} is invalid")
            if key != value.name:
                raise ValueError(
                    f"Effect {definition.id!r} parameter schema key/name mismatch: {key!r} != {value.name!r}"
                )

        for key, value in definition.layer_rules.items():
            if not isinstance(value, LayerRule):
                raise TypeError(f"Effect {definition.id!r} layer rule for {key!r} is invalid")

    def _path_key(self, path: str | Path) -> str:
        return str(Path(path).resolve())


def build_default_effect_registry() -> EffectRegistry:
    registry = EffectRegistry()
    errors: list[str] = []
    default_artifact_path: Path | None = None
    for artifact_path in _default_effect_artifact_candidates():
        if not artifact_path.is_file():
            continue
        try:
            registry.register_effect_set(artifact_path, source_id=DEFAULT_EFFECT_SOURCE_ID)
            default_artifact_path = artifact_path.resolve()
            break
        except Exception as exc:
            errors.append(f"{artifact_path}: {exc}")
            continue
    if default_artifact_path is None:
        if errors:
            raise RuntimeError(
                "Failed to load the default effect set artifact. "
                + " | ".join(errors)
            )
        candidates = ", ".join(str(path) for path in _default_effect_artifact_candidates())
        raise FileNotFoundError(f"Default effect set artifact not found. Checked: {candidates}")

    for builtin_path in _configured_builtin_effect_paths():
        if not builtin_path.is_file():
            continue
        if builtin_path.resolve() == default_artifact_path:
            continue
        try:
            metadata = inspect_effect_source(builtin_path)
            if metadata.get("source_id") == DEFAULT_EFFECT_SOURCE_ID:
                continue
            registry.register_effect_source(builtin_path)
        except Exception as exc:
            errors.append(f"{builtin_path}: {exc}")

    if errors:
        raise RuntimeError(
            "Failed to load one or more configured built-in effect sources. "
            + " | ".join(errors)
        )
    return registry
