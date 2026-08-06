from __future__ import annotations

from src import ControllerService


def test_controller_service_context_manager():
    with ControllerService(use_device=False) as service:
        assert service._thread is not None
        assert service._thread.is_alive()
        status = service.get_status()
        assert status["render_loop_running"] is True
        assert status["output_mode"] == "console-preview"

        result = service.set_state_target("solid_color", {"color": "0x00FF00"})
        assert result["ok"] is True

    assert service._thread is None
