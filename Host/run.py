# -*- coding: utf-8 -*-
"""
ClashBot AI - Application Launcher
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar
"""
import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(project_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

os.chdir(src_dir)

if __name__ == "__main__":
    print("[+] Starting ClashBot AI Engine...")
    try:
        from ui.branding_patch import apply_branding_patches
        apply_branding_patches()
    except Exception as e:
        print(f"[!] Notice: Branding patch initialization: {e}")
    try:
        from ui.ui2client import start_ui2client_server
        start_ui2client_server()
    except Exception as e:
        print(f"[!] Notice: ui2client startup: {e}")
    from ui import gui
    gui.WINDOW_SETTINGS_APP = "ClashBotAI"
    gui.WINDOW_SETTINGS_ORG = "ClashBotAI"
    sys.exit(gui.run())
