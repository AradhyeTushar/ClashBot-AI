# -*- coding: utf-8 -*-
"""
ClashBot AI - Remote Client Launcher (100% Standalone)
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar. All rights reserved.

Launches the 100% Standalone Remote Client application.
Reads connection parameters from client_config.json and connects to the Host Server.
Zero Host dependencies or proprietary source code required.
"""

import os
import sys
import json
import time
import socket
import subprocess
from typing import Optional, Dict, Any

CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CLIENT_DIR, "client_config.json")

# Ensure Client directory is in sys.path and set as current working directory
if CLIENT_DIR not in sys.path:
    sys.path.insert(0, CLIENT_DIR)
os.chdir(CLIENT_DIR)

from PySide6.QtWidgets import QApplication
from client_bridge import ClientBridge, DEFAULT_HOST, DEFAULT_PORT, sanitize_host_and_port
from remote_ui import RemoteMainWindow


def load_client_config() -> Dict[str, Any]:
    """Load configuration from local client_config.json."""
    default_config = {
        "SERVER_HOST": "clashbot-ai.devtushar.uk",
        "SERVER_PORT": 443,
        "AUTO_CONNECT": True,
        "TIMEOUT_SECONDS": 5.0
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                default_config.update(loaded)
        except Exception as e:
            print(f"[!] Warning: Could not read {CONFIG_FILE}: {e}")
    else:
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2)
        except Exception:
            pass
    return default_config


def is_server_listening(host: str, port: int) -> bool:
    """Test if the ClashBot Server is listening on host:port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.6)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def maybe_launch_local_host(host_dir: str) -> Optional[subprocess.Popen]:
    """Optional convenience for local development PC only."""
    host_run_script = os.path.join(host_dir, "run.py")
    if not os.path.exists(host_run_script):
        return None

    print(f"[+] Developer Mode: Launching local Host engine ({host_run_script})...")
    proc = subprocess.Popen(
        [sys.executable, host_run_script],
        cwd=host_dir,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    return proc


def main():
    print("=" * 65)
    print("  ClashBot AI - Standalone Remote Client")
    print("  Author: Aradhye Tushar (https://github.com/AradhyeTushar)")
    print("  License: MIT License - Copyright (c) 2026 Aradhye Tushar")
    print("=" * 65)

    config = load_client_config()
    server_host, server_port = sanitize_host_and_port(
        config.get("SERVER_HOST", DEFAULT_HOST),
        config.get("SERVER_PORT", DEFAULT_PORT)
    )

    # Persist sanitized values back to client_config.json
    if config.get("SERVER_HOST") != server_host or config.get("SERVER_PORT") != server_port:
        config["SERVER_HOST"] = server_host
        config["SERVER_PORT"] = server_port
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass

    print(f"[*] Target Server: {server_host}:{server_port}")

    # For local development: if server_host is 127.0.0.1 and Host exists locally, offer auto-launch
    parent_dir = os.path.dirname(CLIENT_DIR)
    local_host_dir = os.path.join(parent_dir, "Host")
    if server_host in ("127.0.0.1", "localhost") and os.path.exists(local_host_dir):
        if not is_server_listening(server_host, server_port):
            print("[*] Local Host not detected. Launching local Host server...")
            maybe_launch_local_host(local_host_dir)
            for _ in range(25):
                if is_server_listening(server_host, server_port):
                    print("[+] Local Host server is online!")
                    break
                time.sleep(0.4)

    # Initialize Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("ClashBot AI Remote Client")

    # Initialize Client Bridge
    bridge = ClientBridge(host=server_host, port=server_port)

    # Initialize Local ADB Worker & Attach to Bridge
    try:
        from remote_adb_worker import RemoteAdbWorker
        adb_worker = RemoteAdbWorker()
        bridge.attach_adb_worker(adb_worker)
        # Attempt auto-detecting a local emulator
        adb_worker.auto_detect_device()
    except Exception as e:
        print(f"[!] Warning: Could not initialize RemoteAdbWorker: {e}")

    # Create & Display Window
    window = RemoteMainWindow(bridge=bridge)
    if hasattr(window, "server_ip_input") and window.server_ip_input:
        window.server_ip_input.setText(server_host)
    if hasattr(window, "server_port_input") and window.server_port_input:
        window.server_port_input.setText(str(server_port))
    window.show()

    # Start Bridge Connection in background
    if config.get("AUTO_CONNECT", True):
        bridge.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
