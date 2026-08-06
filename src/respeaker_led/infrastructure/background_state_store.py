from __future__ import annotations

import json
from pathlib import Path

from ..core.effect_schema import LayerId, PersistedLayerState, parse_layer_id


BACKGROUND_STATE_SCHEMA_VERSION = 1


def load_background_state(path: str | Path) -> PersistedLayerState | None:
    file_path = Path(path)
    if not file_path.exists():
        return None

    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    try:
        schema_version = int(payload.get("schema_version", 0))
        layer_id = parse_layer_id(payload.get("layer_id"))
        effect_id = str(payload.get("effect_id", "")).strip()
        params = payload.get("params", {})
        enabled = bool(payload.get("enabled", True))
        transparent = bool(payload.get("transparent", False))
        saved_at = float(payload.get("saved_at", 0.0))
    except (TypeError, ValueError):
        return None

    if schema_version != BACKGROUND_STATE_SCHEMA_VERSION:
        return None
    if layer_id is not LayerId.BACKGROUND_STATE_LAYER:
        return None
    if not effect_id or not isinstance(params, dict):
        return None

    return PersistedLayerState(
        schema_version=BACKGROUND_STATE_SCHEMA_VERSION,
        layer_id=LayerId.BACKGROUND_STATE_LAYER,
        effect_id=effect_id,
        params=dict(params),
        enabled=enabled,
        transparent=transparent,
        saved_at=saved_at,
    )


def save_background_state(path: str | Path, state: PersistedLayerState | None) -> None:
    file_path = Path(path)
    if state is None:
        if file_path.exists():
            file_path.unlink()
        return

    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": int(state.schema_version),
        "layer_id": state.layer_id.value,
        "effect_id": state.effect_id,
        "params": dict(state.params),
        "enabled": bool(state.enabled),
        "transparent": bool(state.transparent),
        "saved_at": float(state.saved_at),
    }
    file_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")