import sys
import os
import json

sys.path.insert(0, r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)\Host\src")
os.chdir(r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)\Host\src")
os.environ["CLASHBOT_CLIENT_MODE"] = "1"

from PySide6.QtWidgets import (
    QApplication, QWidget, QCheckBox, QComboBox, QSpinBox,
    QPushButton, QToolButton, QLabel, QLineEdit, QGroupBox
)

app = QApplication.instance() or QApplication(sys.argv)
from ui import main_window
mw = main_window.MainWindow()

def inspect_widget(w):
    info = {
        "class": type(w).__name__,
        "name": w.objectName(),
    }
    if hasattr(w, "text") and callable(w.text):
        try: info["text"] = w.text()
        except: pass
    if hasattr(w, "title") and callable(w.title):
        try: info["title"] = w.title()
        except: pass
    if isinstance(w, QComboBox):
        info["items"] = [w.itemText(i) for i in range(w.count())]
        info["currentText"] = w.currentText()
    if isinstance(w, QSpinBox):
        info["value"] = w.value()
        info["min"] = w.minimum()
        info["max"] = w.maximum()
    if isinstance(w, QCheckBox):
        info["checked"] = w.isChecked()
    return info

structure = {
    "nav_buttons": [b.text() for b in mw.buttons if isinstance(b, QPushButton)],
    "pages": {}
}

if hasattr(mw, "pages") and isinstance(mw.pages, dict):
    for pname, pwidget in mw.pages.items():
        children = []
        for child in pwidget.findChildren(QWidget):
            # Only direct or significant functional widgets
            if isinstance(child, (QCheckBox, QComboBox, QSpinBox, QPushButton, QToolButton, QGroupBox, QLineEdit)):
                children.append(inspect_widget(child))
        structure["pages"][pname] = {
            "widget_count": len(children),
            "widgets": children
        }

# Attribute mapping (which attr maps to which widget)
attr_map = {}
for attr in dir(mw):
    if not attr.startswith("_"):
        try:
            val = getattr(mw, attr)
            if isinstance(val, (QCheckBox, QComboBox, QSpinBox, QPushButton, QLineEdit)):
                attr_map[attr] = {
                    "class": type(val).__name__,
                    "text": getattr(val, "text", lambda: "")() if hasattr(val, "text") else "",
                    "name": val.objectName()
                }
        except:
            pass

structure["attributes"] = attr_map

out_path = r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)\scratch\full_ui_structure.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(structure, f, indent=2)

sys.__stdout__.write(f"Dumped full UI structure to {out_path} ({len(structure['pages'])} pages, {len(attr_map)} attributes)\n")
sys.__stdout__.flush()
