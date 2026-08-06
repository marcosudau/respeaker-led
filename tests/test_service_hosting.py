from __future__ import annotations

import socket

from respeaker_led.services.service_hosting import (
    ActiveServiceInfo,
    create_active_service_info,
    default_port_pool,
    load_active_service_info,
    parse_port_pool,
    save_active_service_info,
    select_service_port,
    service_binding_message,
    take_over_existing_instance,
)


def _reserve_port() -> tuple[socket.socket, int]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    return sock, sock.getsockname()[1]


def test_parse_port_pool_supports_lists_and_ranges():
    assert parse_port_pool("8765,8766,8770-8772") == [8765, 8766, 8770, 8771, 8772]


def test_default_port_pool_uses_release_1_range():
    assert default_port_pool() == [8765, 8766, 8767, 8768, 8769, 8770]


def test_select_service_port_falls_back_to_pool_when_requested_port_is_busy():
    reserved, busy_port = _reserve_port()
    try:
        fallback_probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        fallback_probe.bind(("127.0.0.1", 0))
        fallback_port = fallback_probe.getsockname()[1]
        fallback_probe.close()

        selected = select_service_port("127.0.0.1", busy_port, [busy_port, fallback_port])

        assert selected == fallback_port
    finally:
        reserved.close()


def test_active_service_info_roundtrip_and_binding_message(tmp_path):
    runtime_file = tmp_path / "active_service.json"
    info = create_active_service_info(host="127.0.0.1", port=8765, requested_port=8765, port_pool=[8765, 8766], log_file="log.txt")

    save_active_service_info(runtime_file, info)
    loaded = load_active_service_info(runtime_file)
    message = service_binding_message(info)

    assert loaded is not None
    assert loaded.instance_id == info.instance_id
    assert loaded.port == 8765
    assert message["event"] == "service_binding"
    assert message["port_pool"] == [8765, 8766]


def test_take_over_existing_instance_requests_shutdown(monkeypatch, tmp_path):
    runtime_file = tmp_path / "active_service.json"
    info = ActiveServiceInfo(
        instance_id="existing",
        pid=12345,
        host="127.0.0.1",
        port=8765,
        requested_port=8765,
        port_pool=[8765],
        status="ready",
        started_at=1.0,
        log_file=None,
    )
    save_active_service_info(runtime_file, info)

    events: list[str] = []

    class FakeClient:
        def __init__(self, **kwargs):
            events.append(f"client:{kwargs['host']}:{kwargs['port']}")

        def shutdown(self):
            events.append("shutdown")
            return type("Result", (), {"ok": True})()

    monkeypatch.setattr("respeaker_led.services.service_hosting.LocalControllerClient", FakeClient)
    monkeypatch.setattr("respeaker_led.services.service_hosting._pid_exists", lambda pid: True)
    monkeypatch.setattr("respeaker_led.services.service_hosting._wait_for_pid_exit", lambda pid, timeout: True)

    taken_over = take_over_existing_instance(runtime_file)

    assert taken_over is not None
    assert taken_over.instance_id == "existing"
    assert events == ["client:127.0.0.1:8765", "shutdown"]