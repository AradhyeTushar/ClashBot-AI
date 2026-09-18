import json

with open(r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)\scratch\full_ui_structure.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("Nav buttons:", data["nav_buttons"])
print("\nPages and their main components:")
for page_name, pdata in data["pages"].items():
    print(f"\n--- Page: {page_name} ---")
    groups = []
    cbs = []
    spins = []
    combos = []
    for w in pdata.get("widgets", []):
        cls = w.get("class")
        if cls == "QGroupBox":
            groups.append(w.get("title", ""))
        elif cls == "QCheckBox":
            cbs.append(w.get("text", ""))
        elif cls == "QComboBox":
            combos.append(f"{w.get('name')}: {w.get('currentText')}")
        elif cls == "QSpinBox":
            spins.append(f"{w.get('name')}: {w.get('value')}")
    print(f"  Group boxes ({len(groups)}):", groups)
    print(f"  CheckBoxes ({len(cbs)}):", cbs[:6], f"... total {len(cbs)}")
    print(f"  SpinBoxes ({len(spins)}):", spins[:4])
    print(f"  ComboBoxes ({len(combos)}):", combos[:4])

print("\nAttributes list (sample 30):")
attrs = sorted(data["attributes"].keys())
for a in attrs[:30]:
    print(" ", a, "->", data["attributes"][a])
