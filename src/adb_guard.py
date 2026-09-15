# -*- coding: utf-8 -*-
"""
ClashBot AI - ADB Device Call Guard & Security Interceptor
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Module: adb_guard
License: MIT License - Copyright (c) 2026 Aradhye Tushar. All rights reserved.

Verifies user session, HWID, and subscription entitlement on EVERY device ADB interaction.
Instantly halts execution and triggers file wipeout if unauthorized, expired, or revoked.
"""

import time
import json
import secrets
import os
import sys
import time
import json
import secrets
import logging
import threading
import subprocess
import urllib.request
from typing import Optional, Dict, Any, Callable
from runtime_manager import cleanup_runtime

logger = logging.getLogger("ClashBotAI.AdbGuard")

EMULATOR_PROCESSES = [
    "HD-Player.exe", "BlueStacks.exe", "BlueStacksServices.exe",
    "dnplayer.exe", "LdVBoxHeadless.exe", "dnconsole.exe",
    "MEmu.exe", "MEmuConsole.exe", "MEmuHeadless.exe",
    "Nox.exe", "NoxVMSVC.exe",
    "MuMuPlayer.exe", "MuMuNxMain.exe", "MuMuNxDevice.exe", "MuMuVMMHeadless.exe"
]


def kill_emulator_processes() -> None:
    """Terminate running Android emulators (BlueStacks, LDPlayer, MEmu, Nox, MuMu)."""
    logger.warning("[AdbGuard] Terminating Android Emulator processes...")
    for proc in EMULATOR_PROCESSES:
        try:
            subprocess.run(["taskkill", "/F", "/IM", proc], capture_output=True, timeout=3)
        except Exception:
            pass


class SecurityLockoutException(Exception):
    """Raised when an unauthorized device interaction is detected."""
    pass


class AdbGuard:
    """Security Guard that intercepts and validates all ADB commands."""

    _instance: Optional["AdbGuard"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "AdbGuard":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AdbGuard, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.session_token: Optional[str] = None
        self.username: str = ""
        self.user_id: int = 0
        self.tier: str = "free"
        self.hwid: str = ""
        self.server_url: str = "http://127.0.0.1:8000"
        self.is_authorized: bool = False
        self.last_heartbeat_time: float = 0.0
        self.lockout_triggered: bool = False
        self._call_counter: int = 0
        self._sync_check_interval: int = 25  # Server sync verification every 25 calls
        self.is_free_trial: bool = False
        self.remaining_seconds: int = 7200
        self.session_start_time: float = time.time()
        self._watchdog_running: bool = False

    def configure_session(
        self,
        token: str,
        user_info: Dict[str, Any],
        hwid: str,
        server_url: str = "http://127.0.0.1:8000"
    ) -> None:
        """Store active session credentials upon successful login."""
        self.session_token = token
        self.user_id = user_info.get("id", 0)
        self.username = user_info.get("username", "")
        self.tier = user_info.get("tier", "free")
        self.hwid = hwid
        self.server_url = server_url.rstrip("/")
        self.is_authorized = True
        self.lockout_triggered = False
        self.last_heartbeat_time = time.time()
        self.session_start_time = time.time()

        self.is_free_trial = bool(user_info.get("is_free_trial", self.tier == "free"))
        self.remaining_seconds = int(user_info.get("remaining_seconds", 7200))

        logger.info(f"[AdbGuard] Session configured for '{self.username}' (Tier: {self.tier}, Trial: {self.is_free_trial}, Remaining: {self.remaining_seconds}s)")

        if self.is_free_trial and not self._watchdog_running:
            self._watchdog_running = True
            threading.Thread(target=self._trial_watchdog_loop, daemon=True).start()

    def terminate_emulator_and_bot(self, reason: str = "2-Hour Free Trial expired") -> None:
        """Shut down the Android emulator, cleanup runtime binaries, and exit bot."""
        if self.lockout_triggered:
            return
        self.lockout_triggered = True
        self.is_authorized = False
        logger.critical(f"[AdbGuard] *** CRITICAL TRIAL TERMINATION ***: {reason}")
        
        # 1. Kill emulator processes
        kill_emulator_processes()
        
        # 2. Cleanup runtime files
        cleanup_runtime()
        
        # 3. Terminate bot client process
        time.sleep(0.5)
        os._exit(0)

    def _trial_watchdog_loop(self) -> None:
        """Background loop that tracks 2-Hour free trial and checks heartbeats."""
        while self.is_authorized and not self.lockout_triggered:
            time.sleep(5)
            elapsed = time.time() - self.session_start_time
            left = self.remaining_seconds - elapsed
            if left <= 0:
                self.terminate_emulator_and_bot("2-Hour Free Trial limit reached. Terminating emulator and bot.")
                break

            # Send periodic heartbeat to server every 60s
            if time.time() - self.last_heartbeat_time > 60:
                self._send_heartbeat()

    def _send_heartbeat(self) -> None:
        """Periodic server heartbeat to sync trial status."""
        try:
            url = f"{self.server_url}/api/auth/heartbeat"
            payload = json.dumps({"token": self.session_token, "hwid": self.hwid}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.session_token}"}
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self.last_heartbeat_time = time.time()
                if data.get("close_emulator"):
                    self.terminate_emulator_and_bot(data.get("message", "Trial expired"))
                elif "remaining_seconds" in data:
                    self.remaining_seconds = int(data["remaining_seconds"])
                    self.session_start_time = time.time()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                try:
                    err_data = json.loads(e.read().decode("utf-8"))
                    if err_data.get("close_emulator"):
                        self.terminate_emulator_and_bot(err_data.get("message", "Trial expired on server"))
                except Exception:
                    self.terminate_emulator_and_bot("Server rejected session heartbeat")
        except Exception:
            pass

    def invalidate_session(self, reason: str = "Session invalidated") -> None:
        """Invalidate session, trigger file cleanup, and lock out."""
        if self.lockout_triggered:
            return
        self.lockout_triggered = True
        self.is_authorized = False
        self.session_token = None
        logger.critical(f"[AdbGuard] SECURITY LOCKOUT TRIGGERED: {reason}")
        cleanup_runtime()

    def verify_call(self, call_type: str = "device_action") -> bool:
        """
        Verify that user, HWID, and trial expiration are valid for this ADB call.
        Executes on EVERY device call.
        """
        if self.lockout_triggered or not self.is_authorized:
            raise SecurityLockoutException("AdbGuard: Device access blocked. No active authenticated session.")

        if not self.session_token:
            self.invalidate_session("Missing session token during device interaction.")
            raise SecurityLockoutException("AdbGuard: Session token missing.")

        # Check local 2-hour timer
        if self.is_free_trial:
            elapsed = time.time() - self.session_start_time
            if self.remaining_seconds - elapsed <= 0:
                self.terminate_emulator_and_bot("2-Hour Free Trial limit reached during attack execution.")
                raise SecurityLockoutException("2-Hour Free Trial expired.")

        # Local HWID check
        from license_manager import get_hwid
        current_hwid = get_hwid()
        if self.hwid and current_hwid and self.hwid.lower() != current_hwid.lower():
            self.invalidate_session(f"HWID mismatch: expected {self.hwid}, got {current_hwid}")
            raise SecurityLockoutException("AdbGuard: Hardware ID mismatch detected.")

        self._call_counter += 1

        # Periodic synchronous verification with the server
        if self._call_counter >= self._sync_check_interval:
            self._call_counter = 0
            if not self._verify_with_server(call_type):
                self.invalidate_session("Server rejected device call authorization.")
                raise SecurityLockoutException("AdbGuard: Server denied authorization for device call.")

        return True

    def _verify_with_server(self, call_type: str) -> bool:
        """Send a lightweight verification query to the server."""
        try:
            url = f"{self.server_url}/api/auth/verify-call"
            nonce = secrets.token_hex(8)
            payload = json.dumps({
                "token": self.session_token,
                "hwid": self.hwid,
                "call_type": call_type,
                "nonce": nonce
            }).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.session_token}",
                    "User-Agent": "ClashBotAI/2.1.5"
                }
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("close_emulator"):
                    self.terminate_emulator_and_bot(data.get("message", "Trial expired on server"))
                    return False
                if data.get("status") == "allowed":
                    self.tier = data.get("tier", self.tier)
                    return True
                return False
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                try:
                    err_data = json.loads(e.read().decode("utf-8"))
                    if err_data.get("close_emulator"):
                        self.terminate_emulator_and_bot(err_data.get("message", "Trial expired"))
                        return False
                except Exception:
                    pass
            return False
        except Exception as e:
            if time.time() - self.last_heartbeat_time < 90:
                return True
            logger.warning(f"[AdbGuard] Server verification failed: {e}")
            return False

    def guard_call(self, func: Callable, *args, **kwargs) -> Any:
        """Wrap and execute an ADB function with verification check."""
        call_name = getattr(func, "__name__", "adb_call")
        self.verify_call(call_type=call_name)
        return func(*args, **kwargs)


# Global singleton instance
_guard = AdbGuard()

def get_adb_guard() -> AdbGuard:
    return _guard

def guard_adb_call(func: Callable, *args, **kwargs) -> Any:
    return _guard.guard_call(func, *args, **kwargs)
