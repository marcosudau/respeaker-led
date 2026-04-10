from __future__ import annotations

import time
from pathlib import Path

from led_controller_host import LedControllerRelease1


def main() -> None:
    package_root = Path(__file__).resolve().parents[1]
    controller = LedControllerRelease1(
        package_root / "led_controller_service.exe",
        on_output=lambda line: print(f"[service] {line}"),
    )

    binding = controller.start(use_device=False)
    print("binding:", binding)

    print("ping:", controller.ping())
    print("effects:", controller.list_effects())

    controller.apply_effect("solid_color", "main", {"color": "#224466", "brightness": 0.6})
    time.sleep(2.0)
    controller.clear_layer("main")

    controller.set_state("listening", {"source": "example"})
    time.sleep(1.0)
    controller.clear_state()

    controller.close()


if __name__ == "__main__":
    main()