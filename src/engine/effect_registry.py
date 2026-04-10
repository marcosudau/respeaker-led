from __future__ import annotations

import importlib
import hashlib
import importlib.util
import inspect
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Iterable

from ..core.effect_schema import BaseEffect, EffectCapabilities, EffectDefinition, EffectParamDefinition, LayerRule
from ..infrastructure.paths import EFFECTS_LIBRARY_ROOT, PROJECT_ROOT


_EFFECT_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(slots=True)
class EffectLibrarySource:
    source_id: str
    path: str
    kind: str
    enabled: bool = True


@dataclass(slots=True)
class RegisteredEffectType:
    definition: EffectDefinition
    effect_class: type[BaseEffect]
    source_id: str


class EffectRegistry:
    def __init__(self, effect_classes: Iterable[type[BaseEffect]] | None = None) -> None:
        self._manual_registrations: list[tuple[str, type[BaseEffect]]] = []
        self._library_sources: list[EffectLibrarySource] = []
        self._effects_by_id: dict[str, RegisteredEffectType] = {}

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

    def list_effect_ids(self) -> list[str]:
        return sorted(self._effects_by_id)

    def add_library_path(
        self,
        path: str | Path,
        *,
        enabled: bool = True,
        source_id: str | None = None,
    ) -> EffectLibrarySource:
        resolved = str(Path(path).resolve())
        for source in self._library_sources:
            if Path(source.path).resolve() == Path(resolved):
                source.enabled = enabled
                if source_id is not None:
                    source.source_id = source_id
                return source

        source = EffectLibrarySource(
            source_id=source_id or f"library:{hashlib.sha1(resolved.encode('utf-8')).hexdigest()[:12]}",
            path=resolved,
            kind="library_path",
            enabled=enabled,
        )
        self._library_sources.append(source)
        return source

    def list_library_sources(self) -> list[EffectLibrarySource]:
        return list(self._library_sources)

    def reload(self) -> None:
        self._rebuild_registry(reload_modules=True)

    def _rebuild_registry(self, *, reload_modules: bool = False) -> None:
        rebuilt: dict[str, RegisteredEffectType] = {}

        for source_id, effect_class in self._manual_registrations:
            self._register_effect_class(rebuilt, effect_class, source_id)

        for source in self._library_sources:
            if not source.enabled:
                continue
            for effect_class in self._discover_effect_classes(Path(source.path), reload_modules=reload_modules):
                self._register_effect_class(rebuilt, effect_class, source.source_id)

        self._effects_by_id = rebuilt

    def _register_effect_class(
        self,
        target: dict[str, RegisteredEffectType],
        effect_class: type[BaseEffect],
        source_id: str,
    ) -> None:
        self._validate_effect_class(effect_class)
        definition = effect_class.get_definition()
        if definition.id in target:
            existing = target[definition.id]
            raise ValueError(
                f"Duplicate effect id detected: {definition.id} "
                f"(sources: {existing.source_id}, {source_id})"
            )
        target[definition.id] = RegisteredEffectType(
            definition=definition,
            effect_class=effect_class,
            source_id=source_id,
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


def build_default_effect_registry() -> EffectRegistry:
    registry = EffectRegistry()
    registry.register_builtin_effects()
    return registry
