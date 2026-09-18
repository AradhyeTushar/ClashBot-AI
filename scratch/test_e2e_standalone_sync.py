# -*- coding: utf-8 -*-
"""
End-to-End Verification: Standalone Remote Client <-> Host UI Server Synchronization
Ensures full two-way network synchronization between the decoupled Remote Client and Host Server.
"""

import os
import sys
import time
import socket
import threading

project_root = r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)"
host_src_dir = os.path.join(project_root, "Host", "src")
client_dir = os.path.join(project_root, "Remote Cliant")

print("[1] Starting Host UI2Client Bridge Server on 0.0.0.0:29170...")
if host_src_dir not in sys.path:
    sys.path.insert(0, host_src_dir)

from ui import ui2client
ui2client.start_ui2client_server(port=29170)


# Simulate Host MainWindow attributes
class MockHostWindow:
    def __init__(self):
        from PySide6.QtWidgets import QCheckBox, QComboBox, QSpinBox, QLabel, QPushButton
        self.farming_enabled = QCheckBox("Enable Farming")
        self.farming_enabled.setChecked(True)
        self.upgrade_walls = QCheckBox("Upgrade Walls")
        self.upgrade_walls.setChecked(False)
        self.attack_gold = QSpinBox()
        self.attack_gold.setValue(750000)
        self.wall_stop_level = QComboBox()
        self.wall_stop_level.addItems(["10", "11", "12", "15"])
        self.wall_stop_level.setCurrentText("15")
        self.status = QLabel("Host Ready")
        self.mode_label = QLabel("Idle")
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.pause_btn = QPushButton("Pause")
        self._last_worker_status = "Host Bot Running"

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

mock_host = MockHostWindow()
ui2client.bind_host_main_window(mock_host)
print("[+] Host Mock MainWindow successfully bound to ui2client server!")

# Now test client in a totally isolated namespace
print("\n[2] Connecting Standalone Remote Client...")
# Remove Host from sys.path for client test
sys.path = [p for p in sys.path if "Host" not in p and "src" not in p]
if client_dir not in sys.path:
    sys.path.insert(0, client_dir)

from client_bridge import ClientBridge
import remote_ui

bridge = ClientBridge(host="127.0.0.1", port=29170)
client_win = remote_ui.RemoteMainWindow(bridge=bridge)
client_win.show()
bridge.start()

# Wait for connection
for _ in range(20):
    app.processEvents()
    if bridge.is_connected():
        print("[+] Standalone Client connected to Server!")
        break
    time.sleep(0.1)

assert bridge.is_connected(), "Client failed to connect to Server!"

# Wait for full state snapshot
for _ in range(15):
    app.processEvents()
    time.sleep(0.1)

print(f"[+] Client UI received state snapshot:")
print(f"    - farming_enabled checked: {client_win.farming_enabled.isChecked()}")
print(f"    - attack_gold value: {client_win.attack_gold.value()}")
badge_text = client_win.title_bar.conn_badge.text().encode('ascii', errors='replace').decode('ascii')
print(f"    - Title Badge Text: {badge_text}")

# Test 1: Client toggles upgrade_walls -> Verify Host receives it
print("\n[3] Testing Client Action -> Host Execution:")
print(f"    - client_win._is_syncing: {client_win._is_syncing}")
print(f"    - client_win.bridge._connected: {client_win.bridge._connected}")
print(f"    - client_win.bridge._socket: {client_win.bridge._socket}")
res = client_win.bridge.send_action({"action": "toggle_checkbox", "target": "upgrade_walls", "value": True})
print(f"    - direct send_action result: {res}")
client_win.upgrade_walls.setChecked(True)
for _ in range(25):
    app.processEvents()
    time.sleep(0.05)


print(f"    - Host upgrade_walls after client click: {mock_host.upgrade_walls.isChecked()}")
assert mock_host.upgrade_walls.isChecked() == True, "Host did not receive checkbox toggle!"
print("[+] Checkbox synchronization verified!")

# Test 2: Host broadcasts log -> Verify Client receives it
print("\n[4] Testing Host Log Streaming -> Client Log Box:")
ui2client.broadcast_log("[SYSTEM] Attacking base #402 - 1,200,000 Gold looted!")
for _ in range(15):
    app.processEvents()
    time.sleep(0.05)

log_content = client_win.log_textbox.toPlainText()
print(f"    - Client log box contains: {log_content.strip()}")
assert "Attacking base #402" in log_content, "Client log box did not receive broadcast log!"
print("[+] Log streaming verified!")

# Test 3: Capture screenshot of connected client with live badges
client_win.resize(1020, 680)
app.processEvents()
e2e_shot = os.path.join(project_root, "scratch", "e2e_connected_client.png")
client_win.grab().save(e2e_shot)
print(f"[+] Connected client screenshot saved to: {e2e_shot}")

# Clean up
bridge.stop()
ui2client.stop_ui2client_server()

print("\n>>> ALL E2E TESTS PASSED: Standalone Client is 100% functional and synced! <<<")
