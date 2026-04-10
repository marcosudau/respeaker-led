from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from typing import Any, Callable

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .logging_utils import get_logger
from .preset_loader import PresetRegistry
from .service import ControllerService


logger = get_logger("api")


class StateCommand(BaseModel):
    state_name: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ClearStateCommand(BaseModel):
    state_name: str | None = None


class EventCommand(BaseModel):
    event_name: str
    payload: dict[str, Any] = Field(default_factory=dict)


class CountdownStartCommand(BaseModel):
    total_ms: int
    remaining_ms: int | None = None
    follow_up_state: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class CountdownUpdateCommand(BaseModel):
    remaining_ms: int


class DirectionCommand(BaseModel):
    direction_deg: float


class BrightnessCommand(BaseModel):
    level: float


class EnabledCommand(BaseModel):
    enabled: bool


class EffectCommand(BaseModel):
    effect_id: str
    target_layer: str
    params: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int | None = None
    priority: int | None = None
    enqueue: bool = False
    replace_existing: bool = True


class ClearLayerCommand(BaseModel):
    target_layer: str


class PresetActivationRequest(BaseModel):
    spec: dict[str, Any] = Field(default_factory=dict)


def create_app(
    *,
    fps: float = 8.0,
    use_device: bool = True,
    preset_registry: PresetRegistry | None = None,
    adapter_factory: Callable[[], Any] | None = None,
    lifecycle_callback: Callable[[str], None] | None = None,
) -> FastAPI:
    service = ControllerService(
        fps=fps,
        use_device=use_device,
        preset_registry=preset_registry,
        adapter_factory=adapter_factory,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        service.start()
        if lifecycle_callback is not None:
            lifecycle_callback("started")
        try:
            yield
        finally:
            if lifecycle_callback is not None:
                lifecycle_callback("stopping")
            service.stop()

    app = FastAPI(
        title="LED Controller API",
        version="1.0.0",
        summary="Local API for the generic frame-based LED controller",
        lifespan=lifespan,
    )
    app.state.controller_service = service
    app.state.shutdown_server = None

    def get_service(request: Request) -> ControllerService:
        return request.app.state.controller_service

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("unhandled api exception method=%s path=%s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "internal_server_error"})

    @app.get("/")
    def root(request: Request):
        service = get_service(request)
        snapshot = service.snapshot()
        return {
            "service": "LED Controller API",
            "version": app.version,
            "docs": "/docs",
            "health": "/health",
            "api_base": "/api/v1",
            "output_mode": snapshot["output_mode"],
            "requested_output_mode": snapshot["requested_output_mode"],
            "render_loop_running": snapshot["render_loop_running"],
            "commands": [
                "list_presets",
                "list_effects",
                "set_state",
                "clear_state",
                "emit_event",
                "apply_effect",
                "clear_layer",
                "reset",
                "shutdown",
                "ping",
                "get_status",
                "start_timeout_countdown",
                "update_timeout_countdown",
                "cancel_timeout_countdown",
                "set_direction",
                "clear_direction",
                "set_brightness",
                "set_enabled",
            ],
        }

    @app.get("/health")
    def health(request: Request):
        service = get_service(request)
        snapshot = service.snapshot()
        return {
            "status": "ok" if snapshot["last_error"] is None and not snapshot["fallback_active"] else "degraded",
            "render_loop_running": snapshot["render_loop_running"],
            "render_count": snapshot["render_count"],
            "last_error": snapshot["last_error"],
            "output_mode": snapshot["output_mode"],
            "fallback_active": snapshot["fallback_active"],
        }

    @app.get("/api/v1/ping")
    def ping(request: Request):
        return get_service(request).ping()

    @app.get("/api/v1/status")
    def status(request: Request):
        return get_service(request).get_status()

    @app.get("/api/v1/presets")
    def list_presets(request: Request):
        return {"items": get_service(request).list_presets()}

    @app.get("/api/v1/effects")
    def list_effects(request: Request):
        return {"items": get_service(request).list_effects()}

    @app.get("/api/v1/presets/{preset_id}")
    def preset_detail(preset_id: str, request: Request):
        service = get_service(request)
        try:
            return service.preset_info(preset_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/v1/presets/{preset_id}/sample")
    def preset_sample(preset_id: str, request: Request):
        service = get_service(request)
        try:
            return service.preset_sample(preset_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/v1/presets/{preset_id}/activate")
    def activate_preset(preset_id: str, request: Request, payload: PresetActivationRequest = Body(default_factory=PresetActivationRequest)):
        service = get_service(request)
        try:
            return service.activate_preset(preset_id, payload.spec)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/commands/set_state")
    def set_state(request: Request, payload: StateCommand):
        return get_service(request).set_state(payload.state_name, payload.payload)

    @app.post("/api/v1/commands/clear_state")
    def clear_state(request: Request, payload: ClearStateCommand):
        return get_service(request).clear_state(payload.state_name)

    @app.post("/api/v1/commands/emit_event")
    def emit_event(request: Request, payload: EventCommand):
        try:
            return get_service(request).emit_event(payload.event_name, payload.payload)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/commands/apply_effect")
    def apply_effect(request: Request, payload: EffectCommand):
        service = get_service(request)
        try:
            return service.apply_effect(
                payload.effect_id,
                payload.target_layer,
                payload.params,
                duration_ms=payload.duration_ms,
                priority=payload.priority,
                enqueue=payload.enqueue,
                replace_existing=payload.replace_existing,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/commands/clear_layer")
    def clear_layer(request: Request, payload: ClearLayerCommand):
        service = get_service(request)
        try:
            return service.clear_layer(payload.target_layer)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/commands/reset")
    def reset(request: Request):
        return get_service(request).reset()

    @app.post("/api/v1/commands/shutdown")
    def shutdown(request: Request):
        snapshot = get_service(request).shutdown()
        shutdown_server = getattr(request.app.state, "shutdown_server", None)
        if callable(shutdown_server):
            threading.Thread(target=shutdown_server, daemon=True).start()
        return snapshot

    @app.post("/api/v1/commands/start_timeout_countdown")
    def start_timeout_countdown(request: Request, payload: CountdownStartCommand):
        return get_service(request).start_timeout_countdown(
            payload.total_ms,
            payload.remaining_ms,
            follow_up_state=payload.follow_up_state,
            payload=payload.payload,
        )

    @app.post("/api/v1/commands/update_timeout_countdown")
    def update_timeout_countdown(request: Request, payload: CountdownUpdateCommand):
        try:
            return get_service(request).update_timeout_countdown(payload.remaining_ms)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/commands/cancel_timeout_countdown")
    def cancel_timeout_countdown(request: Request):
        return get_service(request).cancel_timeout_countdown()

    @app.post("/api/v1/commands/set_direction")
    def set_direction(request: Request, payload: DirectionCommand):
        return get_service(request).set_direction(payload.direction_deg)

    @app.post("/api/v1/commands/clear_direction")
    def clear_direction(request: Request):
        return get_service(request).clear_direction()

    @app.post("/api/v1/commands/set_brightness")
    def set_brightness(request: Request, payload: BrightnessCommand):
        return get_service(request).set_brightness(payload.level)

    @app.post("/api/v1/commands/set_enabled")
    def set_enabled(request: Request, payload: EnabledCommand):
        return get_service(request).set_enabled(payload.enabled)

    return app
