# -*- coding: utf-8 -*-
"""Capture screenshots of multiple tabs on the standalone Remote Client."""

import os
import sys

sys.path = [p for p in sys.path if "Host" not in p and "src" not in p]
client_dir = r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)\Remote Cliant"
if client_dir not in sys.path:
    sys.path.insert(0, client_dir)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
import remote_ui

app = QApplication.instance() or QApplication(sys.argv)
window = remote_ui.RemoteMainWindow()
window.show()
window.resize(1020, 680)

# 1. Capture General Tab
window.switch_page("General")
app.processEvents()
window.grab().save(r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)\scratch\standalone_general_tab.png")
print("[+] Captured General tab")

# 2. Capture Attack Army Tab
window.switch_page("Attack Army")
app.processEvents()
window.grab().save(r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)\scratch\standalone_attack_army.png")
print("[+] Captured Attack Army tab")

# 3. Capture Statistics Tab
window.switch_page("Statistics")
app.processEvents()
window.grab().save(r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)\scratch\standalone_stats_tab.png")
print("[+] Captured Statistics tab")

# 4. Capture Settings Drawer
window.switch_page("General")
window._toggle_settings_drawer()
app.processEvents()
window.grab().save(r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)\scratch\standalone_settings_drawer.png")
print("[+] Captured Settings Drawer")

print("All screenshots successfully captured!")
