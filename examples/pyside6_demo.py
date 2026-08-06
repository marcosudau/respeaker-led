"""PySide6 Demo: Direct Embedded ControllerService Integration.

This example demonstrates how to integrate the reSpeaker LED Controller directly
into a PySide6 GUI application (running in the same Python process).
The GUI thread controls state/events/sliders while the ControllerService
runs its background rendering loop and USB connection manager concurrently.

Run with:
    uv run python examples/pyside6_demo.py [--device]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is in sys.path when running as a standalone script
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from src import ControllerService


class VirtualLedRingWidget(QWidget):
    """Custom widget that draws a 12-LED ring visualization in real-time."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(180, 180)
        self._colors: list[int] = [0] * 12

    def update_leds(self, leds: list[int]) -> None:
        if len(leds) == 12:
            self._colors = list(leds)
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        center_x = width / 2.0
        center_y = height / 2.0
        radius = min(width, height) / 2.0 - 25.0

        # Draw outer ring background
        painter.setPen(QPen(QColor(40, 44, 52), 4))
        painter.setBrush(QColor(20, 22, 28))
        painter.drawEllipse(
            int(center_x - radius - 10),
            int(center_y - radius - 10),
            int((radius + 10) * 2),
            int((radius + 10) * 2),
        )

        import math

        num_leds = 12
        led_radius = 10.0

        for i, color_int in enumerate(self._colors):
            angle_deg = (i * 360.0 / num_leds) - 90.0
            angle_rad = math.radians(angle_deg)
            x = center_x + radius * math.cos(angle_rad)
            y = center_y + radius * math.sin(angle_rad)

            r = (color_int >> 16) & 0xFF
            g = (color_int >> 8) & 0xFF
            b = color_int & 0xFF

            led_color = QColor(r, g, b)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(led_color)

            # Draw glowing LED dot
            painter.drawEllipse(
                int(x - led_radius),
                int(y - led_radius),
                int(led_radius * 2),
                int(led_radius * 2),
            )

        painter.end()


class LedControlDemoWindow(QMainWindow):
    """Main window embedding the ControllerService directly."""

    def __init__(self, *, use_device: bool = False) -> None:
        super().__init__()
        self.setWindowTitle("reSpeaker LED Controller — PySide6 Embedded Demo")
        self.resize(680, 520)

        # 1. Instantiate the embedded ControllerService
        self.service = ControllerService(fps=8.0, use_device=use_device)
        self.service.start()

        self._init_ui()

        # 2. Setup QTimer for status & virtual LED updates @ 20 FPS
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(50)
        self.update_timer.timeout.connect(self._on_ui_tick)
        self.update_timer.start()

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Dark theme stylesheet
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1c23; }
            QWidget { color: #e1e4ea; font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }
            QGroupBox { font-weight: bold; border: 1px solid #333842; border-radius: 8px; margin-top: 10px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #61afef; }
            QPushButton { background-color: #282c34; border: 1px solid #3e4451; border-radius: 6px; padding: 8px 16px; font-weight: 500; }
            QPushButton:hover { background-color: #353b45; border-color: #61afef; }
            QPushButton:pressed { background-color: #4b5263; }
            QLabel { color: #abb2bf; }
            QSlider::groove:horizontal { height: 6px; background: #282c34; border-radius: 3px; }
            QSlider::handle:horizontal { background: #61afef; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }
        """)

        main_layout = QHBoxLayout(central_widget)

        # Left Column: Controls
        left_layout = QVBoxLayout()

        # Group 1: Base State Selection
        state_box = QGroupBox("Base State (STT Workflow)")
        state_layout = QVBoxLayout(state_box)

        btn_idle = QPushButton("Idle / Off")
        btn_idle.clicked.connect(lambda: self.service.clear_state_target())

        btn_listening = QPushButton("🎤 Listening (Blue Solid)")
        btn_listening.setStyleSheet("QPushButton { border-left: 4px solid #00aa44; }")
        btn_listening.clicked.connect(
            lambda: self.service.set_state_target("solid_color", {"color": "0x00AAFF"})
        )

        btn_processing = QPushButton("⚙️ Processing (Orange Pulse)")
        btn_processing.setStyleSheet("QPushButton { border-left: 4px solid #ffaa00; }")
        btn_processing.clicked.connect(
            lambda: self.service.set_state_target("soft_pulse", {"color": "0xFFAA00"})
        )

        btn_speaking = QPushButton("🔊 Speaking (Green Pulse)")
        btn_speaking.setStyleSheet("QPushButton { border-left: 4px solid #00ff66; }")
        btn_speaking.clicked.connect(
            lambda: self.service.set_state_target("pulse_pattern", {"color": "0x00FF66"})
        )

        state_layout.addWidget(btn_idle)
        state_layout.addWidget(btn_listening)
        state_layout.addWidget(btn_processing)
        state_layout.addWidget(btn_speaking)
        left_layout.addWidget(state_box)

        # Group 2: Transient Events
        event_box = QGroupBox("Transient Events")
        event_layout = QHBoxLayout(event_box)

        btn_trigger = QPushButton("⚡ Wake Word Flash")
        btn_trigger.clicked.connect(
            lambda: self.service.emit_event_target("short_flash", {"color": "0xFFFFFF"})
        )

        btn_error = QPushButton("⚠️ Warning Flash")
        btn_error.clicked.connect(
            lambda: self.service.emit_event_target("warning_flash")
        )

        event_layout.addWidget(btn_trigger)
        event_layout.addWidget(btn_error)
        left_layout.addWidget(event_box)

        # Group 3: Adjustments (Brightness, Direction, Enable)
        adj_box = QGroupBox("Adjustments")
        adj_layout = QVBoxLayout(adj_box)

        # Brightness
        bright_label = QLabel("Brightness: 100%")
        bright_slider = QSlider(Qt.Orientation.Horizontal)
        bright_slider.setRange(0, 100)
        bright_slider.setValue(100)
        bright_slider.valueChanged.connect(
            lambda val: (
                self.service.set_brightness(val / 100.0),
                bright_label.setText(f"Brightness: {val}%"),
            )
        )
        adj_layout.addWidget(bright_label)
        adj_layout.addWidget(bright_slider)

        # Direction Marker
        dir_label = QLabel("Direction: Off")
        dir_slider = QSlider(Qt.Orientation.Horizontal)
        dir_slider.setRange(0, 359)
        dir_slider.setValue(0)
        dir_slider.valueChanged.connect(
            lambda val: (
                self.service.set_direction(float(val)),
                dir_label.setText(f"Direction: {val}°"),
            )
        )
        adj_layout.addWidget(dir_label)
        adj_layout.addWidget(dir_slider)

        # Master Enable
        chk_enable = QCheckBox("LED Output Enabled")
        chk_enable.setChecked(True)
        chk_enable.toggled.connect(lambda checked: self.service.set_enabled(checked))
        adj_layout.addWidget(chk_enable)

        left_layout.addWidget(adj_box)
        main_layout.addLayout(left_layout, stretch=1)

        # Right Column: Live Ring Preview & System Status
        right_layout = QVBoxLayout()

        preview_box = QGroupBox("Virtual LED Ring (Realtime)")
        preview_layout = QVBoxLayout(preview_box)
        self.ring_widget = VirtualLedRingWidget()
        preview_layout.addWidget(self.ring_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(preview_box)

        status_box = QGroupBox("Embedded Service Status")
        status_layout = QVBoxLayout(status_box)

        self.lbl_status = QLabel("Initializing...")
        self.lbl_status.setFont(QFont("Consolas", 10))
        self.lbl_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        status_layout.addWidget(self.lbl_status)

        right_layout.addWidget(status_box)
        main_layout.addLayout(right_layout, stretch=1)

    def _on_ui_tick(self) -> None:
        """Periodic UI update called by QTimer."""
        status = self.service.get_status()

        # Update virtual LED ring
        last_frame = getattr(self.service.adapter, "last_frame", None)
        if last_frame is not None and hasattr(last_frame, "leds"):
            self.ring_widget.update_leds(last_frame.leds)

        # Update status text
        mode = status.get("output_mode", "unknown")
        render_count = status.get("render_count", 0)
        usb_info = status.get("usb_connection")
        usb_state = usb_info.get("state", "n/a") if usb_info else "disabled"

        self.lbl_status.setText(
            f"Output Mode: {mode}\n"
            f"Render Loop: {'Running' if status.get('render_loop_running') else 'Stopped'} ({render_count} frames)\n"
            f"USB Hardware: {usb_state}\n"
            f"Target FPS: {status.get('fps', 8.0)}"
        )

    def closeEvent(self, event) -> None:
        """Clean shutdown of the embedded ControllerService when GUI closes."""
        self.update_timer.stop()
        self.service.stop()
        event.accept()


def main() -> int:
    parser = argparse.ArgumentParser(description="PySide6 Embedded LED Controller Demo")
    parser.add_argument("--device", action="store_true", help="Connect to physical reSpeaker USB hardware")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = LedControlDemoWindow(use_device=args.device)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
