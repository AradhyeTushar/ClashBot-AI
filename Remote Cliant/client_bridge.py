# -*- coding: utf-8 -*-
"""
ClashBot AI - Remote Client Bridge
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar. All rights reserved.

Maintains an asynchronous, robust TCP socket connection to the Host UI ui2client bridge.
Emits Qt signals when state updates or log messages arrive.
"""

import sys
import json
import time
import base64
import socket
import threading
from typing import Dict, Any, Optional

from PySide6.QtCore import QObject, Signal

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 29170


class ClientBridge(QObject):
    """Bridge communicating with Host UI ui2client server."""

    # Qt Signals for thread-safe UI updates
    connected = Signal()
    disconnected = Signal()
    full_state_received = Signal(dict)
    page_switched = Signal(str, int)
    widget_updated = Signal(str, str, object)  # (widget_type, name, value)
    log_received = Signal(str)
    action_confirmed = Signal(dict)
    status_message = Signal(str)
    host_ready = Signal(bool)
    window_title_received = Signal(str)

    # Device action & streaming signals
    device_action_received = Signal(dict)
    stream_control_received = Signal(bool)

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port

        self._socket: Optional[socket.socket] = None
        self._running = False
        self._connected = False
        self._thread: Optional[threading.Thread] = None
        self._send_lock = threading.Lock()
        self._adb_worker: Optional[Any] = None

    def start(self) -> None:
        """Start the background connection worker thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._connection_loop,
            daemon=True,
            name="RemoteClientBridgeLoop"
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop connection and close socket."""
        self._running = False
        self._connected = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

    def is_connected(self) -> bool:
        return self._connected

    def _connection_loop(self) -> None:
        """Continuously attempt connection and handle incoming messages."""
        while self._running:
            try:
                self.status_message.emit(f"Connecting to Host UI ({self.host}:{self.port})...")
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5.0)
                s.connect((self.host, self.port))
                s.settimeout(None)

                self._socket = s
                self._connected = True
                self.connected.emit()
                self.status_message.emit("Connected to Host UI Engine")

                buffer = ""
                while self._running and self._connected:
                    data = s.recv(4096)
                    if not data:
                        break
                    buffer += data.decode("utf-8", errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        self._handle_incoming_message(line)

            except (ConnectionRefusedError, socket.timeout):
                pass
            except (ConnectionResetError, BrokenPipeError):
                pass
            except Exception as e:
                self.status_message.emit(f"Bridge notice: {e}")
            finally:
                if self._connected:
                    self._connected = False
                    self.disconnected.emit()
                    self.status_message.emit("Disconnected from Host UI. Retrying...")
                if self._socket:
                    try:
                        self._socket.close()
                    except Exception:
                        pass
                    self._socket = None

            if self._running:
                time.sleep(1.5)

    def _handle_incoming_message(self, line: str) -> None:
        """Parse line as JSON and emit corresponding Qt signal."""
        try:
            msg = json.loads(line)
            msg_type = msg.get("type", "")

            if msg_type == "full_state":
                self.full_state_received.emit(msg)
                if "ready" in msg:
                    self.host_ready.emit(bool(msg["ready"]))

            elif msg_type == "host_ready":
                self.host_ready.emit(bool(msg.get("ready", True)))

            elif msg_type == "log":
                self.log_received.emit(msg.get("text", ""))

            elif msg_type == "page_switched":
                page_name = msg.get("page_name", "")
                page_idx = msg.get("page_index", 0)
                self.page_switched.emit(page_name, page_idx)

            elif msg_type == "widget_update":
                w_type = msg.get("widget_type", "")
                w_name = msg.get("name", "")
                w_val = msg.get("value")
                self.widget_updated.emit(w_type, w_name, w_val)

            elif msg_type == "action_executed":
                self.action_confirmed.emit(msg)

            elif msg_type == "window_title":
                title = msg.get("title", "")
                if title:
                    self.window_title_received.emit(title)

            elif msg_type == "device_action":
                self.device_action_received.emit(msg)
                if self._adb_worker:
                    self._adb_worker.execute_action(msg)

            elif msg_type == "start_stream":
                self.stream_control_received.emit(True)
                if self._adb_worker:
                    fps = float(msg.get("fps", 4.0))
                    quality = int(msg.get("quality", 75))
                    self._adb_worker.start_streaming(fps=fps, quality=quality)

            elif msg_type == "stop_stream":
                self.stream_control_received.emit(False)
                if self._adb_worker:
                    self._adb_worker.stop_streaming()

            elif msg_type == "request_frame":
                if self._adb_worker:
                    frame = self._adb_worker.capture_frame_jpeg()
                    if frame:
                        self.send_frame(frame, self._adb_worker._latest_w, self._adb_worker._latest_h)

            elif msg_type == "pong":
                pass

        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"[RemoteBridge] Error processing message: {e}")

    def send_action(self, action_dict: Dict[str, Any]) -> bool:
        """Send a command JSON message to Host UI."""
        if not self._connected or not self._socket:
            return False
        try:
            payload = (json.dumps(action_dict, ensure_ascii=False) + "\n").encode("utf-8")
            with self._send_lock:
                self._socket.sendall(payload)
            return True
        except Exception as e:
            print(f"[RemoteBridge] Send error: {e}")
            self._connected = False
            return False

    def attach_adb_worker(self, worker) -> None:
        """Attach local AdbWorker for bi-directional device command streaming."""
        self._adb_worker = worker
        self._adb_worker.frame_captured.connect(self.send_frame)

    def send_frame(self, jpeg_bytes: bytes, w: int, h: int) -> bool:
        """Forward local emulator frame to Cloud Host Container."""
        try:
            b64_data = base64.b64encode(jpeg_bytes).decode("ascii")
            return self.send_action({
                "type": "device_frame",
                "timestamp": time.time(),
                "width": w,
                "height": h,
                "data": b64_data
            })
        except Exception as e:
            print(f"[RemoteBridge] Frame forwarding error: {e}")
            return False

    # Convenience helper methods
    def switch_page(self, page_name: str) -> bool:
        return self.send_action({"action": "switch_page", "target": page_name})

    def click_button(self, button_name: str) -> bool:
        return self.send_action({"action": "click_button", "target": button_name})

    def set_checkbox(self, attr_name: str, checked: bool) -> bool:
        return self.send_action({"action": "set_checkbox", "target": attr_name, "value": checked})

    def set_combobox(self, attr_name: str, text: str) -> bool:
        return self.send_action({"action": "set_combobox", "target": attr_name, "value": text})

    def set_spinbox(self, attr_name: str, val: int) -> bool:
        return self.send_action({"action": "set_spinbox", "target": attr_name, "value": int(val)})

    def start_bot(self) -> bool:
        return self.click_button("start")

    def stop_bot(self) -> bool:
        return self.click_button("stop")

    def pause_bot(self) -> bool:
        return self.click_button("pause")

    def restart_adb(self) -> bool:
        return self.click_button("restart_adb")

    def toggle_settings(self) -> bool:
        return self.click_button("settings_toggle")

    def focus_host(self) -> bool:
        return self.send_action({"action": "focus_host"})

    def launch_emulator(self, emu_type: str = "mumu") -> bool:
        return self.send_action({"action": "click_button", "target": "launch_emulator", "value": emu_type})

    def close_emulator(self, emu_type: str = "mumu") -> bool:
        return self.send_action({"action": "click_button", "target": "close_emulator", "value": emu_type})

    def connect_adb(self) -> bool:
        return self.send_action({"action": "click_button", "target": "connect_adb"})

    def request_state_refresh(self) -> bool:
        return self.send_action({"type": "get_state"})

