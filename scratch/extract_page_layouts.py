import json

with open(r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)\scratch\full_ui_structure.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for page_name, pdata in data["pages"].items():
    print(f"\n==================== PAGE: {page_name} ====================")
    widgets = pdata.get("widgets", [])
    current_group = "Root"
    for w in widgets:
        cls = w.get("class")
        if cls == "QGroupBox":
            current_group = w.get("title") or "Unnamed Group"
            print(f"  [GROUP] {current_group}")
        elif cls in ("QCheckBox", "QComboBox", "QSpinBox", "QPushButton", "QLineEdit"):
            txt = w.get("text") or w.get("currentText") or w.get("value") or ""
            name = w.get("name") or ""
            print(f"    - {cls:12} | name='{name}' | text='{txt}'")
