from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from .adapters import ConsolePreviewAdapter, FrameAdapter
from .color_math import scale_color
from .composer import SceneComposer
from .effects2 import blink, dynamic_frame, progress, pulse, ring_frame, solid
from .layers import LayerStore
from .models import BaseState, CountdownState, Event, Frame, MainLayerState, Scene, StateLayerState
from .preset_loader import PresetRegistry
from .renderer import SceneRenderer
from .spec_utils import parse_hex_color


DEFAULT_EVENT_PRIORITIES = {
    "error_flash": 900,
    "timeout_imminent": 800,
    "wakeword_ack": 725,
    "trigger_received": 700,
    "warning": 600,
    "text_committed": 500,
    "notification": 400,
}
DEFAULT_EVENT_DURATIONS_MS = {
    "error_flash": 1800,
    "timeout_imminent": 1500,
    "wakeword_ack": 900,
    "trigger_received": 900,
    "warning": 1400,
    "text_committed": 1200,
    "notification": 1000,
}


TickCallback = Callable[["ControllerRuntime", float], None]


def _normalize_name(value: str, fallback: str) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    return text or fallback


def _copy_payload(payload: dict | None) -> dict:
    return dict(payload or {})


def _timestamp_or_now(timestamp: float | None) -> float:
    return time.monotonic() if timestamp is None else float(timestamp)


class ControllerRuntime:
    def __init__(self, adapter: FrameAdapter | None = None, preset_registry: PresetRegistry | None = None) -> None:
        self.store = LayerStore()
        self.composer = SceneComposer()
        self.renderer = SceneRenderer()
        self.adapter = adapter or ConsolePreviewAdapter()
        self.presets = preset_registry or PresetRegistry.empty()
        self.last_scene: Scene | None = None
        self.last_frame: Frame | None = None
        self.active_preset_id: str | None = None
        self.reset(initial_state="idle")

    def set_state_layer(self, state_layer: StateLayerState) -> None:
        self.store.state_layer = state_layer

    def set_state_visual(self, visual, *, mode: str = "custom", enabled: bool = True) -> None:
        self.store.state_layer = StateLayerState(mode=mode, visual=visual, enabled=enabled)

    def clear_state_layer(self) -> None:
        self.store.state_layer = StateLayerState(mode="off", visual=None, enabled=False)

    def set_main_layer(self, main_layer: MainLayerState | None) -> None:
        self.store.main_layer = main_layer

    def set_active_visual(
        self,
        *,
        layer_id: str,
        mode: str,
        visual,
        payload: dict | None = None,
        valid: bool = True,
        updated_at: float | None = None,
    ) -> None:
        self.store.main_layer = MainLayerState(
            id=layer_id,
            mode=mode,
            payload=payload or {},
            visual=visual,
            valid=valid,
            updated_at=time.monotonic() if updated_at is None else updated_at,
        )

    def set_main_visual(
        self,
        *,
        layer_id: str,
        mode: str,
        visual,
        payload: dict | None = None,
        valid: bool = True,
        updated_at: float | None = None,
    ) -> None:
        self.set_active_visual(
            layer_id=layer_id,
            mode=mode,
            visual=visual,
            payload=payload,
            valid=valid,
            updated_at=updated_at,
        )

    def clear_active_visual(self) -> None:
        self.store.main_layer = None
        self.active_preset_id = None

    def clear_main_layer(self) -> None:
        self.clear_active_visual()

    def set_state(self, state_name: str, payload: dict | None = None, *, timestamp: float | None = None) -> None:
        now = _timestamp_or_now(timestamp)
        name = _normalize_name(state_name, "idle")
        payload = _copy_payload(payload)
        self.active_preset_id = None
        self.store.base_state = BaseState(name=name, payload=payload, updated_at=now)
        state_layer, active_visual = self._build_base_state_layers(name, payload, now)
        self.store.state_layer = state_layer
        self.store.main_layer = active_visual

    def clear_state(self, state_name: str | None = None, *, timestamp: float | None = None) -> None:
        normalized = None if state_name is None else _normalize_name(state_name, "")
        if normalized and normalized != self.store.base_state.name:
            return
        self.set_state("idle", timestamp=timestamp)

    def emit_event(self, event_name: str, payload: dict | None = None, *, timestamp: float | None = None) -> Event:
        now = _timestamp_or_now(timestamp)
        name = _normalize_name(event_name, "notification")
        payload = _copy_payload(payload)
        duration_ms = payload.get("duration_ms", DEFAULT_EVENT_DURATIONS_MS.get(name, 1000))
        duration = None if duration_ms is None else max(0, int(duration_ms)) / 1000.0
        priority = int(payload.get("priority", DEFAULT_EVENT_PRIORITIES.get(name, 300)))
        event_id = str(payload.get("event_id", f"{name}-{int(now * 1000)}"))
        created_at = float(payload.get("created_at", payload.get("timestamp", now)))
        visual = self._build_event_visual(name, payload)
        event = Event(
            id=event_id,
            name=name,
            visual=visual,
            payload=payload,
            priority=priority,
            created_at=created_at,
            duration=duration,
            exclusive=visual.exclusive,
        )
        self.push_event(event)
        return event

    def start_timeout_countdown(
        self,
        total_ms: int,
        remaining_ms: int | None = None,
        *,
        follow_up_state: str | None = None,
        payload: dict | None = None,
        timestamp: float | None = None,
    ) -> None:
        now = _timestamp_or_now(timestamp)
        total_ms = max(1, int(total_ms))
        remaining_ms = total_ms if remaining_ms is None else max(0, min(int(remaining_ms), total_ms))
        payload = _copy_payload(payload)
        self.store.countdown = CountdownState(
            total_ms=total_ms,
            remaining_ms=remaining_ms,
            started_at=now,
            deadline=now + (remaining_ms / 1000.0),
            follow_up_state=None if follow_up_state is None else _normalize_name(follow_up_state, ""),
            payload=payload,
        )
        self.store.countdown_visual = dynamic_frame(
            lambda current_now, runtime=self: runtime._render_countdown_overlay(current_now),
            exclusive=False,
        )

    def update_timeout_countdown(self, remaining_ms: int, *, timestamp: float | None = None) -> None:
        if self.store.countdown is None:
            raise ValueError("No active countdown")
        now = _timestamp_or_now(timestamp)
        self.store.countdown.remaining_ms = max(0, min(int(remaining_ms), self.store.countdown.total_ms))
        self.store.countdown.started_at = now
        self.store.countdown.deadline = now + (self.store.countdown.remaining_ms / 1000.0)
        self.store.countdown.active = True

    def cancel_timeout_countdown(self) -> None:
        self.store.countdown = None
        self.store.countdown_visual = None

    def set_direction(self, direction_deg: float) -> None:
        normalized = float(direction_deg) % 360.0
        self.store.direction_deg = normalized
        self.store.direction_visual = self._build_direction_visual(normalized)

    def clear_direction(self) -> None:
        self.store.direction_deg = None
        self.store.direction_visual = None

    def set_brightness(self, level: float) -> None:
        self.store.brightness = max(0.0, min(1.0, float(level)))

    def set_enabled(self, enabled: bool) -> None:
        self.store.enabled = bool(enabled)

    def reset(self, *, initial_state: str = "idle") -> None:
        self.store.event_layer.clear()
        self.store.countdown = None
        self.store.countdown_visual = None
        self.store.direction_deg = None
        self.store.direction_visual = None
        self.store.brightness = 1.0
        self.store.enabled = True
        self.active_preset_id = None
        self.set_state(initial_state, timestamp=time.monotonic())

    def apply_preset(self, preset_id: str, spec: dict) -> None:
        preset = self.presets.get_by_id(preset_id)
        result = preset.build_preset(spec)
        self.active_preset_id = result.preset_id
        if result.state_visual is not None:
            self.set_state_visual(result.state_visual, mode=result.state_mode)
        self.set_active_visual(
            layer_id=result.preset_id,
            mode=result.mode,
            visual=result.visual,
            payload=result.payload,
            valid=result.valid,
        )

    def apply_preset_from_file(self, preset_id: str, spec_file: str | Path) -> None:
        spec = json.loads(Path(spec_file).read_text(encoding="utf-8"))
        self.apply_preset(preset_id, spec)

    def set_progress(self, value: float, *, color: int = 0x3399FF, base_color: int = 0x03070B) -> None:
        self.set_state("transcribing", payload={"source": "progress"})
        self.set_active_visual(
            layer_id="progress",
            mode="progress",
            visual=progress(value, color=color, base_color=base_color),
            payload={"value": value},
        )

    def push_event(self, event: Event) -> None:
        self.store.event_layer.enqueue(event)

    def push_event_visual(
        self,
        *,
        event_id: str,
        kind: str,
        visual,
        priority: int = 100,
        duration: float | None = 3.0,
        exclusive: bool | None = None,
        created_at: float | None = None,
    ) -> None:
        created_at = time.monotonic() if created_at is None else created_at
        self.store.event_layer.enqueue(
            Event(
                id=event_id,
                name=kind,
                visual=visual,
                priority=priority,
                created_at=created_at,
                duration=duration,
                exclusive=visual.exclusive if exclusive is None else exclusive,
            )
        )

    def clear_event_layer(self) -> None:
        self.store.event_layer.clear()

    def render_once(self, now: float | None = None) -> tuple[Scene, Frame]:
        now = time.monotonic() if now is None else now
        self._refresh_automations(now)
        scene = self.composer.compose(self.store, now)
        frame = self.renderer.render(scene)
        frame = self._apply_output_settings(frame)
        self.adapter.apply_frame(frame)
        self.last_scene = scene
        self.last_frame = frame
        return scene, frame

    def run(self, *, seconds: float | None = None, fps: float = 12.0, tick: TickCallback | None = None) -> None:
        interval = 1.0 / max(1.0, fps)
        deadline = None if seconds is None else time.monotonic() + seconds
        while True:
            now = time.monotonic()
            if tick is not None:
                tick(self, now)
            self.render_once(now)
            if deadline is not None and now >= deadline:
                break
            time.sleep(interval)

    def close(self) -> None:
        self.adapter.close()

    def get_status(self, now: float | None = None) -> dict:
        now = time.monotonic() if now is None else now
        countdown = self.store.countdown
        current_event = self.store.event_layer.current_event
        pending_events = self.store.event_layer.pending_events
        return {
            "base_state": {
                "name": self.store.base_state.name,
                "payload": self._sanitize_value(self.store.base_state.payload),
                "updated_at": self.store.base_state.updated_at,
            },
            "active_visual": None
            if self.store.main_layer is None
            else {
                "id": self.store.main_layer.id,
                "mode": self.store.main_layer.mode,
                "payload": self._sanitize_value(self.store.main_layer.payload),
                "updated_at": self.store.main_layer.updated_at,
                "valid": self.store.main_layer.valid,
                "visual": self._serialize_visual(self.store.main_layer.visual),
            },
            "active_preset_id": self.active_preset_id,
            "direction_deg": self.store.direction_deg,
            "brightness": self.store.brightness,
            "enabled": self.store.enabled,
            "countdown": None
            if countdown is None
            else {
                "total_ms": countdown.total_ms,
                "remaining_ms": countdown.remaining_at(now),
                "follow_up_state": countdown.follow_up_state,
                "active": countdown.active,
                "payload": self._sanitize_value(countdown.payload),
            },
            "event_overlay": {
                "current": None if current_event is None else self._serialize_event(current_event),
                "pending": [self._serialize_event(event) for event in pending_events],
            },
            "render_layers": {
                "state_visual": self._serialize_visual(self.store.state_layer.visual),
                "direction_visual": self._serialize_visual(self.store.direction_visual),
                "countdown_visual": self._serialize_visual(self.store.countdown_visual),
            },
            "last_scene": self._serialize_scene(self.last_scene),
            "last_frame": self._serialize_frame(self.last_frame),
        }

    def _build_base_state_layers(self, state_name: str, payload: dict, now: float) -> tuple[StateLayerState, MainLayerState | None]:
        accent = parse_hex_color(payload.get("color"), self._default_state_color(state_name))
        background = parse_hex_color(payload.get("base_color"), self._default_background_color(state_name))
        if state_name == "offline":
            return StateLayerState(mode="offline", visual=solid(background), enabled=True), MainLayerState(
                id="base-state:offline",
                mode="offline",
                payload=payload,
                visual=blink(accent, base_color=background, period=1.2, duty_cycle=0.25, exclusive=False),
                updated_at=now,
            )
        if state_name == "idle":
            return StateLayerState(mode="idle", visual=solid(background), enabled=True), None
        if state_name == "listening":
            return StateLayerState(mode="listening", visual=solid(background), enabled=True), MainLayerState(
                id="base-state:listening",
                mode="listening",
                payload=payload,
                visual=pulse(accent, base_color=background, period=1.8, exclusive=False),
                updated_at=now,
            )
        if state_name == "recording":
            return StateLayerState(mode="recording", visual=solid(background), enabled=True), MainLayerState(
                id="base-state:recording",
                mode="recording",
                payload=payload,
                visual=pulse(accent, base_color=background, period=1.1, exclusive=False),
                updated_at=now,
            )
        if state_name in {"transcribing", "processing"}:
            return StateLayerState(mode=state_name, visual=solid(background), enabled=True), MainLayerState(
                id=f"base-state:{state_name}",
                mode=state_name,
                payload=payload,
                visual=pulse(accent, base_color=background, period=1.4, exclusive=False),
                updated_at=now,
            )
        if state_name == "error":
            return StateLayerState(mode="error", visual=solid(background), enabled=True), MainLayerState(
                id="base-state:error",
                mode="error",
                payload=payload,
                visual=blink(accent, base_color=background, period=0.7, duty_cycle=0.55, exclusive=False),
                updated_at=now,
            )
        return StateLayerState(mode=state_name, visual=solid(background), enabled=True), MainLayerState(
            id=f"base-state:{state_name}",
            mode=state_name,
            payload=payload,
            visual=pulse(accent, base_color=background, period=float(payload.get("period", 1.6)), exclusive=False),
            updated_at=now,
        )

    def _build_event_visual(self, event_name: str, payload: dict):
        accent = parse_hex_color(payload.get("color"), self._default_event_color(event_name))
        background = parse_hex_color(payload.get("base_color"), self._default_event_background(event_name))
        if event_name in {"trigger_received", "wakeword_ack"}:
            return blink(accent, base_color=background, period=0.5, duty_cycle=0.35, exclusive=False)
        if event_name == "text_committed":
            return blink(accent, base_color=background, period=0.75, duty_cycle=0.55, exclusive=False)
        if event_name == "error_flash":
            return blink(accent, base_color=background, period=0.35, duty_cycle=0.6, exclusive=True)
        if event_name == "timeout_imminent":
            return blink(accent, base_color=background, period=0.4, duty_cycle=0.5, exclusive=False)
        if event_name == "warning":
            return blink(accent, base_color=background, period=0.8, duty_cycle=0.5, exclusive=False)
        return blink(accent, base_color=background, period=0.9, duty_cycle=0.45, exclusive=False)

    def _build_direction_visual(self, direction_deg: float):
        center = int(round((direction_deg % 360.0) / 360.0 * 12.0)) % 12
        colors = [None] * 12
        for offset, color in ((0, 0xEAF8FF), (-1, 0x7FC9FF), (1, 0x7FC9FF)):
            colors[(center + offset) % 12] = color
        return ring_frame(colors, exclusive=False)

    def _render_countdown_overlay(self, now: float):
        countdown = self.store.countdown
        if countdown is None:
            return [None] * 12
        active_leds = max(0, min(12, int(round(countdown.progress_at(now) * 12.0))))
        colors = [None] * 12
        for index in range(active_leds):
            colors[index] = 0xFF9F1A
        if active_leds < 12:
            colors[active_leds % 12] = 0xFFF3D1
        return colors

    def _refresh_automations(self, now: float) -> None:
        countdown = self.store.countdown
        if countdown is not None and countdown.is_expired(now):
            follow_up_state = countdown.follow_up_state
            self.cancel_timeout_countdown()
            if follow_up_state:
                self.set_state(follow_up_state, timestamp=now)

    def _apply_output_settings(self, frame: Frame) -> Frame:
        leds = list(frame.leds)
        if not self.store.enabled:
            leds = [0] * len(leds)
        elif self.store.brightness < 1.0:
            leds = [scale_color(color, self.store.brightness) for color in leds]
        return Frame(leds=leds, timestamp=frame.timestamp)

    def _default_state_color(self, state_name: str) -> int:
        return {
            "offline": 0x6A0F0F,
            "idle": 0x10263D,
            "listening": 0x1AA7FF,
            "recording": 0x19D37A,
            "transcribing": 0xFFB347,
            "processing": 0xFFB347,
            "error": 0xFF3B30,
        }.get(state_name, 0x7AA4FF)

    def _default_background_color(self, state_name: str) -> int:
        return {
            "offline": 0x080101,
            "idle": 0x010408,
            "listening": 0x020810,
            "recording": 0x031108,
            "transcribing": 0x120A02,
            "processing": 0x120A02,
            "error": 0x120103,
        }.get(state_name, 0x060812)

    def _default_event_color(self, event_name: str) -> int:
        return {
            "trigger_received": 0x33D1FF,
            "wakeword_ack": 0x33D1FF,
            "text_committed": 0x42D392,
            "warning": 0xFFB347,
            "error_flash": 0xFF3B30,
            "timeout_imminent": 0xFF9F1A,
        }.get(event_name, 0x7AA4FF)

    def _default_event_background(self, event_name: str) -> int:
        return {
            "trigger_received": 0x05131A,
            "wakeword_ack": 0x05131A,
            "text_committed": 0x06120B,
            "warning": 0x1A1005,
            "error_flash": 0x120103,
            "timeout_imminent": 0x190D02,
        }.get(event_name, 0x05070A)

    def _sanitize_value(self, value):
        if callable(value):
            return "<callable>"
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, dict):
            return {str(key): self._sanitize_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._sanitize_value(item) for item in value]
        return value

    def _serialize_visual(self, visual) -> dict | None:
        if visual is None:
            return None
        return {
            "type": visual.type,
            "exclusive": visual.exclusive,
            "params": self._sanitize_value(visual.params),
        }

    def _serialize_event(self, event: Event) -> dict:
        return {
            "id": event.id,
            "name": event.name,
            "priority": event.priority,
            "created_at": event.created_at,
            "duration": event.duration,
            "exclusive": event.exclusive,
            "payload": self._sanitize_value(event.payload),
        }

    def _serialize_scene(self, scene: Scene | None) -> dict | None:
        if scene is None:
            return None
        return {
            "timestamp": scene.timestamp,
            "diagnostics": list(scene.diagnostics),
            "main_layer_valid": scene.main_layer_valid,
            "layers": [
                {
                    "name": layer.name,
                    "priority": layer.priority,
                    "visual": self._serialize_visual(layer.visual),
                }
                for layer in scene.layers
            ],
        }

    def _serialize_frame(self, frame: Frame | None) -> dict | None:
        if frame is None:
            return None
        return {"timestamp": frame.timestamp, "leds": list(frame.leds)}


LedController = ControllerRuntime


def build_demo(controller: ControllerRuntime) -> None:
    controller.set_state("listening")
    controller.set_active_visual(
        layer_id="demo-progress",
        mode="progress",
        visual=progress(64, color=0x33AAFF, base_color=0x020304),
        payload={"value": 64},
    )


def demo_tick(controller: ControllerRuntime, now: float, start: float, total_seconds: float) -> None:
    known_event_ids = {event.id for event in controller.store.event_layer.pending_events}
    if controller.store.event_layer.current_event is not None:
        known_event_ids.add(controller.store.event_layer.current_event.id)

    if now - start > total_seconds / 4.0 and "event-warn" not in known_event_ids:
        controller.emit_event(
            "warning",
            {
                "event_id": "event-warn",
                "duration_ms": 2500,
                "color": 0xFF8800,
                "base_color": 0x120800,
                "created_at": now,
            },
            timestamp=now,
        )
    if now - start > total_seconds / 2.0 and "event-critical" not in known_event_ids:
        controller.emit_event(
            "error_flash",
            {
                "event_id": "event-critical",
                "duration_ms": 3000,
                "color": 0xFF1744,
                "base_color": 0x120003,
                "created_at": now,
            },
            timestamp=now,
        )
