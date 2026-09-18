# -*- coding: utf-8 -*-
"""
ClashBot AI - Remote Client ADB Worker & Emulator Agent
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar. All rights reserved.

Architecture:
- Completely decoupled from Host proprietary bot code.
- Manages local Android Emulator (MuMu, LDPlayer, BlueStacks, MEmu, Nox) on the user's PC.
- High-speed frame streaming: captures screencap, compresses to in-memory JPEG, emits frames.
- Low-latency input execution: executes tap, swipe, keyevent, and monkey launcher commands.
"""

import os
import sys
import time
import base64
import random
import logging
import threading
import subprocess
from io import BytesIO
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Callable

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("RemoteClient.AdbWorker")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Default known emulator ports
COMMON_EMULATOR_PORTS = [
    16384,  # MuMu Player 12 (Instance 1)
    16416,  # MuMu Player 12 (Instance 2)
    7555,   # MuMu Player 6 / X
    5555,   # LDPlayer / BlueStacks standard
    5557,   # LDPlayer multi-instance
    5565,   # BlueStacks Hyper-V
    21503,  # MEmu Player
    62001,  # NoxPlayer
]


class RemoteAdbWorker(QObject):
    """
    Local ADB worker running on the user's machine.
    Captures live game frames, executes tap/swipe commands, and communicates
    with the Cloud Container via the ClientBridge.
    """

    # Qt Signals for UI and Bridge integration
    device_connected = Signal(str, int)       # (host, port)
    device_disconnected = Signal()
    device_status_changed = Signal(str)       # Status text for UI
    frame_captured = Signal(bytes, int, int)  # (jpeg_bytes, width, height)
    action_executed = Signal(str, dict)       # (action_type, details)

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 16384,
        adb_path: Optional[str] = None,
        parent=None
    ):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.adb_bin = self._resolve_adb(adb_path)
        self.target_device = f"{self.host}:{self.port}"

        self._streaming = False
        self._stream_thread: Optional[threading.Thread] = None
        self._stream_fps = 4.0
        self._target_quality = 75
        self._max_width = 1280
        self._lock = threading.Lock()

        # Cache last good frame
        self._latest_jpeg: Optional[bytes] = None
        self._latest_w: int = 1280
        self._latest_h: int = 720

    def _resolve_adb(self, preferred: Optional[str] = None) -> str:
        """Find the local adb binary."""
        client_root = Path(__file__).resolve().parent
        candidates = [
            preferred,
            str(client_root / "tools" / "adb" / "adb.exe"),
            str(client_root.parent / "Host" / "src" / "Tools" / "adb" / "adb.exe"),
            r"C:\Users\aradh\Desktop\ClashBot-AI -DEV)\Remote Cliant\tools\adb\adb.exe",
            "adb.exe",
            "adb"
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return str(Path(c).resolve())
        return "adb"

    def set_target(self, host: str, port: int) -> None:
        """Update target emulator host and port."""
        with self._lock:
            self.host = host
            self.port = int(port)
            self.target_device = f"{self.host}:{self.port}"
        logger.info(f"Target emulator updated to {self.target_device}")

    # ------------------------------------------------------------------
    # Connection Management
    # ------------------------------------------------------------------
    def ping(self) -> bool:
        """Check if local emulator ADB port is currently responsive."""
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
                timeout=6,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            out = (res.stdout + res.stderr).lower()
            if "connected" in out or "already" in out:
                if self.ping():
                    self.device_connected.emit(self.host, self.port)
                    self.device_status_changed.emit(f"Connected to {self.target_device}")
                    return True
        except Exception as e:
            logger.warning(f"Connection error to {self.target_device}: {e}")
        return False

    def auto_detect_device(self) -> Optional[Tuple[str, int]]:
        """Probe common emulator ports to find an active device."""
        for port in COMMON_EMULATOR_PORTS:
            target = f"127.0.0.1:{port}"
            try:
                subprocess.run(
                    [self.adb_bin, "connect", target],
                    capture_output=True,
                    timeout=2,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                res = subprocess.run(
                    [self.adb_bin, "-s", target, "shell", "echo", "1"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                if res.returncode == 0 and res.stdout.strip() == "1":
                    self.set_target("127.0.0.1", port)
                    self.device_connected.emit("127.0.0.1", port)
                    self.device_status_changed.emit(f"Auto-detected emulator on port {port}")
                    return ("127.0.0.1", port)
            except Exception:
                continue
        return None

    def restart_adb_server(self) -> bool:
        """Restart local ADB server process."""
        try:
            subprocess.run(
                [self.adb_bin, "kill-server"],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            time.sleep(0.5)
            subprocess.run(
                [self.adb_bin, "start-server"],
                capture_output=True,
                timeout=8,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            return self.connect()
        except Exception as e:
            logger.error(f"Error restarting ADB server: {e}")
            return False

    # ------------------------------------------------------------------
    # Command Execution (Dispatched from Cloud Container)
    # ------------------------------------------------------------------
    def execute_action(self, action_dict: Dict[str, Any]) -> bool:
        """Execute action requested by the Cloud Container."""
        cmd_type = action_dict.get("cmd") or action_dict.get("action", "")
        cmd_type = cmd_type.lower()

        if cmd_type == "tap":
            x = int(action_dict.get("x", 0))
            y = int(action_dict.get("y", 0))
            jitter = bool(action_dict.get("jitter", True))
            return self.tap(x, y, jitter=jitter)

        elif cmd_type == "swipe":
            x1 = int(action_dict.get("x1", 0))
            y1 = int(action_dict.get("y1", 0))
            x2 = int(action_dict.get("x2", 0))
            y2 = int(action_dict.get("y2", 0))
            dur = int(action_dict.get("duration", 300))
            return self.swipe(x1, y1, x2, y2, duration_ms=dur)

        elif cmd_type == "keyevent":
            code = int(action_dict.get("code", 4))
            return self.keyevent(code)

        elif cmd_type == "text":
            text_str = str(action_dict.get("text", ""))
            return self.text(text_str)

        elif cmd_type == "launch_app":
            pkg = action_dict.get("package", "com.supercell.clashofclans")
            return self.launch_app(pkg)

        elif cmd_type == "force_stop":
            pkg = action_dict.get("package", "com.supercell.clashofclans")
            return self.force_stop(pkg)

        logger.warning(f"Unknown device action received: {action_dict}")
        return False

    def tap(self, x: int, y: int, jitter: bool = True) -> bool:
        """Execute screen tap on local emulator."""
        final_x = x + random.randint(-2, 2) if jitter else x
        final_y = y + random.randint(-2, 2) if jitter else y
        ok = self._shell(f"input tap {final_x} {final_y}")
        if ok:
            self.action_executed.emit("tap", {"x": final_x, "y": final_y})
        return ok

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        """Execute swipe/drag gesture on local emulator."""
        ok = self._shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")
        if ok:
            self.action_executed.emit("swipe", {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration": duration_ms})
        return ok

    def keyevent(self, keycode: int) -> bool:
        """Send Android key event (4=BACK, 3=HOME, 66=ENTER)."""
        ok = self._shell(f"input keyevent {keycode}")
        if ok:
            self.action_executed.emit("keyevent", {"code": keycode})
        return ok

    def text(self, msg: str) -> bool:
        """Send text input to the device with spaces escaped."""
        safe_msg = msg.replace(" ", "%s")
        ok = self._shell(f"input text {safe_msg}")
        if ok:
            self.action_executed.emit("text", {"text": msg})
        return ok

    def launch_app(self, package_name: str = "com.supercell.clashofclans") -> bool:
        """Launch Clash of Clans on local emulator."""
        logger.info(f"Launching {package_name}...")
        ok = self._shell(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
        if not ok:
            ok = self._shell(f"am start -n {package_name}/com.supercell.titan.GameApp")
        return ok

    def force_stop(self, package_name: str = "com.supercell.clashofclans") -> bool:
        """Force-stop Clash of Clans on local emulator."""
        return self._shell(f"am force-stop {package_name}")

    def _shell(self, cmd_str: str) -> bool:
        """Helper to run adb shell command."""
        if not self.target_device:
            return False
        cmd = [self.adb_bin, "-s", self.target_device, "shell"] + cmd_str.split()
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                timeout=8,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            return res.returncode == 0
        except Exception as e:
            logger.warning(f"ADB shell execution error: {e}")
            return False

    # ------------------------------------------------------------------
    # High-Speed Frame Capture & Streaming
    # ------------------------------------------------------------------
    def capture_frame_jpeg(self, quality: int = 75) -> Optional[bytes]:
        """
        Capture emulator frame via adb exec-out screencap and compress to JPEG buffer.
        Never writes to disk. Returns compressed bytes (~25-35 KB).
        """
        if not self.target_device:
            return None

        cmd = [self.adb_bin, "-s", self.target_device, "exec-out", "screencap", "-p"]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            if res.returncode != 0 or not res.stdout:
                return None
            raw_png = res.stdout

            # Compress PNG bytes to JPEG using PIL or OpenCV if available
            try:
                from PIL import Image
                img = Image.open(BytesIO(raw_png))
                w, h = img.size
                if w > self._max_width:
                    scale = self._max_width / float(w)
                    img = img.resize((self._max_width, int(h * scale)), Image.Resampling.BILINEAR)
                    w, h = img.size

                buf = BytesIO()
                # Convert RGBA to RGB for JPEG
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(buf, format="JPEG", quality=quality, optimize=True)
                jpeg_bytes = buf.getvalue()

                self._latest_jpeg = jpeg_bytes
                self._latest_w = w
                self._latest_h = h
                return jpeg_bytes
            except ImportError:
                # If PIL is not present, return raw PNG directly
                return raw_png

        except Exception as e:
            logger.warning(f"Frame capture error: {e}")
            return None

    def start_streaming(self, fps: float = 4.0, quality: int = 75) -> None:
        """Start background frame streaming thread."""
        if self._streaming:
            return
        self._streaming = True
        self._stream_fps = max(1.0, min(fps, 10.0))
        self._target_quality = quality
        self._stream_thread = threading.Thread(
            target=self._stream_loop,
            daemon=True,
            name="RemoteAdbStreamThread"
        )
        self._stream_thread.start()
        logger.info(f"Local ADB frame streaming started at {self._stream_fps} FPS (Q={quality})")

    def stop_streaming(self) -> None:
        """Stop background frame streaming."""
        self._streaming = False
        if self._stream_thread:
            self._stream_thread.join(timeout=1.0)
            self._stream_thread = None
        logger.info("Local ADB frame streaming stopped")

    def _stream_loop(self) -> None:
        """Continuously capture frames and emit signal."""
        interval = 1.0 / self._stream_fps
        while self._streaming:
            start_t = time.time()
            frame = self.capture_frame_jpeg(quality=self._target_quality)
            if frame:
                self.frame_captured.emit(frame, self._latest_w, self._latest_h)
            elapsed = time.time() - start_t
            sleep_t = max(0.01, interval - elapsed)
            time.sleep(sleep_t)

    def get_latest_frame(self) -> Optional[bytes]:
        """Return the most recently captured JPEG bytes."""
        return self._latest_jpeg

    def get_latest_frame_b64(self) -> Optional[str]:
        """Return the most recently captured JPEG as base64 string."""
        if self._latest_jpeg:
            return base64.b64encode(self._latest_jpeg).decode("ascii")
        return None
