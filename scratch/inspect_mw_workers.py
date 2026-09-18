import sys
import os
sys.path.insert(0, r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)\Host\src")
os.chdir(r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)\Host\src")
os.environ["CLASHBOT_CLIENT_MODE"] = "1"

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from ui import main_window
mw = main_window.MainWindow()

out = []
if hasattr(mw, 'emulator_select'):
    items = [mw.emulator_select.itemText(i) for i in range(mw.emulator_select.count())]
    out.append(f"emulator_select items: {items}")
    out.append(f"currentText: {mw.emulator_select.currentText()}")
if hasattr(mw, 'emulator_instance_select'):
    items = [mw.emulator_instance_select.itemText(i) for i in range(mw.emulator_instance_select.count())]
    out.append(f"emulator_instance_select items: {items}")
    out.append(f"currentText: {mw.emulator_instance_select.currentText()}")
if hasattr(mw, 'emulator_install_path_input'):
    out.append(f"emulator_install_path_input: {mw.emulator_install_path_input.text()}")

with open(r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)\scratch\inspect_mw_workers_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
