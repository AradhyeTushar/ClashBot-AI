import os
import sys

client_dir = r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)\Remote Cliant"
host_src = r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)\Host\src"
if host_src not in sys.path:
    sys.path.insert(0, host_src)
if client_dir not in sys.path:
    sys.path.insert(0, client_dir)

os.environ["CLASHBOT_CLIENT_MODE"] = "1"
os.chdir(client_dir)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

app = QApplication.instance() or QApplication(sys.argv)

from remote_ui import RemoteMainWindow
from client_bridge import ClientBridge

bridge = ClientBridge()
win = RemoteMainWindow(bridge=bridge)
win.resize(1200, 780)
win.show()

# Simulate full state received with MuMu Player 16384
mock_state = {
    "type": "full_state",
    "ready": True,
    "bot_status": "Ready",
    "configured_emulator": "mumu",
    "configured_port": 16384,
    "adb_connected": True,
    "adb_target": "127.0.0.1:16384",
    "labels": {"status": "Ready"},
    "checkboxes": {},
    "comboboxes": {},
    "spinboxes": {}
}
win._on_bridge_full_state(mock_state)

def save_and_quit():
    pixmap = win.grab()
    out_path = r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)\scratch\remote_ui_with_workers.png"
    pixmap.save(out_path, "PNG")
    print(f"[+] Saved screenshot to: {out_path}")
    app.quit()

QTimer.singleShot(500, save_and_quit)
app.exec()
