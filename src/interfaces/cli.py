from __future__ import annotations

import argparse
import json
import sys

if __package__ in {None, ""}:
    from pathlib import Path

    _PROJECT_ROOT = Path(__file__).resolve().parents[2]
    _PROJECT_ROOT_STR = str(_PROJECT_ROOT)
    if _PROJECT_ROOT_STR not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT_STR)
    __package__ = "src.interfaces"

from uvicorn.config import Config as UvicornConfig
from uvicorn.server import Server as UvicornServer

from .api import create_app
from .client import LocalControllerClient
from ..infrastructure.logging_utils import get_logger, setup_logging
from ..infrastructure.paths import ACTIVE_SERVICE_FILE
from ..services.service_hosting import (
    clear_active_service_info,
    create_active_service_info,
    default_port_pool,
    parse_port_pool,
    save_active_service_info,
    select_service_port,
    service_binding_message,
    take_over_existing_instance,
    update_active_service_status,
)


logger = get_logger("cli")


def parse_json_payload(value: str | None) -> dict:
    if not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("Payload must be a JSON object")
    return parsed


def parse_bool_flag(value: str) -> bool:
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value}")


def parse_qualified_identifier(value: str, *, label: str) -> tuple[str, str]:
    text = str(value or "").strip()
    source_id, separator, local_id = text.partition("::")
    if not separator or not source_id or not local_id:
        raise argparse.ArgumentTypeError(f"{label} must use the form <source_id>::<id>")
    return source_id, local_id


def use_real_device(args) -> bool:
    return not getattr(args, "no_device", False)


def add_connection_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--timeout", type=float, default=2.0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local service controller for the reSpeaker XVF3800 LED ring.")
    parser.add_argument(
        "--no-device",
        action="store_true",
        help="Start the service without the real reSpeaker and use console preview instead.",
    )
    parser.add_argument("--fps", type=float, default=8.0, help="Render frames per second")

    subparsers = parser.add_subparsers(dest="command", required=True)

    effect_list_parser = subparsers.add_parser("list-effects", help="List built-in effects exposed by a running local service")
    add_connection_options(effect_list_parser)
    effect_list_parser.set_defaults(command_kind="list_effects")

    show_effect_parser = subparsers.add_parser("show-effect", help="Show structured metadata for a qualified effect")
    add_connection_options(show_effect_parser)
    show_effect_parser.add_argument("qualified_effect_id")
    show_effect_parser.set_defaults(command_kind="show_effect")

    list_effect_presets_parser = subparsers.add_parser("list-effect-presets", help="List embedded presets for a qualified effect")
    add_connection_options(list_effect_presets_parser)
    list_effect_presets_parser.add_argument("qualified_effect_id")
    list_effect_presets_parser.set_defaults(command_kind="list_effect_presets")

    list_effect_commands_parser = subparsers.add_parser("list-effect-commands", help="List embedded commands for a qualified effect")
    add_connection_options(list_effect_commands_parser)
    list_effect_commands_parser.add_argument("qualified_effect_id")
    list_effect_commands_parser.set_defaults(command_kind="list_effect_commands")

    apply_effect_preset_parser = subparsers.add_parser("apply-effect-preset", help="Apply a qualified embedded effect preset")
    add_connection_options(apply_effect_preset_parser)
    apply_effect_preset_parser.add_argument("qualified_preset_id")
    apply_effect_preset_parser.set_defaults(command_kind="apply_effect_preset")

    effect_source_list_parser = subparsers.add_parser("list-effect-sources", help="List registered or autodiscovered effect sources")
    add_connection_options(effect_source_list_parser)
    effect_source_list_parser.set_defaults(command_kind="list_effect_sources")

    register_effect_source_parser = subparsers.add_parser("register-effect-source", help="Register a .lefx or .lefxset source on a running service")
    add_connection_options(register_effect_source_parser)
    register_effect_source_parser.add_argument("path")
    register_effect_source_parser.add_argument("--enabled", type=parse_bool_flag, default=True)
    register_effect_source_parser.set_defaults(command_kind="register_effect_source")

    reload_effect_sources_parser = subparsers.add_parser("reload-effect-sources", help="Reload all effect sources and autodiscovery packages")
    add_connection_options(reload_effect_sources_parser)
    reload_effect_sources_parser.set_defaults(command_kind="reload_effect_sources")

    remove_effect_source_parser = subparsers.add_parser("remove-effect-source", help="Remove a registered effect source from the running service")
    add_connection_options(remove_effect_source_parser)
    remove_effect_source_parser.add_argument("source_id")
    remove_effect_source_parser.set_defaults(command_kind="remove_effect_source")

    list_commands_parser = subparsers.add_parser("list-commands", help="List registered packaged commands")
    add_connection_options(list_commands_parser)
    list_commands_parser.add_argument("--source")
    list_commands_parser.set_defaults(command_kind="list_commands")

    invoke_command_parser = subparsers.add_parser("invoke-command", help="Invoke a packaged command on a running service")
    add_connection_options(invoke_command_parser)
    invoke_command_parser.add_argument("source_id")
    invoke_command_parser.add_argument("command_name")
    invoke_command_parser.add_argument("state", nargs="?")
    invoke_command_parser.set_defaults(command_kind="invoke_command")

    serve_parser = subparsers.add_parser("serve", help="Start the local controller process")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument(
        "--port-pool",
        default="",
        help="Optional comma-separated port list or ranges for fallback, e.g. 8765,8766,8770-8774",
    )
    serve_parser.set_defaults(command_kind="serve")

    ping_parser = subparsers.add_parser("ping", help="Ping a running local controller service")
    add_connection_options(ping_parser)
    ping_parser.set_defaults(command_kind="ping")

    status_parser = subparsers.add_parser("status", help="Read controller status from a running local service")
    add_connection_options(status_parser)
    status_parser.set_defaults(command_kind="status")

    set_state_parser = subparsers.add_parser("set-state", help="Set the active base state on a running service")
    add_connection_options(set_state_parser)
    set_state_parser.add_argument("state_name")
    set_state_parser.add_argument("--payload", default="{}")
    set_state_parser.set_defaults(command_kind="set_state")

    clear_state_parser = subparsers.add_parser("clear-state", help="Clear the active base state back to idle")
    add_connection_options(clear_state_parser)
    clear_state_parser.add_argument("state_name", nargs="?")
    clear_state_parser.set_defaults(command_kind="clear_state")

    emit_event_parser = subparsers.add_parser("emit-event", help="Emit a transient event on a running service")
    add_connection_options(emit_event_parser)
    emit_event_parser.add_argument("event_name")
    emit_event_parser.add_argument("--payload", default="{}")
    emit_event_parser.add_argument("--duration-ms", type=int)
    emit_event_parser.add_argument("--priority", type=int)
    emit_event_parser.add_argument("--source")
    emit_event_parser.add_argument("--reason")
    emit_event_parser.set_defaults(command_kind="emit_event")

    apply_effect_parser = subparsers.add_parser("apply-effect", help="Apply a built-in effect on a running service")
    add_connection_options(apply_effect_parser)
    apply_effect_parser.add_argument("effect_id")
    apply_effect_parser.add_argument("target_layer")
    apply_effect_parser.add_argument("--params", default="{}")
    apply_effect_parser.add_argument("--duration-ms", type=int)
    apply_effect_parser.add_argument("--priority", type=int)
    apply_effect_parser.add_argument("--enqueue", action="store_true")
    apply_effect_parser.add_argument("--replace-existing", type=parse_bool_flag, default=True)
    apply_effect_parser.set_defaults(command_kind="apply_effect")

    clear_layer_parser = subparsers.add_parser("clear-layer", help="Clear a specific runtime layer on a running service")
    add_connection_options(clear_layer_parser)
    clear_layer_parser.add_argument("target_layer")
    clear_layer_parser.set_defaults(command_kind="clear_layer")

    reset_parser = subparsers.add_parser("reset", help="Reset a running controller service to idle")
    add_connection_options(reset_parser)
    reset_parser.set_defaults(command_kind="reset")

    shutdown_parser = subparsers.add_parser("shutdown", help="Shut down a running controller service")
    add_connection_options(shutdown_parser)
    shutdown_parser.set_defaults(command_kind="shutdown")

    countdown_start_parser = subparsers.add_parser("start-countdown", help="Start a timeout countdown on a running service")
    add_connection_options(countdown_start_parser)
    countdown_start_parser.add_argument("total_ms", type=int)
    countdown_start_parser.add_argument("--remaining-ms", type=int)
    countdown_start_parser.add_argument("--follow-up-state")
    countdown_start_parser.add_argument("--payload", default="{}")
    countdown_start_parser.set_defaults(command_kind="start_countdown")

    countdown_update_parser = subparsers.add_parser("update-countdown", help="Update the remaining timeout countdown")
    add_connection_options(countdown_update_parser)
    countdown_update_parser.add_argument("remaining_ms", type=int)
    countdown_update_parser.set_defaults(command_kind="update_countdown")

    countdown_cancel_parser = subparsers.add_parser("cancel-countdown", help="Cancel the active timeout countdown")
    add_connection_options(countdown_cancel_parser)
    countdown_cancel_parser.set_defaults(command_kind="cancel_countdown")

    direction_set_parser = subparsers.add_parser("set-direction", help="Set the optional direction marker")
    add_connection_options(direction_set_parser)
    direction_set_parser.add_argument("direction", type=float)
    direction_set_parser.set_defaults(command_kind="set_direction")

    direction_clear_parser = subparsers.add_parser("clear-direction", help="Clear the optional direction marker")
    add_connection_options(direction_clear_parser)
    direction_clear_parser.set_defaults(command_kind="clear_direction")

    brightness_parser = subparsers.add_parser("set-brightness", help="Adjust controller brightness between 0.0 and 1.0")
    add_connection_options(brightness_parser)
    brightness_parser.add_argument("level", type=float)
    brightness_parser.set_defaults(command_kind="set_brightness")

    enabled_parser = subparsers.add_parser("set-enabled", help="Enable or disable LED output")
    add_connection_options(enabled_parser)
    enabled_parser.add_argument("enabled", type=parse_bool_flag)
    enabled_parser.set_defaults(command_kind="set_enabled")

    return parser


def make_client(args, *, best_effort: bool = False) -> LocalControllerClient:
    return LocalControllerClient(
        host=args.host,
        port=args.port,
        timeout=args.timeout,
        best_effort=best_effort,
    )


def emit_result(result) -> int:
    if getattr(result, "data", None) is not None:
        print(json.dumps(result.data, ensure_ascii=True, indent=2, sort_keys=True))
    elif getattr(result, "ok", False):
        print(json.dumps({"ok": True}, ensure_ascii=True))
    return 0 if getattr(result, "ok", False) else 1


def _normalize_argv(argv: list[str]) -> list[str]:
    normalized = list(argv)
    if not normalized:
        return normalized
    if normalized[0] == "--":
        return normalized[1:]
    for index, value in enumerate(normalized):
        if value == "--serve":
            normalized[index] = "serve"
            break
    return normalized


def main() -> int:
    parser = build_parser()
    args = parser.parse_args(_normalize_argv(sys.argv[1:]))
    use_device = use_real_device(args)

    if args.command_kind == "serve":
        log_file = setup_logging(console=True)
        instance_id: str | None = None
        try:
            port_pool = parse_port_pool(args.port_pool) or default_port_pool()
            previous = take_over_existing_instance(ACTIVE_SERVICE_FILE)
            if previous is not None:
                logger.info("took over existing instance pid=%s host=%s port=%s", previous.pid, previous.host, previous.port)

            selected_port = select_service_port(args.host, args.port, port_pool)
            instance_info = create_active_service_info(
                host=args.host,
                port=selected_port,
                requested_port=args.port,
                port_pool=port_pool,
                log_file=str(log_file),
            )
            instance_id = instance_info.instance_id
            save_active_service_info(ACTIVE_SERVICE_FILE, instance_info)
            print(json.dumps(service_binding_message(instance_info), ensure_ascii=True), flush=True)
            logger.info(
                "starting controller service output_mode=%s host=%s port=%s requested_port=%s",
                "device" if use_device else "console-preview",
                args.host,
                selected_port,
                args.port,
            )
            app = create_app(
                fps=args.fps,
                use_device=use_device,
                lifecycle_callback=lambda phase: update_active_service_status(ACTIVE_SERVICE_FILE, instance_info.instance_id, "ready" if phase == "started" else "stopping"),
            )
            config = UvicornConfig(
                app,
                host=args.host,
                port=selected_port,
                log_level="info",
                http="h11",
                ws="none",
                loop="asyncio",
                lifespan="on",
            )
            server = UvicornServer(config)
            app.state.shutdown_server = lambda: setattr(server, "should_exit", True)
            server.run()
            return 0
        except Exception as exc:
            logger.exception("controller service failed to start")
            print(json.dumps({"event": "service_start_failed", "detail": str(exc)}, ensure_ascii=True), file=sys.stderr)
            return 1
        finally:
            clear_active_service_info(ACTIVE_SERVICE_FILE, instance_id=instance_id)

    if args.command_kind in {
        "list_effects",
        "show_effect",
        "list_effect_presets",
        "list_effect_commands",
        "apply_effect_preset",
        "list_effect_sources",
        "register_effect_source",
        "reload_effect_sources",
        "remove_effect_source",
        "list_commands",
        "invoke_command",
        "ping",
        "status",
        "set_state",
        "clear_state",
        "emit_event",
        "apply_effect",
        "clear_layer",
        "reset",
        "shutdown",
        "start_countdown",
        "update_countdown",
        "cancel_countdown",
        "set_direction",
        "clear_direction",
        "set_brightness",
        "set_enabled",
    }:
        setup_logging(console=False)
        client = make_client(args, best_effort=False)

        if args.command_kind == "list_effects":
            return emit_result(client.list_effects())
        if args.command_kind == "show_effect":
            source_id, effect_id = parse_qualified_identifier(args.qualified_effect_id, label="qualified_effect_id")
            return emit_result(client.get_effect(source_id, effect_id))
        if args.command_kind == "list_effect_presets":
            source_id, effect_id = parse_qualified_identifier(args.qualified_effect_id, label="qualified_effect_id")
            return emit_result(client.list_effect_presets(source_id, effect_id))
        if args.command_kind == "list_effect_commands":
            source_id, effect_id = parse_qualified_identifier(args.qualified_effect_id, label="qualified_effect_id")
            return emit_result(client.list_effect_commands_for_effect(source_id, effect_id))
        if args.command_kind == "apply_effect_preset":
            source_id, preset_id = parse_qualified_identifier(args.qualified_preset_id, label="qualified_preset_id")
            return emit_result(client.apply_effect_preset(source_id, preset_id))
        if args.command_kind == "list_effect_sources":
            return emit_result(client.list_effect_sources())
        if args.command_kind == "register_effect_source":
            return emit_result(client.register_effect_source(args.path, enabled=args.enabled))
        if args.command_kind == "reload_effect_sources":
            return emit_result(client.reload_effect_sources())
        if args.command_kind == "remove_effect_source":
            return emit_result(client.remove_effect_source(args.source_id))
        if args.command_kind == "list_commands":
            return emit_result(client.list_commands(args.source))
        if args.command_kind == "invoke_command":
            return emit_result(client.invoke_command(args.source_id, args.command_name, args.state))
        if args.command_kind == "ping":
            return emit_result(client.ping())
        if args.command_kind == "status":
            return emit_result(client.get_status())
        if args.command_kind == "set_state":
            return emit_result(client.set_state(args.state_name, parse_json_payload(args.payload)))
        if args.command_kind == "clear_state":
            return emit_result(client.clear_state(args.state_name))
        if args.command_kind == "emit_event":
            payload = parse_json_payload(args.payload)
            if args.duration_ms is not None:
                payload["duration_ms"] = args.duration_ms
            if args.priority is not None:
                payload["priority"] = args.priority
            if args.source:
                payload["source"] = args.source
            if args.reason:
                payload["reason"] = args.reason
            return emit_result(client.emit_event(args.event_name, payload))
        if args.command_kind == "apply_effect":
            return emit_result(
                client.apply_effect(
                    args.effect_id,
                    args.target_layer,
                    parse_json_payload(args.params),
                    duration_ms=args.duration_ms,
                    priority=args.priority,
                    enqueue=args.enqueue,
                    replace_existing=args.replace_existing,
                )
            )
        if args.command_kind == "clear_layer":
            return emit_result(client.clear_layer(args.target_layer))
        if args.command_kind == "reset":
            return emit_result(client.reset())
        if args.command_kind == "shutdown":
            return emit_result(client.shutdown())
        if args.command_kind == "start_countdown":
            return emit_result(
                client.start_timeout_countdown(
                    args.total_ms,
                    args.remaining_ms,
                    follow_up_state=args.follow_up_state,
                    payload=parse_json_payload(args.payload),
                )
            )
        if args.command_kind == "update_countdown":
            return emit_result(client.update_timeout_countdown(args.remaining_ms))
        if args.command_kind == "cancel_countdown":
            return emit_result(client.cancel_timeout_countdown())
        if args.command_kind == "set_direction":
            return emit_result(client.set_direction(args.direction))
        if args.command_kind == "clear_direction":
            return emit_result(client.clear_direction())
        if args.command_kind == "set_brightness":
            return emit_result(client.set_brightness(args.level))
        if args.command_kind == "set_enabled":
            return emit_result(client.set_enabled(args.enabled))
    parser.error(f"Unsupported command kind: {args.command_kind}")
    return 2
