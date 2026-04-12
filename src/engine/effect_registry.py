from __future__ import annotations

import hashlib
import importlib
import importlib.util
import inspect
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Iterable

from ..core.effect_schema import BaseEffect, EffectCapabilities, EffectDefinition, EffectParamDefinition, LayerRule
from ..infrastructure.paths import EFFECTS_LIBRARY_ROOT, EFFECT_PACKAGES_ROOT, PROJECT_ROOT
from .effect_command_registry import EffectCommandRegistry
from .effect_package_loader import LoadedEffectPackage, LoadedEffectSet, load_effect_package, load_effect_set
from .effect_preset_registry import EffectPresetRegistry


_EFFECT_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


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
        self._preset_registry = EffectPresetRegistry()
        self._command_registry = EffectCommandRegistry()

        for effect_class in effect_classes or ():
            self.register(effect_class)

    def register_builtin_effects(
        self,
        source_id: str = "default-effects",
        path: str | Path | None = None,
    ) -> EffectLibrarySource:
        source = self.add_library_path(path or EFFECTS_LIBRARY_ROOT, enabled=True, source_id=source_id)
        self._rebuild_registry()
        return source

    def register(self, effect_class: type[BaseEffect], source_id: str = "builtin") -> None:
        self._validate_effect_class(effect_class)
        self._manual_registrations.append((source_id, effect_class))
        self._rebuild_registry()

    def get(self, effect_id: str) -> RegisteredEffectType:
        return self._effects_by_id[effect_id]

    def get_command(self, source_id: str, command_name: str):
        return self._command_registry.get(source_id, command_name)

    def get_preset(self, source_id: str, preset_id: str):
        return self._preset_registry.get(source_id, preset_id)

    def list_effect_ids(self) -> list[str]:
        return sorted(self._effects_by_id)

    def add_library_path(
        self,
        path: str | Path,
        *,
        enabled: bool = True,
        source_id: str | None = None,
    ) -> EffectLibrarySource:
        resolved = self._path_key(path)
        existing = self._find_configured_source_by_path(resolved)
        if existing is not None:
            existing.enabled = enabled
            if source_id is not None:
                existing.source_id = source_id
            return existing

        source = EffectLibrarySource(
            source_id=source_id or f"library:{hashlib.sha1(resolved.encode('utf-8')).hexdigest()[:12]}",
            path=resolved,
            kind="library_path",
            enabled=enabled,
        )
        self._configured_sources.append(source)
        return source

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

    def list_library_sources(self) -> list[EffectLibrarySource]:
        return list(self.list_effect_sources())

    def list_effect_presets(self, source_id: str | None = None, effect_id: str | None = None) -> list[dict]:
        return [preset.serialize() for preset in self._preset_registry.list_presets(source_id, effect_id)]

    def list_effect_commands(self, source_id: str | None = None) -> list[dict]:
        return [command.serialize() for command in self._command_registry.list_commands(source_id)]

    def reload(self) -> None:
        self._rebuild_registry(reload_modules=True)

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

    def _rebuild_registry(self, *, reload_modules: bool = False) -> None:
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
                reload_modules=reload_modules,
            )

        for source in self._discover_autodiscovered_sources():
            path_key = self._path_key(source.path)
            if path_key in configured_paths or path_key in self._blocked_source_paths:
                continue
            self._load_source_into_registry(
                source,
                rebuilt,
                presets,
                commands,
                reload_modules=reload_modules,
            )
            discovered_sources.append(source)

        self._effects_by_id = rebuilt
        self._preset_registry = presets
        self._command_registry = commands
        self._discovered_sources = discovered_sources

    def _load_source_into_registry(
        self,
        source: EffectLibrarySource,
        target: dict[str, RegisteredEffectType],
        preset_registry: EffectPresetRegistry,
        command_registry: EffectCommandRegistry,
        *,
        reload_modules: bool,
    ) -> None:
        if source.kind == "library_path":
            source.package_id = None
            source.package_version = None
            source.preset_count = 0
            source.command_count = 0
            for effect_class in self._discover_effect_classes(Path(source.path), reload_modules=reload_modules):
                self._register_effect_class(
                    target,
                    effect_class,
                    source.source_id,
                    source_kind=source.kind,
                    origin_path=source.path,
                )
            return

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
            registration_id=loaded.manifest.qualified_effect_id,
            source_kind=source.kind,
            origin_path=loaded.origin_path,
            package_id=loaded.manifest.package_id,
            package_version=loaded.manifest.version,
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
                registration_id=effect.manifest.qualified_effect_id,
                source_kind=source.kind,
                origin_path=effect.origin_path,
                package_id=effect.manifest.package_id,
                package_version=effect.manifest.version,
            )
        preset_registry.register_many(loaded.manifest.source_id, list(loaded.presets))
        command_registry.register_many(loaded.manifest.source_id, list(loaded.commands))

    def _reconcile_source_identity(self, source: EffectLibrarySource, actual_source_id: str) -> None:
        if source.source_id.startswith("pending:"):
            source.source_id = actual_source_id
            return
        if source.source_id != actual_source_id:
            raise ValueError(
                f"Configured source id {source.source_id!r} does not match package source id {actual_source_id!r}"
            )

    def _discover_autodiscovered_sources(self) -> list[EffectLibrarySource]:
        root = Path(EFFECT_PACKAGES_ROOT)
        if not root.exists():
            return []
        sources: list[EffectLibrarySource] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".lefx", ".lefxset"}:
                continue
            sources.append(
                EffectLibrarySource(
                    source_id=f"pending:{hashlib.sha1(str(path.resolve()).encode('utf-8')).hexdigest()[:12]}",
                    path=self._path_key(path),
                    kind="effect_package" if path.suffix.lower() == ".lefx" else "effect_set",
                    enabled=True,
                    autodiscovered=True,
                )
            )
        return sources

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

    def _discover_effect_classes(self, root: Path, *, reload_modules: bool = False) -> list[type[BaseEffect]]:
        if not root.exists():
            return []

        module_files = sorted(
            path
            for path in root.rglob("*.py")
            if "__pycache__" not in path.parts and path.name != "__init__.py"
        )
        discovered: list[type[BaseEffect]] = []
        seen: set[type[BaseEffect]] = set()
        for module_file in module_files:
            module = self._load_module(module_file, reload_module=reload_modules)
            for effect_class in self._effect_classes_from_module(module):
                if effect_class not in seen:
                    discovered.append(effect_class)
                    seen.add(effect_class)
        return discovered

    def _load_module(self, module_path: Path, *, reload_module: bool = False) -> ModuleType:
        project_module_name = self._project_module_name(module_path)
        if project_module_name is not None:
            importlib.invalidate_caches()
            if project_module_name in sys.modules:
                if reload_module:
                    return importlib.reload(sys.modules[project_module_name])
                return sys.modules[project_module_name]
            return importlib.import_module(project_module_name)

        unique_name = f"respeaker_effect_{hashlib.sha1(str(module_path).encode('utf-8')).hexdigest()}"
        spec = importlib.util.spec_from_file_location(unique_name, module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load effect module from {module_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[unique_name] = module
        spec.loader.exec_module(module)
        return module

    def _project_module_name(self, module_path: Path) -> str | None:
        try:
            relative = module_path.resolve().relative_to(PROJECT_ROOT.resolve())
        except ValueError:
            return None

        if relative.suffix != ".py":
            return None

        module_parts = list(relative.with_suffix("").parts)
        if not module_parts:
            return None
        if module_parts[-1] == "__init__":
            module_parts = module_parts[:-1]
        return ".".join(module_parts) if module_parts else None

    def _effect_classes_from_module(self, module: ModuleType) -> list[type[BaseEffect]]:
        effect_classes: list[type[BaseEffect]] = []
        for value in module.__dict__.values():
            if not inspect.isclass(value):
                continue
            if value is BaseEffect:
                continue
            if not issubclass(value, BaseEffect):
                continue
            if inspect.isabstract(value):
                continue
            effect_classes.append(value)
        return effect_classes

    def _validate_effect_class(self, effect_class: type[BaseEffect]) -> None:
        if not inspect.isclass(effect_class) or not issubclass(effect_class, BaseEffect):
            raise TypeError(f"Expected BaseEffect subclass, got {effect_class!r}")

        definition = getattr(effect_class, "definition", None)
        if not isinstance(definition, EffectDefinition):
            raise TypeError(f"{effect_class.__name__} must define an EffectDefinition in 'definition'")

        if not definition.id or not _EFFECT_ID_RE.match(definition.id):
            raise ValueError(
                f"Effect id must be snake_case and start with a lowercase letter: {definition.id!r}"
            )
        if not definition.title.strip():
            raise ValueError(f"Effect {definition.id!r} must define a non-empty title")
        if not definition.description.strip():
            raise ValueError(f"Effect {definition.id!r} must define a non-empty description")
        if definition.version < 1:
            raise ValueError(f"Effect {definition.id!r} must have version >= 1")

        if not isinstance(definition.capabilities, EffectCapabilities):
            raise TypeError(f"Effect {definition.id!r} has invalid capabilities")

        for key, value in definition.parameter_schema.items():
            if key != value.name:
                raise ValueError(
                    f"Effect {definition.id!r} parameter schema key/name mismatch: {key!r} != {value.name!r}"
                )
            if not isinstance(value, EffectParamDefinition):
                raise TypeError(f"Effect {definition.id!r} parameter {key!r} is invalid")

        for key, value in definition.layer_rules.items():
            if not isinstance(value, LayerRule):
                raise TypeError(f"Effect {definition.id!r} layer rule for {key!r} is invalid")

    def _path_key(self, path: str | Path) -> str:
        return str(Path(path).resolve())


def build_default_effect_registry() -> EffectRegistry:
    registry = EffectRegistry()
    registry.register_builtin_effects()
    return registry
