from __future__ import annotations

import argparse
import json
import time

import uvicorn

from .adapters import ConsolePreviewAdapter, ReSpeakerAdapter
from .api import create_app
from .client import LocalControllerClient
from .preset_loader import PresetRegistry
from .runtime import ControllerRuntime, build_demo, demo_tick


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


def log_cli_effect(*, use_device: bool, label: str, params: dict | None = None) -> None:
    if not use_device:
        return
    normalized_params = params or {}
    encoded = json.dumps(normalized_params, ensure_ascii=True, sort_keys=True)
    print(f"[device] effect={label} params={encoded}")


def add_connection_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--timeout", type=float, default=2.0)


def build_parser(registry: PresetRegistry) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generic frame-based LED effect engine for the reSpeaker XVF3800.")
    parser.add_argument(
        "--no-device",
        action="store_true",
        help="Do not use the real reSpeaker. Preview individual LED frames in the console instead.",
    )
    parser.add_argument("--fps", type=float, default=8.0, help="Render frames per second")

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-presets", help="List all discovered preset packs")
    list_parser.set_defaults(command_kind="list_presets")

    serve_parser = subparsers.add_parser("serve", help="Start the local controller process")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
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
    direction_set_parser.add_argument("direction_deg", type=float)
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

    activate_preset_parser = subparsers.add_parser("activate-preset", help="Activate an optional preset on a running service")
    add_connection_options(activate_preset_parser)
    activate_preset_parser.add_argument("preset_id")
    activate_preset_parser.add_argument("--spec", default="{}")
    activate_preset_parser.set_defaults(command_kind="activate_preset")

    demo_parser = subparsers.add_parser("demo", help="Run a generic layered demo with progress and events")
    demo_parser.add_argument("--seconds", type=float, default=12.0)
    demo_parser.set_defaults(command_kind="demo")

    return parser


def make_controller(use_device: bool, registry: PresetRegistry) -> ControllerRuntime:
    adapter = ReSpeakerAdapter() if use_device else ConsolePreviewAdapter()
    return ControllerRuntime(adapter=adapter, preset_registry=registry)


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


def main() -> int:
    registry = PresetRegistry.discover()
    parser = build_parser(registry)
    args = parser.parse_args()
    use_device = use_real_device(args)

    if args.command_kind == "list_presets":
        for preset in registry.list_presets():
            sample = str(preset.sample_path) if preset.sample_path else "-"
            print(f"{preset.manifest.command:18}  {preset.manifest.name:24}  sample={sample}")
        return 0

    if args.command_kind == "serve":
        print(f"[api] starting output_mode={'device' if use_device else 'console-preview'} host={args.host} port={args.port} fps={args.fps}")
        app = create_app(fps=args.fps, use_device=use_device, preset_registry=registry)
        config = uvicorn.Config(app, host=args.host, port=args.port, log_level="info")
        server = uvicorn.Server(config)
        app.state.shutdown_server = lambda: setattr(server, "should_exit", True)
        server.run()
        return 0

    if args.command_kind in {
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
        "activate_preset",
    }:
        client = make_client(args, best_effort=False)

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
            return emit_result(client.set_direction(args.direction_deg))
        if args.command_kind == "clear_direction":
            return emit_result(client.clear_direction())
        if args.command_kind == "set_brightness":
            return emit_result(client.set_brightness(args.level))
        if args.command_kind == "set_enabled":
            return emit_result(client.set_enabled(args.enabled))
        if args.command_kind == "activate_preset":
            return emit_result(client.activate_preset(args.preset_id, parse_json_payload(args.spec)))

    controller = make_controller(use_device, registry)
    try:
        if args.command_kind == "demo":
            log_cli_effect(
                use_device=use_device,
                label="demo",
                params={"seconds": args.seconds, "fps": args.fps},
            )
            build_demo(controller)
            start = time.monotonic()
            controller.run(
                seconds=args.seconds,
                fps=args.fps,
                tick=lambda ctrl, now: demo_tick(ctrl, now, start, args.seconds),
            )
            return 0

        parser.error(f"Unsupported command kind: {args.command_kind}")
        return 2
    finally:
        controller.close()
