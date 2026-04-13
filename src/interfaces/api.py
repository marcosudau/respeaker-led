from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..infrastructure.logging_utils import get_logger
from ..services.service import ControllerService
from ..version import __version__


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
    direction: float


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


class RegisterEffectSourceRequest(BaseModel):
    path: str
    enabled: bool = True


class ApplyEffectRequest(BaseModel):
    target_layer: str
    params: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int | None = None
    priority: int | None = None
    enqueue: bool = False
    replace_existing: bool = True


def create_app(
    *,
    fps: float = 8.0,
    use_device: bool = True,
    adapter_factory: Callable[[], Any] | None = None,
    lifecycle_callback: Callable[[str], None] | None = None,
) -> FastAPI:
    service = ControllerService(
        fps=fps,
        use_device=use_device,
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
        version=__version__,
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
                "list_effects",
                "show_effect",
                "list_effect_presets",
                "list_effect_commands",
                "apply_effect_preset",
                "list_effect_sources",
                "list_commands",
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

    @app.get("/api/v1/effects")
    def list_effects(request: Request):
        return {"items": get_service(request).list_effects()}

    @app.get("/api/v1/effects/{source_id}")
    def list_effects_for_source(source_id: str, request: Request):
        return {"items": get_service(request).list_effects_for_source(source_id)}

    @app.get("/api/v1/effects/{source_id}/{effect_id}")
    def effect_detail(source_id: str, effect_id: str, request: Request):
        try:
            return get_service(request).effect_info_for_source(source_id, effect_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/v1/effects/{source_id}/{effect_id}/presets")
    def list_effect_presets(source_id: str, effect_id: str, request: Request):
        return {"items": get_service(request).list_effect_presets(source_id, effect_id)}

    @app.get("/api/v1/effects/{source_id}/{effect_id}/commands")
    def list_effect_commands_for_effect(source_id: str, effect_id: str, request: Request):
        return {"items": get_service(request).list_effect_commands_for_effect(source_id, effect_id)}

    @app.post("/api/v1/effects/{source_id}/{effect_id}/apply")
    def apply_effect_for_source(source_id: str, effect_id: str, payload: ApplyEffectRequest, request: Request):
        service = get_service(request)
        try:
            return service.apply_effect(
                f"{source_id}::{effect_id}",
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

    @app.get("/api/v1/effect-presets/{source_id}/{preset_id}")
    def effect_preset_detail(source_id: str, preset_id: str, request: Request):
        try:
            return get_service(request).effect_preset_info(source_id, preset_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/v1/effect-presets/{source_id}/{preset_id}/apply")
    def apply_effect_preset(source_id: str, preset_id: str, request: Request):
        try:
            return get_service(request).apply_effect_preset(source_id, preset_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/v1/effect-sources")
    def list_effect_sources(request: Request):
        return {"items": get_service(request).list_effect_sources()}

    @app.post("/api/v1/effect-sources/register")
    def register_effect_source(request: Request, payload: RegisterEffectSourceRequest):
        try:
            return get_service(request).register_effect_source(payload.path, enabled=payload.enabled)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/effect-sources/reload")
    def reload_effect_sources(request: Request):
        try:
            return get_service(request).reload_effect_sources()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.delete("/api/v1/effect-sources/{source_id}")
    def remove_effect_source(source_id: str, request: Request):
        try:
            return get_service(request).remove_effect_source(source_id)
        except ValueError as exc:
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
        return get_service(request).set_direction(payload.direction)

    @app.post("/api/v1/commands/clear_direction")
    def clear_direction(request: Request):
        return get_service(request).clear_direction()

    @app.post("/api/v1/commands/set_brightness")
    def set_brightness(request: Request, payload: BrightnessCommand):
        return get_service(request).set_brightness(payload.level)

    @app.post("/api/v1/commands/set_enabled")
    def set_enabled(request: Request, payload: EnabledCommand):
        return get_service(request).set_enabled(payload.enabled)

    @app.get("/api/v1/commands")
    def list_all_effect_commands(request: Request):
        return {"items": get_service(request).list_effect_commands()}

    @app.get("/api/v1/commands/{source_id}")
    def list_source_effect_commands(source_id: str, request: Request):
        return {"items": get_service(request).list_effect_commands(source_id)}

    @app.get("/api/v1/commands/{source_id}/{command_name}")
    def effect_command_info(source_id: str, command_name: str, request: Request):
        try:
            return get_service(request).effect_command_info(source_id, command_name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/v1/commands/{source_id}/{command_name}")
    def toggle_effect_command(source_id: str, command_name: str, request: Request):
        try:
            return get_service(request).invoke_effect_command(source_id, command_name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/commands/{source_id}/{command_name}/on")
    def enable_effect_command(source_id: str, command_name: str, request: Request):
        try:
            return get_service(request).invoke_effect_command(source_id, command_name, state="on")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/commands/{source_id}/{command_name}/off")
    def disable_effect_command(source_id: str, command_name: str, request: Request):
        try:
            return get_service(request).invoke_effect_command(source_id, command_name, state="off")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app
