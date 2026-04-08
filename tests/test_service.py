from __future__ import annotations

from src.service import ControllerService


def test_service_falls_back_to_preview_and_starts_worker_when_adapter_init_fails():
    def broken_adapter():
        raise RuntimeError("device missing")

    service = ControllerService(use_device=True, adapter_factory=broken_adapter)

    assert service.snapshot()["output_mode"] == "console-preview"
    assert service.snapshot()["fallback_active"] is True
    assert "device missing" in service.snapshot()["last_error"]

    service.start()
    try:
        assert service.snapshot()["render_loop_running"] is True
    finally:
        service.stop()