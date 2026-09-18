# -*- coding: utf-8 -*-
"""
ClashBot AI - Ephemeral ADB Worker & Device Agent
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar. All rights reserved.

Architecture:
- Connects directly to local Android emulator (MuMu, BlueStacks, LDPlayer, Nox, MEmu).
- Executes low-level device actions: humanized anti-detection taps, swipes, inputs, keyevents.
- High-speed frame capture (in-memory compressed JPEG screencap).
- Auto-starts and recovers emulator via EmulatorWorker if connection is lost.
"""

import os
import sys
import time
import json
import random
import secrets
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Callable

logger = logging.getLogger("ClashBotAI.AdbWorker")

_worker_instance: Optional["AdbWorker"] = None


class AdbWorker:
    """
    High-performance ADB Device Agent communicating with local Android emulator.
    Handles device commands, screenshot capture, and automatic emulator bootstrapping.
    """

    def __init__(
        self,
        adb_bin: Optional[str] = None,
        host: str = "127.0.0.1",
        port: Optional[int] = None
    ):
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.host = host
        self.port = port
        self.adb_bin = self._resolve_adb_binary(adb_bin)
        self.target_device = ""

        # Session & authorization properties
        self._server_url: str = ""
        self._session_token: str = ""
        self._hwid: str = ""
        self._last_auth_check: float = 0.0

        # Load initial target from config if not specified
        if self.port is None:
            self._init_target_from_config()
        else:
            self.target_device = f"{self.host}:{self.port}"

    def _resolve_adb_binary(self, preferred: Optional[str] = None) -> str:
        """Find the adb.exe binary across common local candidate paths."""
        if preferred and os.path.isfile(preferred):
            return preferred

        candidates = [
            str(self.project_root / "Host" / "src" / "Tools" / "adb" / "adb.exe"),
            str(self.project_root / "src" / "Tools" / "adb" / "adb.exe"),
            r"C:\Users\aradh\Desktop\ClashBot-AI -DEV)\Host\src\Tools\adb\adb.exe",
            "adb"
        ]
        for cand in candidates:
            if cand != "adb" and os.path.isfile(cand):
                return cand

        # Fallback to system adb in PATH
        return "adb"

    def _init_target_from_config(self) -> None:
        """Initialize target emulator host and port from config.json."""
        try:
            from network.emulator_worker import get_emulator_worker
            emu_worker = get_emulator_worker()
            emu_type, inst_id, host, port = emu_worker.get_configured_emulator()
            self.host = host
            self.port = emu_worker.resolve_instance_port(emu_type, inst_id)
            self.target_device = f"{self.host}:{self.port}"
        except Exception as e:
            self.host = "127.0.0.1"
            self.port = 16384
            self.target_device = f"{self.host}:{self.port}"

    def set_target(self, host: str, port: int) -> None:
        """Set target emulator host and port."""
        self.host = host
        self.port = int(port)
        self.target_device = f"{self.host}:{self.port}"

    def configure_auth(self, token: str, hwid: str, server_url: str = "") -> None:
        """Bind worker to authenticated server session and machine HWID."""
        self._session_token = token
        self._hwid = hwid
        if server_url:
            self._server_url = server_url.rstrip("/")

    # -------------------------------------------------------------
    # Connection Management
    # -------------------------------------------------------------
    def is_connected(self) -> bool:
        """Quick check if target emulator port is active and responding."""
        return self.ping()

    def ping(self) -> bool:
        """Check if target emulator is currently responsive via ADB shell."""
        if not self.target_device:
            return False
        cmd = [self.adb_bin, "-s", self.target_device, "shell", "echo", "1"]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            return res.returncode == 0 and res.stdout.strip() == "1"
        except Exception:
            return False

    def connect(self) -> bool:
        """Connect to local emulator via ADB connect."""
        if not self.target_device:
            return False
        cmd = [self.adb_bin, "connect", self.target_device]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=8,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            out = (res.stdout + res.stderr).lower()
            if "connected" in out or "already" in out:
                return self.ping()
        except Exception as e:
            logger.warning(f"[AdbWorker] Connection error: {e}")
        return False

    def auto_start_emulator(self) -> bool:
        """Auto-detect and launch the configured Android emulator via EmulatorWorker."""
        try:
            from network.emulator_worker import get_emulator_worker
            emu_worker = get_emulator_worker()
            emu_type, inst_id, _, _ = emu_worker.get_configured_emulator()
            logger.info(f"[AdbWorker] Auto-starting emulator: {emu_type} (Instance {inst_id})...")
            return emu_worker.launch_emulator(emu_type, inst_id, wait_ready=True)
        except Exception as e:
            logger.warning(f"[AdbWorker] auto_start_emulator failed: {e}")
            return False

    def ensure_connected(
        self,
        timeout_sec: float = 35.0,
        status_cb: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Verify connection to target device. If offline or not responding,
        automatically launch the emulator and poll until connected.
        """
        if self.ping():
            return True

        if status_cb:
            status_cb("Connecting to emulator...")

        # Try connecting first
        if self.connect():
            return True

        # If offline, launch emulator automatically
        if status_cb:
            status_cb("Starting Android Emulator...")
        logger.info("[AdbWorker] Emulator offline. Launching emulator automatically...")
        self.auto_start_emulator()

        # Poll until responsive or timeout
        start = time.time()
        while time.time() - start < timeout_sec:
            elapsed = int(time.time() - start)
            if status_cb:
                status_cb(f"Waiting for emulator to boot ({elapsed}s)...")
            if self.connect():
                if status_cb:
                    status_cb("Emulator connected successfully.")
                logger.info("[AdbWorker] Successfully connected to emulator.")
                return True
            time.sleep(2.0)

        logger.warning(f"[AdbWorker] Timeout ({timeout_sec}s) connecting to emulator.")
        return False

    # -------------------------------------------------------------
    # Device Actions (Taps, Swipes, Inputs)
    # -------------------------------------------------------------
    def _route_cloud_action(self, action_dict: Dict[str, Any]) -> bool:
        """Helper to route actions through Cloud Bridge if active."""
        try:
            from ui.ui2client import get_latest_client_frame, send_device_action
            if get_latest_client_frame() is not None:
                send_device_action(action_dict)
                return True
        except ImportError:
            pass
        return False

    def tap(self, x: int, y: int, jitter: bool = True) -> bool:
        """Execute screen tap with anti-detection humanized jitter."""
        final_x = x + random.randint(-2, 2) if jitter else x
        final_y = y + random.randint(-2, 2) if jitter else y
        if self._route_cloud_action({"cmd": "tap", "x": final_x, "y": final_y}):
            return True
        return self.shell(f"input tap {final_x} {final_y}")

    def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration_ms: int = 300
    ) -> bool:
        """Execute screen drag or swipe."""
        if self._route_cloud_action({"cmd": "swipe", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration": duration_ms}):
            return True
        return self.shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")

    def keyevent(self, keycode: int) -> bool:
        """Send Android keyevent (e.g. 4 for Back, 3 for Home, 66 for Enter)."""
        if self._route_cloud_action({"cmd": "keyevent", "code": keycode}):
            return True
        return self.shell(f"input keyevent {keycode}")

    def text(self, msg: str) -> bool:
        """Send text input to the device with spaces escaped."""
        if self._route_cloud_action({"cmd": "text", "text": msg}):
            return True
        safe_msg = msg.replace(" ", "%s")
        return self.shell(f"input text {safe_msg}")

    def launch_app(self, package_name: str = "com.supercell.clashofclans") -> bool:
        """Launch an Android application by package name."""
        logger.info(f"[AdbWorker] Launching {package_name}...")
        ok = self.shell(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
        if not ok:
            ok = self.shell(f"am start -n {package_name}/com.supercell.titan.GameApp")
        return ok

    def force_stop(self, package_name: str = "com.supercell.clashofclans") -> bool:
        """Force-stop an Android application."""
        logger.info(f"[AdbWorker] Force-stopping {package_name}...")
        return self.shell(f"am force-stop {package_name}")

    def is_app_in_foreground(self, package_name: str = "com.supercell.clashofclans") -> bool:
        """Check if package is the current focused foreground app."""
        if not self.target_device:
            return False
        cmd = [self.adb_bin, "-s", self.target_device, "shell", "dumpsys", "window"]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            for line in res.stdout.splitlines():
                if "mCurrentFocus" in line and package_name in line:
                    return True
        except Exception:
            pass
        return False

    def shell(self, cmd_str: str) -> bool:
        """Execute an ADB shell command on the target device."""
        if not self.target_device:
            return False
        cmd = [self.adb_bin, "-s", self.target_device, "shell"] + cmd_str.split()
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                timeout=12,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            return res.returncode == 0
        except Exception:
            return False

    # -------------------------------------------------------------
    # Screen Capture (Raw & In-Memory Compressed)
    # -------------------------------------------------------------
    def screencap(self) -> Optional[bytes]:
        """Grab raw screenshot bytes (PNG) directly from the emulator device."""
        try:
            from ui.ui2client import get_latest_client_frame
            cloud_frame = get_latest_client_frame()
            if cloud_frame is not None:
                return cloud_frame
        except ImportError:
            pass

        if not self.target_device:
            return None
        cmd = [self.adb_bin, "-s", self.target_device, "exec-out", "screencap", "-p"]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            if res.returncode == 0 and res.stdout:
                return res.stdout
        except Exception as e:
            logger.warning(f"[AdbWorker] screencap failed: {e}")
        return None

    def screencap_compressed(
        self,
        quality: int = 80,
        max_width: int = 1280
    ) -> Optional[bytes]:
        """
        Grab screenshot and compress in-memory as JPEG bytes.
        Never touches disk, providing high-speed low-latency frames.
        """
        try:
            from ui.ui2client import get_latest_client_frame
            cloud_frame = get_latest_client_frame()
            if cloud_frame is not None:
                # Cloud frame is already a compressed JPEG from the user's PC, return it directly!
                return cloud_frame
        except ImportError:
            pass

        raw = self.screencap()
        if not raw:
            return None

        try:
            import cv2
            import numpy as np

            buf = np.frombuffer(raw, dtype=np.uint8)
            img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if img is None:
                return raw

            # Resize if width exceeds max_width
            h, w = img.shape[:2]
            if w > max_width:
                scale = float(max_width) / float(w)
                new_size = (max_width, int(h * scale))
                img = cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)

            ok, encoded = cv2.imencode(
                ".jpg",
                img,
                [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            )
            if ok:
                return encoded.tobytes()

        except Exception as e:
            logger.warning(f"[AdbWorker] screencap_compressed failed: {e}")

        return raw

    def restart_adb_server(self) -> bool:
        """Kill and restart ADB server daemon, reconnecting to target device."""
        logger.info("[AdbWorker] Restarting ADB server...")
        try:
            subprocess.run(
                [self.adb_bin, "kill-server"],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            time.sleep(1.0)
            subprocess.run(
                [self.adb_bin, "start-server"],
                capture_output=True,
                timeout=8,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            time.sleep(1.0)
            return self.connect()
        except Exception as e:
            logger.warning(f"[AdbWorker] restart_adb_server failed: {e}")
            return False

    def zoom_out(self) -> bool:
        """Pinch zoom out to center and expose full village view."""
        try:
            import ui2_zoom
            return ui2_zoom.zoom_out(self.target_device)
        except Exception:
            return self.swipe(960, 400, 960, 200, 300)

    def screencap_cv2(self):
        """
        Grab screenshot and decode directly as OpenCV BGR numpy.ndarray.
        Returns None if capture fails or cv2/numpy unavailable.
        """
        raw = self.screencap()
        if not raw:
            return None
        try:
            import cv2
            import numpy as np
            buf = np.frombuffer(raw, dtype=np.uint8)
            return cv2.imdecode(buf, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.warning(f"[AdbWorker] screencap_cv2 failed: {e}")
            return None

    # -------------------------------------------------------------
    # Batch Action Execution
    # -------------------------------------------------------------
    def execute_server_actions(self, actions: List[Dict[str, Any]]) -> int:
        """
        Execute an action batch (taps, swipes, keyevents, delays)
        with anti-detection timing and error handling.
        """
        executed = 0
        for act in actions:
            act_type = str(act.get("type", "")).lower().strip()
            delay = float(act.get("delay", 0.05))

            if act_type == "tap":
                x = int(act.get("x", 0))
                y = int(act.get("y", 0))
                self.tap(x, y)
                executed += 1

            elif act_type == "swipe":
                x1 = int(act.get("x1", 0))
                y1 = int(act.get("y1", 0))
                x2 = int(act.get("x2", 0))
                y2 = int(act.get("y2", 0))
                dur = int(act.get("duration", 300))
                self.swipe(x1, y1, x2, y2, duration_ms=dur)
                executed += 1

            elif act_type == "keyevent":
                code = int(act.get("keycode", 4))
                self.keyevent(code)
                executed += 1

            elif act_type == "zoom_out":
                self.zoom_out()
                executed += 1

            elif act_type == "launch_app":
                pkg = str(act.get("package", "com.supercell.clashofclans"))
                self.launch_app(pkg)
                executed += 1

            elif act_type == "force_stop":
                pkg = str(act.get("package", "com.supercell.clashofclans"))
                self.force_stop(pkg)
                executed += 1

            if delay > 0:
                time.sleep(delay)

        return executed


# -----------------------------------------------------------------
# Qt QThread Background Worker for Async Non-Blocking Operations
# -----------------------------------------------------------------
try:
    from PySide6.QtCore import QThread, Signal
except ImportError:
    class QThread:
        def __init__(self, parent=None): pass
        def start(self): self.run()
        def wait(self, timeout=None): pass
        def isRunning(self): return False
    def Signal(*args):
        class _Signal:
            def __init__(self): self._cbs = []
            def emit(self, *a, **kw):
                for cb in self._cbs:
                    try: cb(*a, **kw)
                    except Exception: pass
            def connect(self, fn): self._cbs.append(fn)
        return _Signal()


class AdbWorkerThread(QThread):
    """
    Asynchronous Qt background worker managing ADB connection monitoring,
    frame capture streaming, and action dispatching without blocking GUI.
    """
    connected = Signal(str)        # device_target
    disconnected = Signal()
    status_changed = Signal(str)
    frame_ready = Signal(bytes)    # compressed jpeg frame
    action_completed = Signal(str) # action name
    error = Signal(str)

    def __init__(
        self,
        mode: str = "connect",       # "connect", "stream", "action", "restart"
        action_data: Optional[Any] = None,
        poll_interval: float = 2.0,
        parent=None
    ):
        super().__init__(parent)
        self.mode = mode
        self.action_data = action_data
        self.poll_interval = poll_interval
        self._is_running = True
        self.worker = get_adb_worker()

    def stop(self):
        self._is_running = False

    def run(self):
        try:
            if self.mode == "restart":
                self.status_changed.emit("Restarting ADB Server...")
                ok = self.worker.restart_adb_server()
                if ok:
                    self.connected.emit(self.worker.target_device)
                    self.status_changed.emit(f"ADB Connected to {self.worker.target_device}")
                else:
                    self.disconnected.emit()
                    self.error.emit("Failed to connect after ADB restart")
                return

            if self.mode == "connect":
                self.status_changed.emit(f"Connecting to {self.worker.target_device}...")
                ok = self.worker.ensure_connected(
                    timeout_sec=35.0,
                    status_cb=lambda msg: self.status_changed.emit(msg)
                )
                if ok:
                    self.connected.emit(self.worker.target_device)
                    self.status_changed.emit(f"ADB Connected to {self.worker.target_device}")
                else:
                    self.disconnected.emit()
                    self.error.emit("Could not connect to device")
                return

            if self.mode == "action":
                if isinstance(self.action_data, list):
                    count = self.worker.execute_server_actions(self.action_data)
                    self.action_completed.emit(f"Executed {count} actions")
                return

            if self.mode == "stream":
                while self._is_running:
                    if self.worker.ping():
                        frame = self.worker.screencap_compressed(quality=70, max_width=960)
                        if frame:
                            self.frame_ready.emit(frame)
                    else:
                        self.disconnected.emit()
                    time.sleep(self.poll_interval)

        except Exception as e:
            logger.error(f"[AdbWorkerThread] Error in run: {e}")
            self.error.emit(str(e))


def get_adb_worker(
    adb_bin: Optional[str] = None,
    host: str = "127.0.0.1",
    port: Optional[int] = None
) -> AdbWorker:
    """Singleton getter for AdbWorker."""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = AdbWorker(adb_bin, host, port)
    return _worker_instance

