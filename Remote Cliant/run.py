# -*- coding: utf-8 -*-
"""
ClashBot AI - Remote Client Launcher
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar

Launches the Remote Client UI.
Automatically launches Host/run.py if not already running,
so both the Host UI and the Remote Client UI open simultaneously side-by-side
allowing live visual verification of all remote clicks and actions.
"""

import os
import sys
import time
import socket
import subprocess
from typing import Optional

# Setup directories
client_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(client_dir)
host_src_dir = os.path.join(project_root, "Host", "src")
host_dir = os.path.join(project_root, "Host")

if host_src_dir not in sys.path:
    sys.path.insert(0, host_src_dir)
if client_dir not in sys.path:
    sys.path.insert(0, client_dir)

# Ensure current working directory is host_src_dir for asset and module loading
os.chdir(host_src_dir)

# Enforce client mode so ui2client server is not started locally
os.environ["CLASHBOT_CLIENT_MODE"] = "1"

from PySide6.QtWidgets import QApplication
from client_bridge import ClientBridge, DEFAULT_HOST, DEFAULT_PORT
from remote_ui import RemoteMainWindow


def is_host_running(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> bool:
    """Check if Host UI ui2client bridge server is actively listening."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.6)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def launch_host_engine() -> Optional[subprocess.Popen]:
    """Launch Host/run.py in a background process if not already running."""
    host_run_script = os.path.join(host_dir, "run.py")

    if not os.path.exists(host_run_script):
        sys.__stdout__.write(f"[!] Warning: Host run.py not found at {host_run_script}\n")
        sys.__stdout__.flush()
        return None

    sys.__stdout__.write(f"[+] Launching Main Host UI engine: {host_run_script}\n")
    sys.__stdout__.flush()
    proc = subprocess.Popen(
        [sys.executable, host_run_script],
        cwd=host_dir,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    return proc


def main():
    real_out = sys.__stdout__
    real_out.write("=" * 65 + "\n")
    real_out.write("  ClashBot AI - Remote Client Launcher\n")
    real_out.write("  Author: Aradhye Tushar (https://github.com/AradhyeTushar)\n")
    real_out.write("=" * 65 + "\n")
    real_out.flush()

    host_proc = None
    if not is_host_running():
        real_out.write("[*] Host engine is not running. Launching Host UI (Host/run.py)...\n")
        real_out.flush()
        host_proc = launch_host_engine()
        # Give Host UI a moment to initialize its window and server
        real_out.write("[*] Waiting for Host UI engine to initialize...\n")
        real_out.flush()
        for _ in range(30):
            if is_host_running():
                real_out.write("[+] Host UI engine bridge is online!\n")
                real_out.flush()
                break
            time.sleep(0.4)
    else:
        real_out.write("[+] Detected existing running Host UI engine.\n")
        real_out.flush()

    # Initialize Qt Application
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    app.setApplicationName("ClashBot AI Remote Client")

    # Start Client Bridge
    bridge = ClientBridge(DEFAULT_HOST, DEFAULT_PORT)
    bridge.start()

    # Create and show Remote UI window
    window = RemoteMainWindow(bridge)

    # Position Remote UI window slightly offset so Host UI and Remote UI are both visible side-by-side
    screen_geo = app.primaryScreen().availableGeometry()
    win_w = 1000
    win_h = 650
    if screen_geo.width() >= 1900:
        target_x = screen_geo.x() + (screen_geo.width() - win_w) - 30
        target_y = screen_geo.y() + 50
    else:
        target_x = screen_geo.x() + 40
        target_y = screen_geo.y() + 40
    window.setGeometry(target_x, target_y, win_w, win_h)
    window.show()

    real_out.write("[+] Remote Client UI launched successfully.\n")
    real_out.write("[+] Both Host UI and Remote UI are active on desktop.\n")
    real_out.write("[+] Ready for remote clicks and synchronization!\n")
    real_out.flush()

    ret = app.exec()
    bridge.stop()
    sys.exit(ret)


if __name__ == "__main__":
    main()
