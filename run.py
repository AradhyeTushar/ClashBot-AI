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
    from ui import gui
    sys.exit(gui.run())
