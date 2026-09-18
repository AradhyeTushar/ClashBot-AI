# -*- coding: utf-8 -*-
"""
ClashBot AI - Android Emulator Worker & Lifecycle Controller
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar. All rights reserved.

Comprehensive Android Emulator management for ClashBot AI:
- Supported Emulators:
    * MuMu Player 12 / MuMu Player Pro (nx_main / MuMuManager)
    * BlueStacks 5 / BlueStacks 10 (HD-Player / HD-Adb)
    * LDPlayer 9 / LDPlayer 4 (ldconsole / dnplayer)
    * Nox Player (Nox / nox_adb)
    * MEmu Play (MEmuConsole / MEmu)
    * Custom / Other Android devices (generic ADB IP/Port)
- Capabilities:
    * Auto-detecting installed emulators from Windows Registry and common filesystem paths.
    * Parsing multi-instance configurations and resolving accurate ADB listening ports.
    * Launching, monitoring boot completion, restarting, and terminating emulator instances.
    * Proactive health checks and crash recovery.
"""

import os
import sys
import time
import json
import socket
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

try:
    import winreg
except ImportError:
    winreg = None

logger = logging.getLogger("ClashBotAI.EmulatorWorker")

_emulator_worker_instance: Optional["EmulatorWorker"] = None


class EmulatorWorker:
    """
    Manages Android emulator installation discovery, instance detection,
    and process lifecycle (start, stop, reboot, port resolution).
    """

    DEFAULT_PORTS = {
        "mumu": 16384,         # Base port: 16384, 16416, 16448... (+32)
        "bluestacks": 5555,    # Base port: 5555, 5556, 5557, 5558... (+1 or bst.conf)
        "ldplayer": 5554,      # Base port: 5554, 5556, 5558... (+2)
        "nox": 62001,          # Base port: 62001, 62025, 62026...
        "memu": 21503,         # Base port: 21503, 21513, 21523... (+10)
        "other": 5555
    }

    def __init__(self, config_path: Optional[str] = None):
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.config_path = config_path or str(self.project_root / "Host" / "src" / "profiles" / "config.json")
        if not os.path.exists(self.config_path):
            alt_cfg = str(self.project_root / "src" / "profiles" / "config.json")
            if os.path.exists(alt_cfg):
                self.config_path = alt_cfg

        self._installed_cache: Dict[str, Dict[str, Any]] = {}
        self._last_discovery_ts: float = 0.0

    # -------------------------------------------------------------
    # Configuration Helpers
    # -------------------------------------------------------------
    def load_config(self) -> Dict[str, Any]:
        """Load current bot configuration file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"[EmulatorWorker] Failed to load config: {e}")
        return {}

    def get_configured_emulator(self) -> Tuple[str, str, str, int]:
        """
        Returns (emulator_type, instance_id, host, port) from config.json.
        """
        cfg = self.load_config()
        emu_type = str(cfg.get("EMULATOR_SELECTION", "bluestacks")).lower().strip()
        instance = str(cfg.get("EMULATOR_INSTANCE", "0")).strip()
        host = str(cfg.get("EMULATOR_IP", "127.0.0.1")).strip() or "127.0.0.1"
        try:
            port = int(cfg.get("EMULATOR_PORT", self.DEFAULT_PORTS.get(emu_type, 5555)))
        except (ValueError, TypeError):
            port = self.DEFAULT_PORTS.get(emu_type, 5555)

        return emu_type, instance, host, port

    # -------------------------------------------------------------
    # Registry & Path Discovery
    # -------------------------------------------------------------
    def _read_registry_string(self, root_key, subkey: str, val_name: str) -> Optional[str]:
        """Safely read string value from Windows Registry."""
        if not winreg:
            return None
        for access in (winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0),
                       winreg.KEY_READ | getattr(winreg, "KEY_WOW64_32KEY", 0),
                       winreg.KEY_READ):
            try:
                with winreg.OpenKey(root_key, subkey, 0, access) as key:
                    val, reg_type = winreg.QueryValueEx(key, val_name)
                    if isinstance(val, str) and val.strip():
                        return val.strip()
            except Exception:
                continue
        return None

    def discover_installed_emulators(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Scan system for all supported Android emulators.
        Returns mapping: { "mumu": {...}, "bluestacks": {...}, "ldplayer": {...} }
        """
        now = time.time()
        if not force_refresh and self._installed_cache and (now - self._last_discovery_ts) < 30.0:
            return self._installed_cache

        discovered: Dict[str, Dict[str, Any]] = {}

        # 1. MuMu Player 12 / MuMu Player Pro
        mumu_candidates = [
            r"C:\Program Files\Netease\MuMuPlayer-12.0\nx_main\MuMuManager.exe",
            r"C:\Program Files\Netease\MuMuPlayer-12.0\shell\MuMuPlayer.exe",
            r"C:\Program Files\Netease\MuMuPlayer\nx_main\MuMuManager.exe",
            r"C:\Program Files (x86)\Netease\MuMuPlayer\nx_main\MuMuManager.exe",
            r"D:\Program Files\Netease\MuMuPlayer-12.0\nx_main\MuMuManager.exe",
            r"C:\MuMuPlayer\nx_main\MuMuManager.exe",
        ]
        # Check Registry
        reg_mumu = self._read_registry_string(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Netease\MuMuPlayer-12.0", "InstallDir") if winreg else None
        if reg_mumu:
            mumu_candidates.insert(0, os.path.join(reg_mumu, "nx_main", "MuMuManager.exe"))
            mumu_candidates.insert(1, os.path.join(reg_mumu, "shell", "MuMuPlayer.exe"))

        for cand in mumu_candidates:
            if os.path.isfile(cand):
                mgr_exe = cand if "MuMuManager.exe" in cand else os.path.join(os.path.dirname(cand), "..", "nx_main", "MuMuManager.exe")
                discovered["mumu"] = {
                    "name": "MuMu Player 12",
                    "type": "mumu",
                    "path": cand,
                    "manager_exe": mgr_exe if os.path.isfile(mgr_exe) else cand,
                    "base_port": 16384,
                    "installed": True
                }
                break

        # 2. BlueStacks 5 / 10 / NXT
        bs_candidates = [
            r"C:\Program Files\BlueStacks_nxt\HD-Player.exe",
            r"C:\Program Files (x86)\BlueStacks_nxt\HD-Player.exe",
            r"D:\Program Files\BlueStacks_nxt\HD-Player.exe",
            r"C:\Program Files\BlueStacks\HD-Player.exe",
        ]
        reg_bs = self._read_registry_string(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\BlueStacks_nxt", "InstallDir") if winreg else None
        if reg_bs:
            bs_candidates.insert(0, os.path.join(reg_bs, "HD-Player.exe"))

        for cand in bs_candidates:
            if os.path.isfile(cand):
                install_dir = os.path.dirname(cand)
                conf_file = r"C:\ProgramData\BlueStacks_nxt\bluestacks.conf"
                discovered["bluestacks"] = {
                    "name": "BlueStacks 5",
                    "type": "bluestacks",
                    "path": cand,
                    "install_dir": install_dir,
                    "config_file": conf_file if os.path.isfile(conf_file) else None,
                    "base_port": 5555,
                    "installed": True
                }
                break

        # 3. LDPlayer 9 / 4
        ld_candidates = [
            r"C:\LDPlayer\LDPlayer9\ldconsole.exe",
            r"C:\LDPlayer\LDPlayer9\dnplayer.exe",
            r"D:\LDPlayer\LDPlayer9\ldconsole.exe",
            r"C:\LDPlayer\LDPlayer4.0\ldconsole.exe",
            r"C:\Program Files\LDPlayer9\ldconsole.exe",
            r"C:\Program Files\leidian\LDPlayer9\ldconsole.exe"
        ]
        reg_ld = self._read_registry_string(winreg.HKEY_CURRENT_USER, r"SOFTWARE\XuanZhi\LDPlayer9", "InstallDir") if winreg else None
        if reg_ld:
            ld_candidates.insert(0, os.path.join(reg_ld, "ldconsole.exe"))
            ld_candidates.insert(1, os.path.join(reg_ld, "dnplayer.exe"))

        for cand in ld_candidates:
            if os.path.isfile(cand):
                dir_p = os.path.dirname(cand)
                console = os.path.join(dir_p, "ldconsole.exe")
                discovered["ldplayer"] = {
                    "name": "LDPlayer 9",
                    "type": "ldplayer",
                    "path": cand,
                    "console_exe": console if os.path.isfile(console) else cand,
                    "base_port": 5554,
                    "installed": True
                }
                break

        # 4. Nox Player
        nox_candidates = [
            r"C:\Program Files\Nox\bin\Nox.exe",
            r"C:\Program Files (x86)\Nox\bin\Nox.exe",
            r"D:\Program Files\Nox\bin\Nox.exe"
        ]
        for cand in nox_candidates:
            if os.path.isfile(cand):
                discovered["nox"] = {
                    "name": "Nox Player",
                    "type": "nox",
                    "path": cand,
                    "base_port": 62001,
                    "installed": True
                }
                break

        # 5. MEmu Play
        memu_candidates = [
            r"C:\Program Files\Microvirt\MEmu\MEmu.exe",
            r"D:\Program Files\Microvirt\MEmu\MEmu.exe"
        ]
        for cand in memu_candidates:
            if os.path.isfile(cand):
                discovered["memu"] = {
                    "name": "MEmu Play",
                    "type": "memu",
                    "path": cand,
                    "base_port": 21503,
                    "installed": True
                }
                break

        self._installed_cache = discovered
        self._last_discovery_ts = now
        return discovered

    # -------------------------------------------------------------
    # Instance & Port Resolution
    # -------------------------------------------------------------
    def resolve_instance_port(self, emulator_type: str, instance_id: str = "0") -> int:
        """
        Calculate or parse the exact ADB listening port for a given emulator instance.
        """
        emu_type = emulator_type.lower().strip()
        idx = 0
        try:
            # Handle numeric, "Pie64", "Nougat32", "Instance 0" etc.
            if instance_id.isdigit():
                idx = int(instance_id)
            else:
                digits = "".join([c for c in instance_id if c.isdigit()])
                if digits:
                    idx = int(digits)
        except Exception:
            idx = 0

        # MuMu Player: 16384 for index 0, 16416 for 1, 16448 for 2 (+32)
        if emu_type == "mumu":
            return 16384 + (idx * 32)

        # LDPlayer: 5554 for index 0, 5556 for 1, 5558 for 2 (+2)
        elif emu_type == "ldplayer":
            return 5554 + (idx * 2)

        # BlueStacks: Inspect bluestacks.conf if available
        elif emu_type == "bluestacks":
            conf_path = r"C:\ProgramData\BlueStacks_nxt\bluestacks.conf"
            if os.path.exists(conf_path):
                try:
                    target_tag = f"bst.instance.{instance_id}.status.adb_port=" if instance_id and not instance_id.isdigit() else ""
                    fallback_tag = "status.adb_port="
                    with open(conf_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line = line.strip()
                            if target_tag and target_tag in line:
                                port_val = line.split("=")[-1].strip().strip('"')
                                if port_val.isdigit():
                                    return int(port_val)
                            elif fallback_tag in line and idx == 0:
                                port_val = line.split("=")[-1].strip().strip('"')
                                if port_val.isdigit():
                                    return int(port_val)
                except Exception:
                    pass
            return 5555 + idx

        # Nox: 62001, 62025...
        elif emu_type == "nox":
            return 62001 if idx == 0 else 62025 + (idx - 1)

        # MEmu: 21503, 21513... (+10)
        elif emu_type == "memu":
            return 21503 + (idx * 10)

        return self.DEFAULT_PORTS.get(emu_type, 5555)

    def is_port_open(self, host: str = "127.0.0.1", port: int = 5555, timeout_sec: float = 0.5) -> bool:
        """Check if an ADB TCP port is actively listening and responsive."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout_sec)
        try:
            s.connect((host, port))
            s.close()
            return True
        except Exception:
            return False

    # -------------------------------------------------------------
    # Process & Instance Lifecycle
    # -------------------------------------------------------------
    def is_instance_running(self, emulator_type: Optional[str] = None, instance_id: str = "0") -> bool:
        """Check if the specified emulator instance is running and its ADB port is open."""
        emu_type = emulator_type or self.get_configured_emulator()[0]
        port = self.resolve_instance_port(emu_type, instance_id)
        return self.is_port_open("127.0.0.1", port)

    def launch_emulator(
        self,
        emulator_type: Optional[str] = None,
        instance_id: Optional[str] = None,
        wait_ready: bool = True,
        timeout_sec: float = 40.0
    ) -> bool:
        """
        Launch the configured emulator instance.
        If wait_ready=True, polls the ADB port until active or timed out.
        """
        cfg_emu, cfg_inst, _, _ = self.get_configured_emulator()
        emu_type = (emulator_type or cfg_emu).lower().strip()
        inst_id = str(instance_id if instance_id is not None else cfg_inst).strip() or "0"

        port = self.resolve_instance_port(emu_type, inst_id)

        # If already responsive, no need to launch again
        if self.is_port_open("127.0.0.1", port):
            logger.info(f"[EmulatorWorker] Emulator {emu_type}:{inst_id} is already running on port {port}.")
            return True

        discovered = self.discover_installed_emulators()
        emu_info = discovered.get(emu_type)
        if not emu_info or not emu_info.get("path"):
            logger.warning(f"[EmulatorWorker] Cannot launch: Emulator '{emu_type}' not found on system.")
            return False

        path = emu_info["path"]
        mgr_exe = emu_info.get("manager_exe") or emu_info.get("console_exe") or path

        idx = 0
        try:
            idx = int("".join([c for c in inst_id if c.isdigit()]) or 0)
        except Exception:
            idx = 0

        logger.info(f"[EmulatorWorker] Starting {emu_type} (Instance {inst_id}) via {mgr_exe}...")

        try:
            # 1. MuMu Manager Command
            if emu_type == "mumu":
                if os.path.basename(mgr_exe).lower() == "mumumanager.exe":
                    cmd = [mgr_exe, "api", "-v", str(idx), "launch_player"]
                else:
                    cmd = [mgr_exe]
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 2. LDPlayer Console Command
            elif emu_type == "ldplayer":
                if os.path.basename(mgr_exe).lower() == "ldconsole.exe":
                    cmd = [mgr_exe, "launch", "--index", str(idx)]
                else:
                    cmd = [mgr_exe, f"index={idx}"]
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 3. BlueStacks 5 Player
            elif emu_type == "bluestacks":
                bs_instance_arg = inst_id if not inst_id.isdigit() else f"Nougat32_{idx}" if idx > 0 else "Nougat32"
                cmd = [path, "--instance", bs_instance_arg]
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 4. Generic / Nox / MEmu
            else:
                subprocess.Popen([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        except Exception as e:
            logger.error(f"[EmulatorWorker] Launch command failed: {e}")
            return False

        if not wait_ready:
            return True

        # Wait for ADB port to come alive
        start_time = time.time()
        logger.info(f"[EmulatorWorker] Waiting for emulator on 127.0.0.1:{port} to boot...")
        while time.time() - start_time < timeout_sec:
            if self.is_port_open("127.0.0.1", port):
                logger.info(f"[+] [EmulatorWorker] Emulator {emu_type}:{inst_id} is online on port {port}!")
                return True
            time.sleep(1.0)

        logger.warning(f"[!] [EmulatorWorker] Timeout ({timeout_sec}s) waiting for emulator port {port}.")
        return False

    def restart_emulator(
        self,
        emulator_type: Optional[str] = None,
        instance_id: Optional[str] = None,
        timeout_sec: float = 45.0
    ) -> bool:
        """Restart the configured or specified emulator instance."""
        logger.info(f"[EmulatorWorker] Restarting emulator {emulator_type}:{instance_id}...")
        self.close_emulator(emulator_type, instance_id)
        time.sleep(2.0)
        return self.launch_emulator(emulator_type, instance_id, wait_ready=True, timeout_sec=timeout_sec)

    def close_emulator(self, emulator_type: Optional[str] = None, instance_id: Optional[str] = None) -> bool:
        """Gracefully close or terminate the emulator instance."""
        cfg_emu, cfg_inst, _, _ = self.get_configured_emulator()
        emu_type = (emulator_type or cfg_emu).lower().strip()
        inst_id = str(instance_id if instance_id is not None else cfg_inst).strip() or "0"

        discovered = self.discover_installed_emulators()
        emu_info = discovered.get(emu_type)
        if not emu_info:
            return False

        mgr_exe = emu_info.get("manager_exe") or emu_info.get("console_exe")
        try:
            if emu_type == "mumu" and mgr_exe and os.path.basename(mgr_exe).lower() == "mumumanager.exe":
                subprocess.run(
                    [mgr_exe, "api", "-v", inst_id, "close_player"],
                    timeout=8,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                return True
            elif emu_type == "ldplayer" and mgr_exe and os.path.basename(mgr_exe).lower() == "ldconsole.exe":
                subprocess.run(
                    [mgr_exe, "quit", "--index", inst_id],
                    timeout=8,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                return True
            elif emu_type == "bluestacks" and mgr_exe:
                # Terminate BlueStacks player processes for instance
                for p in ["HD-Player.exe", "BlueStacksServices.exe"]:
                    subprocess.run(
                        ["taskkill", "/F", "/IM", p],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    )
                return True
        except Exception as e:
            logger.warning(f"[EmulatorWorker] Error during close_emulator: {e}")

        return False

    def auto_configure_installed_emulator(self) -> Tuple[str, int]:
        """
        Verify current config.json EMULATOR_SELECTION.
        If current selection is not installed but another emulator is found (e.g. MuMu),
        update config.json automatically to point to the installed emulator and correct port.
        """
        cfg = self.load_config()
        current_emu = str(cfg.get("EMULATOR_SELECTION", "")).lower().strip()
        discovered = self.discover_installed_emulators()

        # If current is valid and installed, keep it
        if current_emu in discovered and discovered[current_emu].get("installed"):
            resolved_port = self.resolve_instance_port(current_emu, str(cfg.get("EMULATOR_INSTANCE", "0")))
            return current_emu, resolved_port

        # Otherwise pick first installed emulator (prefer mumu > bluestacks > ldplayer)
        for preferred in ("mumu", "bluestacks", "ldplayer", "nox", "memu"):
            if preferred in discovered and discovered[preferred].get("installed"):
                info = discovered[preferred]
                target_port = info.get("base_port", self.DEFAULT_PORTS.get(preferred, 5555))
                cfg["EMULATOR_SELECTION"] = preferred
                cfg["EMULATOR_INSTANCE"] = "0"
                cfg["EMULATOR_IP"] = "127.0.0.1"
                cfg["EMULATOR_PORT"] = str(target_port)

                # Ensure path is recorded
                if "EMULATOR_INSTALL_PATHS" not in cfg or not isinstance(cfg["EMULATOR_INSTALL_PATHS"], dict):
                    cfg["EMULATOR_INSTALL_PATHS"] = {}
                cfg["EMULATOR_INSTALL_PATHS"][preferred] = info.get("path", "")

                try:
                    if os.path.exists(self.config_path):
                        with open(self.config_path, "w", encoding="utf-8") as f:
                            json.dump(cfg, f, indent=2)
                        logger.info(f"[EmulatorWorker] Auto-configured config.json to installed emulator: {preferred} (Port {target_port})")
                except Exception as e:
                    logger.warning(f"[EmulatorWorker] Could not write config.json: {e}")

                return preferred, target_port

        return current_emu or "mumu", 16384


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


class EmulatorWorkerThread(QThread):
    """
    Asynchronous Qt background worker managing emulator bootstrapping,
    boot waiting, and status reporting without freezing the GUI.
    """
    status_changed = Signal(str)
    boot_progress = Signal(int, str)
    emulator_ready = Signal(str, int)  # (emu_type, port)
    emulator_stopped = Signal(str)
    error = Signal(str)

    def __init__(
        self,
        action: str = "launch",
        emulator_type: Optional[str] = None,
        instance_id: Optional[str] = None,
        timeout_sec: float = 45.0,
        parent=None
    ):
        super().__init__(parent)
        self.action = action  # "launch", "restart", "close"
        self.emulator_type = emulator_type
        self.instance_id = instance_id
        self.timeout_sec = timeout_sec
        self.worker = get_emulator_worker()

    def run(self):
        """Execute lifecycle operation in background thread."""
        try:
            emu_type = self.emulator_type
            inst_id = self.instance_id
            if not emu_type:
                emu_type, inst_id, _, _ = self.worker.get_configured_emulator()

            if self.action == "close":
                self.status_changed.emit(f"Closing emulator {emu_type}...")
                ok = self.worker.close_emulator(emu_type, inst_id)
                self.emulator_stopped.emit(emu_type)
                self.status_changed.emit("Emulator closed." if ok else "Emulator shutdown requested.")
                return

            if self.action == "restart":
                self.status_changed.emit(f"Restarting emulator {emu_type}...")
                self.worker.close_emulator(emu_type, inst_id)
                time.sleep(2.0)

            # Launch & monitor boot
            self.status_changed.emit(f"Launching {emu_type} (Instance {inst_id})...")
            port = self.worker.resolve_instance_port(emu_type, inst_id)

            # Fire launch
            launched = self.worker.launch_emulator(
                emu_type,
                inst_id,
                wait_ready=False
            )
            if not launched:
                self.error.emit(f"Failed to execute launch command for {emu_type}")
                return

            # Wait for port online with periodic progress updates
            start = time.time()
            while time.time() - start < self.timeout_sec:
                elapsed = int(time.time() - start)
                pct = min(95, int((elapsed / self.timeout_sec) * 100))
                self.boot_progress.emit(pct, f"Waiting for emulator to boot ({elapsed}s)...")

                if self.worker.is_port_open("127.0.0.1", port):
                    self.boot_progress.emit(100, "Emulator is online and responsive.")
                    self.status_changed.emit(f"Connected to {emu_type} on port {port}.")
                    self.emulator_ready.emit(emu_type, port)
                    return

                time.sleep(1.0)

            self.error.emit(f"Timed out after {int(self.timeout_sec)}s waiting for emulator port {port}")

        except Exception as e:
            logger.error(f"[EmulatorWorkerThread] Error in run: {e}")
            self.error.emit(str(e))


def get_emulator_worker(config_path: Optional[str] = None) -> EmulatorWorker:
    """Singleton getter for EmulatorWorker."""
    global _emulator_worker_instance
    if _emulator_worker_instance is None:
        _emulator_worker_instance = EmulatorWorker(config_path)
    return _emulator_worker_instance

