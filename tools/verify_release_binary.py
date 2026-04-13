from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


DEFAULT_SOURCE_ID = "default-effects"
DEFAULT_EFFECT_SET_FILENAME = "default-effects.lefxset"
SOFT_PULSE_QUALIFIED_ID = "default-effects::soft_pulse"
SOFT_PULSE_STATE_PRESET_ID = "default-effects::state_soft_pulse_idle"
SOFT_PULSE_EFFECT_PRESET_ID = "default-effects::effect_soft_pulse_main"
SOFT_PULSE_COMMAND_NAME = "effect_soft_pulse_accent"
DIRECTION_EFFECT_QUALIFIED_ID = "default-effects::direction_indicator"
DEFAULT_DIRECTION = 120.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smoke-test the built release binary by exercising the default effect-set end to end.")
    parser.add_argument("exe_path")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8771)
    parser.add_argument("--startup-timeout", type=float, default=20.0)
    parser.add_argument("--shutdown-timeout", type=float, default=20.0)
    return parser


def _run_cli(exe_path: Path, *args: str):
    completed = subprocess.run(
        [str(exe_path), *args],
        cwd=str(exe_path.parent),
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"CLI command failed ({' '.join(args)}): stdout={completed.stdout.strip()!r} stderr={completed.stderr.strip()!r}"
        )
    output = completed.stdout.strip()
    return {} if not output else json.loads(output)


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _service_log_tail(log_path: Path, *, max_lines: int = 80) -> str:
    if not log_path.exists():
        return "<no service log available>"
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-max_lines:])


def _items_payload(payload, *, label: str) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]
    raise RuntimeError(f"{label} did not return a JSON list or an object with 'items'")


def _find_default_source(sources_payload) -> dict:
    for item in _items_payload(sources_payload, label="list-effect-sources"):
        if isinstance(item, dict) and item.get("source_id") == DEFAULT_SOURCE_ID:
            return item
    raise RuntimeError("Default source 'default-effects' is missing from list-effect-sources")


def _find_effect(effects_payload, qualified_id: str) -> dict:
    for item in _items_payload(effects_payload, label="list-effects"):
        if isinstance(item, dict) and item.get("qualified_id") == qualified_id:
            return item
    raise RuntimeError(f"Effect {qualified_id!r} is missing from list-effects")


def _active_main_visual(snapshot: dict) -> dict:
    active_visual = snapshot.get("active_visual")
    if not isinstance(active_visual, dict):
        return {}
    visual = active_visual.get("visual")
    return visual if isinstance(visual, dict) else {}


def _layer_visual(snapshot: dict, layer_name: str) -> dict:
    render_layers = snapshot.get("render_layers")
    if not isinstance(render_layers, dict):
        return {}
    visual = render_layers.get(layer_name)
    return visual if isinstance(visual, dict) else {}


def _scene_layer_names(snapshot: dict) -> set[str]:
    last_scene = snapshot.get("last_scene")
    if not isinstance(last_scene, dict):
        return set()
    layers = last_scene.get("layers")
    if not isinstance(layers, list):
        return set()
    names: set[str] = set()
    for layer in layers:
        if isinstance(layer, dict) and isinstance(layer.get("name"), str):
            names.add(layer["name"])
    return names


def _await_shutdown(exe_path: Path, process: subprocess.Popen, host: str, port: int, timeout: float) -> None:
    deadline = time.monotonic() + max(0.1, timeout)
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return
        try:
            ping_payload = _run_cli(exe_path, "ping", "--host", host, "--port", str(port))
        except Exception:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            return
        if not isinstance(ping_payload, dict) or ping_payload.get("ok") is not True:
            return
        time.sleep(0.2)
    raise TimeoutError(f"Release binary did not stop within {timeout} seconds")


def verify_release_binary(
    *,
    exe_path: Path,
    host: str,
    port: int,
    startup_timeout: float,
    shutdown_timeout: float,
) -> dict:
    if not exe_path.exists():
        raise FileNotFoundError(f"Release binary does not exist: {exe_path}")

    log_path = exe_path.parent / "verify_release_binary_service.log"
    with log_path.open("w", encoding="utf-8") as service_log:
        process = subprocess.Popen(
            [str(exe_path), "--no-device", "serve", "--host", host, "--port", str(port)],
            cwd=str(exe_path.parent),
            stdout=service_log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            deadline = time.monotonic() + max(0.1, startup_timeout)
            ping_payload = None
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"Release binary exited unexpectedly with code {process.returncode}")
                try:
                    ping_payload = _run_cli(exe_path, "ping", "--host", host, "--port", str(port))
                except Exception:
                    time.sleep(0.2)
                    continue
                if isinstance(ping_payload, dict) and ping_payload.get("ok") is True:
                    break
                time.sleep(0.2)
            else:
                raise TimeoutError(f"Release binary did not become ready within {startup_timeout} seconds")

            status_payload = _run_cli(exe_path, "status", "--host", host, "--port", str(port))
            _expect(status_payload.get("render_loop_running") is True, "Release binary responded, but render loop is not running")

            sources_payload = _run_cli(exe_path, "list-effect-sources", "--host", host, "--port", str(port))
            default_source = _find_default_source(sources_payload)
            _expect(default_source.get("kind") == "effect_set", "Default effect source is not loaded as effect_set")
            _expect(
                Path(str(default_source.get("path", ""))).name == DEFAULT_EFFECT_SET_FILENAME,
                "Default effect source path does not point to default-effects.lefxset",
            )

            effects_payload = _run_cli(exe_path, "list-effects", "--host", host, "--port", str(port))
            soft_pulse_summary = _find_effect(effects_payload, SOFT_PULSE_QUALIFIED_ID)
            direction_summary = _find_effect(effects_payload, DIRECTION_EFFECT_QUALIFIED_ID)
            _expect(soft_pulse_summary.get("source_kind") == "effect_set", "soft_pulse was not loaded from the effect set")
            _expect(direction_summary.get("source_kind") == "effect_set", "direction_indicator was not loaded from the effect set")

            soft_pulse_effect = _run_cli(
                exe_path,
                "show-effect",
                SOFT_PULSE_QUALIFIED_ID,
                "--host",
                host,
                "--port",
                str(port),
            )
            _expect("background_color" in soft_pulse_effect.get("parameters", {}), "soft_pulse is missing background_color")
            _expect("base_color" not in soft_pulse_effect.get("parameters", {}), "soft_pulse still exposes base_color")

            presets_payload = _run_cli(
                exe_path,
                "list-effect-presets",
                SOFT_PULSE_QUALIFIED_ID,
                "--host",
                host,
                "--port",
                str(port),
            )
            preset_ids = {
                item.get("preset_id")
                for item in _items_payload(presets_payload, label="list-effect-presets")
                if isinstance(item, dict)
            }
            _expect(
                {"state_soft_pulse_idle", "effect_soft_pulse_main"}.issubset(preset_ids),
                "soft_pulse presets are incomplete in the release binary",
            )

            commands_payload = _run_cli(
                exe_path,
                "list-effect-commands",
                SOFT_PULSE_QUALIFIED_ID,
                "--host",
                host,
                "--port",
                str(port),
            )
            command_names = {
                item.get("command_name")
                for item in _items_payload(commands_payload, label="list-effect-commands")
                if isinstance(item, dict)
            }
            _expect(SOFT_PULSE_COMMAND_NAME in command_names, "soft_pulse command accent toggle is missing")

            apply_state_payload = _run_cli(
                exe_path,
                "apply-effect-preset",
                SOFT_PULSE_STATE_PRESET_ID,
                "--host",
                host,
                "--port",
                str(port),
            )
            state_visual = _layer_visual(apply_state_payload, "state_visual")
            _expect(
                apply_state_payload.get("active_effect_preset_id") == SOFT_PULSE_STATE_PRESET_ID,
                "State preset did not become the active preset",
            )
            _expect(
                "preset:default-effects:state_soft_pulse_idle" in _scene_layer_names(apply_state_payload),
                "State preset did not appear in the rendered scene",
            )

            apply_main_payload = _run_cli(
                exe_path,
                "apply-effect-preset",
                SOFT_PULSE_EFFECT_PRESET_ID,
                "--host",
                host,
                "--port",
                str(port),
            )
            main_visual = _active_main_visual(apply_main_payload)
            _expect(
                apply_main_payload.get("active_effect_preset_id") == SOFT_PULSE_EFFECT_PRESET_ID,
                "Main preset did not become the active preset",
            )
            _expect(main_visual.get("effect_id") == SOFT_PULSE_QUALIFIED_ID, "Main preset did not render soft_pulse on the main layer")
            _expect(
                "background_color" in main_visual.get("params", {}) and "base_color" not in main_visual.get("params", {}),
                "Main preset params are not normalized to background_color",
            )

            command_on_payload = _run_cli(
                exe_path,
                "invoke-command",
                DEFAULT_SOURCE_ID,
                SOFT_PULSE_COMMAND_NAME,
                "on",
                "--host",
                host,
                "--port",
                str(port),
            )
            _expect(_active_main_visual(command_on_payload).get("effect_id") == SOFT_PULSE_QUALIFIED_ID, "Command on did not activate soft_pulse")

            direction_payload = _run_cli(
                exe_path,
                "set-direction",
                str(DEFAULT_DIRECTION),
                "--host",
                host,
                "--port",
                str(port),
            )
            direction_visual = _layer_visual(direction_payload, "direction_visual")
            _expect(float(direction_payload.get("direction", -1.0)) == DEFAULT_DIRECTION, "Direction command did not update controller direction")
            _expect(
                direction_visual.get("effect_id") in {DIRECTION_EFFECT_QUALIFIED_ID, "direction_indicator"},
                "Direction overlay is not using direction_indicator",
            )
            _expect(direction_visual.get("params", {}).get("direction") == DEFAULT_DIRECTION, "Direction overlay params are not normalized")

            command_off_payload = _run_cli(
                exe_path,
                "invoke-command",
                DEFAULT_SOURCE_ID,
                SOFT_PULSE_COMMAND_NAME,
                "off",
                "--host",
                host,
                "--port",
                str(port),
            )
            _expect(command_off_payload.get("active_visual") is None, "Command off did not clear the main layer")
            _expect(
                _layer_visual(command_off_payload, "direction_visual").get("effect_id") in {DIRECTION_EFFECT_QUALIFIED_ID, "direction_indicator"},
                "Direction overlay disappeared unexpectedly after command off",
            )

            direction_effect = _run_cli(
                exe_path,
                "show-effect",
                DIRECTION_EFFECT_QUALIFIED_ID,
                "--host",
                host,
                "--port",
                str(port),
            )
            _expect("direction" in direction_effect.get("parameters", {}), "direction_indicator is missing direction")
            _expect("direction_deg" not in direction_effect.get("parameters", {}), "direction_indicator still exposes direction_deg")

            shutdown_payload = _run_cli(exe_path, "shutdown", "--host", host, "--port", str(port))
            _await_shutdown(exe_path, process, host, port, shutdown_timeout)
            return {
                "ok": True,
                "ping": ping_payload,
                "status": status_payload,
                "default_source": default_source,
                "soft_pulse": soft_pulse_effect,
                "direction_indicator": direction_effect,
                "shutdown": shutdown_payload,
            }
        except Exception as exc:
            raise RuntimeError(f"{exc}\n\nService log tail:\n{_service_log_tail(log_path)}") from exc
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    result = verify_release_binary(
        exe_path=Path(args.exe_path).resolve(),
        host=args.host,
        port=int(args.port),
        startup_timeout=float(args.startup_timeout),
        shutdown_timeout=float(args.shutdown_timeout),
    )
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())