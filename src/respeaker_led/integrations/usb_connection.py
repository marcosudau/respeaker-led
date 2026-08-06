from __future__ import annotations

import enum
import importlib.util
import threading
import time
from typing import Callable, Any, Optional

import usb.core
import usb.util

from ..infrastructure.logging_utils import get_logger
from ..infrastructure.paths import XVF_HOST_PATH

logger = get_logger("usb_connection")


class UsbConnectionState(enum.Enum):
    """Represents the current state of the USB connection."""
    DISCONNECTED = 1
    CONNECTING = 2
    CONNECTED = 3


class UsbConnectionManager:
    """Manages the USB connection to a reSpeaker XVF3800 device with automatic reconnection."""
    
    def __init__(
        self,
        *,
        retry_interval_s: float = 3.0,
        heartbeat_interval_s: float = 2.0,
        on_connected: Callable[[], None] | None = None,
        on_disconnected: Callable[[str], None] | None = None,
    ) -> None:
        self.retry_interval_s = retry_interval_s
        self.heartbeat_interval_s = heartbeat_interval_s
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected
        
        self._state = UsbConnectionState.DISCONNECTED
        self._device = None
        self._xvf_module = None
        
        # Concurrency
        self._io_lock = threading.RLock()
        self._state_lock = threading.RLock()
        self._stop_event = threading.Event()
        self._monitor_thread: threading.Thread | None = None
        
        # State & Stats
        self._ring_mode_dirty = True
        
        self._connect_count = 0
        self._disconnect_count = 0
        self._last_connected_at: float | None = None
        self._last_error = ""
        self._retry_count = 0

    @property
    def state(self) -> UsbConnectionState:
        with self._state_lock:
            return self._state
            
    @property  
    def is_connected(self) -> bool:
        return self.state == UsbConnectionState.CONNECTED
        
    @property
    def connection_stats(self) -> dict[str, Any]:
        with self._state_lock:
            return {
                "state": self._state.name,
                "connect_count": self._connect_count,
                "disconnect_count": self._disconnect_count,
                "last_connected_at": self._last_connected_at,
                "last_error": self._last_error,
                "retry_count": self._retry_count,
            }
            
    def start(self) -> None:
        """Starts the connection monitor thread."""
        with self._state_lock:
            if self._monitor_thread is not None and self._monitor_thread.is_alive():
                return
            self._stop_event.clear()
            self._monitor_thread = threading.Thread(
                target=self._connection_monitor, 
                daemon=True,
                name="UsbConnectionMonitor"
            )
            self._monitor_thread.start()

    def stop(self) -> None:
        """Stops the monitor thread and closes the connection."""
        self._stop_event.set()
        if self._monitor_thread is not None:
            self._monitor_thread.join(timeout=self.retry_interval_s + 1.0)
            self._monitor_thread = None
        self._disconnect("Stopped by user")

    def close(self) -> None:
        """Alias for stop()."""
        self.stop()
        
    def __enter__(self) -> UsbConnectionManager:
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

    def write(self, name: str, data: list) -> None:
        """Writes data to the USB device in a thread-safe manner."""
        with self._io_lock:
            if not self.is_connected or self._device is None:
                raise RuntimeError("USB device not connected")
            try:
                self._device.write(name, data)
            except (usb.core.USBError, usb.core.USBTimeoutError, Exception) as e:
                self._disconnect(f"Write error: {e}")
                raise

    def read(self, name: str) -> tuple:
        """Reads data from the USB device in a thread-safe manner."""
        with self._io_lock:
            if not self.is_connected or self._device is None:
                raise RuntimeError("USB device not connected")
            try:
                return self._device.read(name)
            except (usb.core.USBError, usb.core.USBTimeoutError, Exception) as e:
                self._disconnect(f"Read error: {e}")
                raise

    def consume_ring_mode_dirty(self) -> bool:
        """Returns True if ring mode is dirty, and clears the flag."""
        with self._state_lock:
            dirty = self._ring_mode_dirty
            self._ring_mode_dirty = False
            return dirty

    def _connection_monitor(self) -> None:
        """Background thread that manages the USB connection lifecycle."""
        while not self._stop_event.is_set():
            state = self.state
            
            if state in (UsbConnectionState.DISCONNECTED, UsbConnectionState.CONNECTING):
                if self._try_connect():
                    if self._stop_event.wait(self.heartbeat_interval_s):
                        break
                else:
                    if self._stop_event.wait(self.retry_interval_s):
                        break
            elif state == UsbConnectionState.CONNECTED:
                if not self._heartbeat():
                    # Heartbeat failed, disconnect handles state update
                    pass
                else:
                    if self._stop_event.wait(self.heartbeat_interval_s):
                        break

    def _load_xvf_module(self):
        """Dynamically loads the xvf_host module."""
        if self._xvf_module is None:
            spec = importlib.util.spec_from_file_location("xvf_host", XVF_HOST_PATH)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self._xvf_module = module
            else:
                raise RuntimeError(f"Could not load xvf_host module from {XVF_HOST_PATH}")
        return self._xvf_module

    def _try_connect(self) -> bool:
        """Attempts to connect to the USB device."""
        with self._state_lock:
            self._state = UsbConnectionState.CONNECTING
            self._retry_count += 1
            
        try:
            xvf_module = self._load_xvf_module()
            with self._io_lock:
                device = xvf_module.find()
                if device:
                    self._device = device
                    with self._state_lock:
                        self._state = UsbConnectionState.CONNECTED
                        self._connect_count += 1
                        self._last_connected_at = time.time()
                        self._retry_count = 0
                        self._ring_mode_dirty = True
                    logger.info("Successfully connected to USB device.")
                    if self.on_connected:
                        try:
                            self.on_connected()
                        except Exception as e:
                            logger.error(f"Error in on_connected callback: {e}")
                    return True
        except Exception as e:
            logger.debug(f"Connection attempt failed: {e}")
            
        with self._state_lock:
            self._state = UsbConnectionState.DISCONNECTED
        return False

    def _heartbeat(self) -> bool:
        """Performs a heartbeat read to verify connection is alive."""
        try:
            self.read("VERSION")
            return True
        except Exception as e:
            logger.warning(f"Heartbeat failed: {e}")
            return False

    def _disconnect(self, reason: str) -> None:
        """Handles disconnection logic, cleans up resources, and updates state."""
        with self._state_lock:
            if self._state == UsbConnectionState.DISCONNECTED:
                return
            
            logger.warning(f"USB Disconnected. Reason: {reason}")
            self._state = UsbConnectionState.DISCONNECTED
            self._disconnect_count += 1
            self._last_error = reason
            self._ring_mode_dirty = True
            
        with self._io_lock:
            if self._device is not None:
                try:
                    if hasattr(self._device, "dev") and self._device.dev:
                        usb.util.dispose_resources(self._device.dev)
                except Exception as e:
                    logger.debug(f"Error disposing USB resources: {e}")
                self._device = None

        if self.on_disconnected:
            try:
                self.on_disconnected(reason)
            except Exception as e:
                logger.error(f"Error in on_disconnected callback: {e}")
