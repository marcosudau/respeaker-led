from __future__ import annotations

import json
import os
import signal
import socket
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from .client import LocalControllerClient


DEFAULT_SERVICE_PORT = 8765
DEFAULT_PORT_POOL = [8765, 8766, 8767, 8768, 8769, 8770]


@dataclass(slots=True)
class ActiveServiceInfo:
    instance_id: str
    pid: int
    host: str
    port: int
    requested_port: int
    port_pool: list[int] = field(default_factory=list)
    status: str = "binding"
    started_at: float = 0.0
    log_file: str | None = None


def parse_port_pool(value: str | None) -> list[int]:
    if value is None:
        return []

    ports: list[int] = []
    for raw_chunk in str(value).split(","):
        chunk = raw_chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start_text, end_text = chunk.split("-", 1)
            start = int(start_text.strip())
            end = int(end_text.strip())
            if end < start:
                start, end = end, start
            ports.extend(range(start, end + 1))
            continue
        ports.append(int(chunk))

    return _deduplicate_ports(ports)


def default_port_pool() -> list[int]:
    return list(DEFAULT_PORT_POOL)


def select_service_port(host: str, requested_port: int, port_pool: list[int] | None = None) -> int:
    candidates = _deduplicate_ports([int(requested_port), *(port_pool or [])])
    for candidate in candidates:
        if is_port_available(host, candidate):
            return candidate
    joined = ", ".join(str(port) for port in candidates)
    raise RuntimeError(f"No free port available for host {host!r}. Checked: {joined}")


def is_port_available(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, int(port)))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def create_active_service_info(
    *,
    host: str,
    port: int,
    requested_port: int,
    port_pool: list[int] | None = None,
    log_file: str | None = None,
) -> ActiveServiceInfo:
    return ActiveServiceInfo(
        instance_id=uuid.uuid4().hex,
        pid=os.getpid(),
        host=str(host),
        port=int(port),
        requested_port=int(requested_port),
        port_pool=list(port_pool or []),
        status="binding",
        started_at=time.time(),
        log_file=log_file,
    )


def load_active_service_info(path: str | Path) -> ActiveServiceInfo | None:
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
        return ActiveServiceInfo(
            instance_id=str(payload.get("instance_id", "")).strip(),
            pid=int(payload.get("pid", 0)),
            host=str(payload.get("host", "127.0.0.1")),
            port=int(payload.get("port", 0)),
            requested_port=int(payload.get("requested_port", payload.get("port", 0))),
            port_pool=[int(item) for item in payload.get("port_pool", [])],
            status=str(payload.get("status", "binding")),
            started_at=float(payload.get("started_at", 0.0)),
            log_file=None if payload.get("log_file") in {None, ""} else str(payload.get("log_file")),
        )
    except (TypeError, ValueError):
        return None


def save_active_service_info(path: str | Path, info: ActiveServiceInfo) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "instance_id": info.instance_id,
        "pid": int(info.pid),
        "host": info.host,
        "port": int(info.port),
        "requested_port": int(info.requested_port),
        "port_pool": [int(port) for port in info.port_pool],
        "status": info.status,
        "started_at": float(info.started_at),
        "log_file": info.log_file,
    }
    file_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")


def update_active_service_status(path: str | Path, instance_id: str, status: str) -> None:
    info = load_active_service_info(path)
    if info is None or info.instance_id != instance_id:
        return
    info.status = str(status)
    save_active_service_info(path, info)


def clear_active_service_info(path: str | Path, *, instance_id: str | None = None) -> None:
    file_path = Path(path)
    if not file_path.exists():
        return
    if instance_id is not None:
        info = load_active_service_info(file_path)
        if info is None or info.instance_id != instance_id:
            return
    file_path.unlink(missing_ok=True)


def take_over_existing_instance(path: str | Path, *, timeout: float = 2.0) -> ActiveServiceInfo | None:
    existing = load_active_service_info(path)
    if existing is None:
        return None
    if existing.pid <= 0 or existing.pid == os.getpid():
        return existing
    if not _pid_exists(existing.pid):
        return existing

    client = LocalControllerClient(host=existing.host, port=existing.port, timeout=0.5, best_effort=True)
    client.shutdown()
    if _wait_for_pid_exit(existing.pid, timeout):
        return existing

    _force_terminate_pid(existing.pid)
    if _wait_for_pid_exit(existing.pid, timeout):
        return existing

    raise RuntimeError(
        f"Existing controller instance could not be stopped (pid={existing.pid}, host={existing.host}, port={existing.port})"
    )


def service_binding_message(info: ActiveServiceInfo) -> dict[str, object]:
    return {
        "event": "service_binding",
        "instance_id": info.instance_id,
        "pid": info.pid,
        "host": info.host,
        "port": info.port,
        "requested_port": info.requested_port,
        "port_pool": list(info.port_pool),
        "status": info.status,
        "log_file": info.log_file,
    }


def _deduplicate_ports(ports: list[int]) -> list[int]:
    ordered: list[int] = []
    seen: set[int] = set()
    for raw_port in ports:
        port = int(raw_port)
        if port <= 0:
            continue
        if port not in seen:
            ordered.append(port)
            seen.add(port)
    return ordered


def _wait_for_pid_exit(pid: int, timeout: float) -> bool:
    deadline = time.monotonic() + max(0.0, float(timeout))
    while time.monotonic() < deadline:
        if not _pid_exists(pid):
            return True
        time.sleep(0.05)
    return not _pid_exists(pid)


def _force_terminate_pid(pid: int) -> None:
    try:
        os.kill(int(pid), signal.SIGTERM)
    except OSError:
        return


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(int(pid), 0)
    except OSError:
        return False
    return True