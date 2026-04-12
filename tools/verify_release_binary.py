from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smoke-test the built release binary by starting, pinging, querying status and shutting it down.")
    parser.add_argument("exe_path")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8771)
    parser.add_argument("--startup-timeout", type=float, default=20.0)
    parser.add_argument("--shutdown-timeout", type=float, default=20.0)
    return parser


def _run_cli(exe_path: Path, *args: str) -> dict:
    completed = subprocess.run(
        [str(exe_path), *args],
        cwd=str(exe_path.parent),
        check=True,
        capture_output=True,
        text=True,
    )
    output = completed.stdout.strip()
    return {} if not output else json.loads(output)


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

    process = subprocess.Popen(
        [str(exe_path), "--no-device", "serve", "--host", host, "--port", str(port)],
        cwd=str(exe_path.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + max(0.1, startup_timeout)
        ping_payload: dict | None = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Release binary exited unexpectedly with code {process.returncode}")
            try:
                ping_payload = _run_cli(exe_path, "ping", "--host", host, "--port", str(port))
            except Exception:
                time.sleep(0.2)
                continue
            if ping_payload.get("ok") is True:
                break
            time.sleep(0.2)
        else:
            raise TimeoutError(f"Release binary did not become ready within {startup_timeout} seconds")

        status_payload = _run_cli(exe_path, "status", "--host", host, "--port", str(port))
        if status_payload.get("render_loop_running") is not True:
            raise RuntimeError("Release binary responded, but render loop is not running")

        shutdown_payload = _run_cli(exe_path, "shutdown", "--host", host, "--port", str(port))
        process.wait(timeout=max(0.1, shutdown_timeout))
        return {
            "ok": True,
            "ping": ping_payload,
            "status": status_payload,
            "shutdown": shutdown_payload,
        }
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