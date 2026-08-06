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

    list_parser = subparsers.add_parser("list", help="List states, overlays, events, or presets")
    add_connection_options(list_parser)
    list_parser.add_argument(
        "kind",
        choices=("state", "states", "overlay", "overlays", "event", "events", "preset", "presets"),
    )
    list_parser.add_argument("--details", action="store_true")
    list_parser.add_argument("--json", action="store_true")
    list_parser.set_defaults(command_kind="list_v2")

    show_parser = subparsers.add_parser("show", help="Show one state, overlay, event, or preset")
    add_connection_options(show_parser)
    show_parser.add_argument("target")
    show_parser.add_argument("--json", action="store_true")
    show_parser.set_defaults(command_kind="show_v2")

    set_parser = subparsers.add_parser("set", help="Set a state or overlay")
    add_connection_options(set_parser)
    set_parser.add_argument("subject_or_target")
    set_parser.add_argument("target", nargs="?")
    set_parser.add_argument("--slot", choices=("background", "primary"), default="primary")
    set_parser.add_argument("--channel")
    set_parser.add_argument("--config", default="{}")
    set_parser.add_argument("--inputs", default="{}")
    set_action = set_parser.add_mutually_exclusive_group()
    set_action.add_argument("--on", dest="action", action="store_const", const="on")
    set_action.add_argument("--off", dest="action", action="store_const", const="off")
    set_action.add_argument("--toggle", dest="action", action="store_const", const="toggle")
    set_parser.set_defaults(command_kind="set_v2", action="on")

    clear_parser = subparsers.add_parser("clear", help="Clear a state slot or overlay channel")
    add_connection_options(clear_parser)
    clear_parser.add_argument("subject")
    clear_parser.add_argument("channel", nargs="?")
    clear_parser.add_argument("--slot", choices=("background", "primary"), default="primary")
    clear_parser.set_defaults(command_kind="clear_v2")

    update_parser = subparsers.add_parser("update", help="Update a controlled overlay")
    add_connection_options(update_parser)
    update_parser.add_argument("subject_or_channel")
    update_parser.add_argument("channel", nargs="?")
    update_parser.add_argument("--inputs", required=True)
    update_parser.set_defaults(command_kind="update_v2")

    emit_parser = subparsers.add_parser("emit", help="Emit an event")
    add_connection_options(emit_parser)
    emit_parser.add_argument("subject_or_target")
    emit_parser.add_argument("target", nargs="?")
    emit_parser.add_argument("--config", default="{}")
    emit_parser.add_argument("--priority", type=int)
    emit_parser.set_defaults(command_kind="emit_v2")

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


def emit_list_result(result, *, as_json: bool = False, details: bool = False) -> int:
    if not getattr(result, "ok", False):
        return emit_result(result)
    data = getattr(result, "data", None)
    if as_json or details or not isinstance(data, list):
        print(json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True))
    else:
        for item in data:
            print(item)
    return 0


def _normalize_argv(argv: list[str]) -> list[str]:
    slash_aliases = {
        "/on": "--on",
        "/off": "--off",
        "/toggle": "--toggle",
        "/json": "--json",
        "/details": "--details",
    }
    normalized = [slash_aliases.get(value.lower(), value) for value in argv]
    if not normalized:
        return normalized
    if normalized[0] == "--":
        return normalized[1:]
    for index, value in enumerate(normalized):
        if value == "--serve":
            normalized[index] = "serve"
            break
    return normalized


def ensure_daemon_running(
    host: str = "127.0.0.1",
    port: int = 8765,
    timeout: float = 0.5,
    startup_wait: float = 5.0,
) -> bool:
    """Check if the daemon is running; start it in the background if not."""
    client = LocalControllerClient(host=host, port=port, timeout=timeout)
    result = client.ping()
    if result.ok:
        return True

    import subprocess
    cmd = [sys.executable, "-m", "src", "serve", "--host", host, "--port", str(port)]
    try:
        if sys.platform.startswith("win"):
            creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            subprocess.Popen(
                cmd,
                creationflags=creationflags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
    except OSError as exc:
        logger.warning("failed to spawn daemon: %s", exc)
        return False

    import time as _time
    attempts = int(startup_wait / 0.5)
    for _ in range(attempts):
        _time.sleep(0.5)
        if client.ping().ok:
            return True
    return False


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
        "list_v2",
        "show_v2",
        "set_v2",
        "clear_v2",
        "update_v2",
        "emit_v2",
        "list_effect_sources",
        "register_effect_source",
        "reload_effect_sources",
        "remove_effect_source",
        "ping",
        "status",
        "set_state",
        "clear_state",
        "emit_event",
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

        # Auto-spawn daemon for non-serve commands
        if args.command_kind != "serve":
            if not ensure_daemon_running(
                host=getattr(args, "host", "127.0.0.1"),
                port=getattr(args, "port", 8765),
            ):
                print(json.dumps({"ok": False, "error": "Could not start or connect to the LED controller daemon"}, ensure_ascii=True))
                return 1

        client = make_client(args, best_effort=False)

        if args.command_kind == "list_v2":
            result = client.list_v2(args.kind, details=args.details)
            return emit_list_result(result, as_json=args.json, details=args.details)
        if args.command_kind == "show_v2":
            return emit_result(client.show_target(args.target))
        if args.command_kind == "set_v2":
            subject = args.subject_or_target
            target = args.target
            if subject not in {"state", "overlay"}:
                target = subject
                resolved = client.show_target(target)
                if not resolved.ok:
                    return emit_result(resolved)
                subject = str(resolved.data.get("type", ""))
            if not target:
                parser.error("set requires a target id or preset")
            if subject == "state":
                return emit_result(
                    client.set_state_target(
                        target,
                        parse_json_payload(args.config),
                        slot=args.slot,
                        action=args.action,
                    )
                )
            if subject == "overlay":
                return emit_result(
                    client.set_overlay_target(
                        target,
                        args.channel,
                        parse_json_payload(args.config),
                        parse_json_payload(args.inputs),
                        action=args.action,
                    )
                )
            parser.error(f"{target!r} is a {subject or 'unknown type'}; set accepts only states and overlays")
        if args.command_kind == "clear_v2":
            if args.subject == "state":
                return emit_result(client.clear_state_target(slot=args.slot))
            channel = args.channel if args.subject == "overlay" else args.subject
            if not channel:
                parser.error("clear overlay requires a channel")
            return emit_result(client.clear_overlay_target(channel))
        if args.command_kind == "update_v2":
            channel = args.channel if args.subject_or_channel == "overlay" else args.subject_or_channel
            if not channel:
                parser.error("update requires an overlay channel")
            return emit_result(client.update_overlay_target(channel, parse_json_payload(args.inputs)))
        if args.command_kind == "emit_v2":
            target = (
                args.target
                if args.subject_or_target == "event"
                else args.subject_or_target
            )
            if not target:
                parser.error("emit requires an event id or preset")
            return emit_result(
                client.emit_event_target(
                    target,
                    parse_json_payload(args.config),
                    priority=args.priority,
                )
            )
        if args.command_kind == "list_effect_sources":
            return emit_result(client.list_effect_sources())
        if args.command_kind == "register_effect_source":
            return emit_result(client.register_effect_source(args.path, enabled=args.enabled))
        if args.command_kind == "reload_effect_sources":
            return emit_result(client.reload_effect_sources())
        if args.command_kind == "remove_effect_source":
            return emit_result(client.remove_effect_source(args.source_id))
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
