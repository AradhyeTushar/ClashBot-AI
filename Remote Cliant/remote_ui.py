# -*- coding: utf-8 -*-
"""
ClashBot AI - Remote Client User Interface (Exact Host UI Integration)
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar. All rights reserved.

Provides 100% exact UI parity with Host UI:
- All 11 navigation pages (General, Attack Army, Multi Village, Builder Base,
  Clan Capital, Upgrades/Research, XP Farming, Extra Modes, Bot Runtime, Statistics, Log).
- All 66 refined checkboxes with exact SVG checkmarks, glowing borders, and hover effects.
- Complete set of ComboBoxes, SpinBoxes, Groups, and Settings Drawer.
- Full two-way real-time click synchronization: any click on Remote Client
  instantly and visibly animates and executes on the Host UI window.
"""

import os
import sys
from typing import Optional, Dict, Any

# Ensure Host/src is in sys.path
client_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(client_dir)
host_src_dir = os.path.join(project_root, "Host", "src")
if host_src_dir not in sys.path:
    sys.path.insert(0, host_src_dir)

# Ensure client mode flag is set before any Host UI modules load
os.environ["CLASHBOT_CLIENT_MODE"] = "1"

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QLabel, QPushButton, QToolButton, QCheckBox,
    QComboBox, QSpinBox, QHBoxLayout, QWidget
)

from ui.branding_patch import apply_branding_patches
apply_branding_patches()

from ui import main_window
from client_bridge import ClientBridge


class RemoteMainWindow(main_window.MainWindow):
    """
    Exact Host UI instance operating in Remote Client mode.
    Every click, checkbox toggle, dropdown selection, and tab switch
    immediately synchronizes with the Host engine via the local IPC bridge.
    """

    def __init__(self, bridge: Optional[ClientBridge] = None, parent=None):
        self.bridge = bridge
        self._is_syncing = False
        self._hooked_client_widgets = set()

        # Initialize base MainWindow (builds the exact 11 pages and all controls)
        super().__init__()

        # Configure client-specific overrides and click synchronization
        self._setup_client_mode()
        self._wire_bridge()
        self._wire_client_controls()

    def _setup_client_mode(self) -> None:
        """Neutralize local bot execution and customize title bar."""
        # 1. Neutralize local worker so bot runs exclusively on Host
        if hasattr(self, "worker") and self.worker:
            self.worker.start = lambda *args, **kwargs: None

        # 2. Window Title
        self._update_window_title()

        # 3. Add Connection Badge & Focus Host Button to TitleBar
        if hasattr(self, "title_bar") and self.title_bar:
            layout = self.title_bar.layout()
            if layout:
                self.conn_badge = QLabel("• Connecting to Host...")
                self.conn_badge.setObjectName("RemoteConnBadge")
                self.conn_badge.setStyleSheet(
                    "color: #F59E0B; font-weight: bold; font-size: 11px; margin-left: 12px;"
                )

                self.focus_btn = QPushButton("🗖 Focus Host")
                self.focus_btn.setObjectName("FocusHostBtn")
                self.focus_btn.setToolTip("Bring Main Host UI Window to front")
                self.focus_btn.setCursor(Qt.PointingHandCursor)
                self.focus_btn.setStyleSheet("""
                    QPushButton#FocusHostBtn {
                        background-color: rgba(139, 85, 246, 0.22);
                        color: #DDD6FE;
                        border: 1px solid #8B55F6;
                        border-radius: 4px;
                        padding: 3px 10px;
                        font-size: 11px;
                        font-weight: bold;
                    }
                    QPushButton#FocusHostBtn:hover {
                        background-color: rgba(139, 85, 246, 0.45);
                        border: 1px solid #A78BFA;
                        color: #FFFFFF;
                    }
                    QPushButton#FocusHostBtn:pressed {
                        background-color: rgba(139, 85, 246, 0.6);
                    }
                """)
                if self.bridge:
                    self.focus_btn.clicked.connect(self.bridge.focus_host)

                # Insert right before minimize/close buttons
                count = layout.count()
                insert_idx = max(0, count - 2)
                layout.insertWidget(insert_idx, self.conn_badge)
                layout.insertWidget(insert_idx + 1, self.focus_btn)

        # 4. Refine Checkbox Styling Across Entire Window
        assets_dir = os.path.join(host_src_dir, "assets").replace("\\", "/")
        refined_cb_style = f"""
            QCheckBox {{
                color: #C9CCD6;
                font-weight: 400;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #3A4253;
                background-color: #1B1F2A;
            }}
            QCheckBox::indicator:hover {{
                border: 1.5px solid #8B55F6;
                background-color: #222636;
            }}
            QCheckBox::indicator:unchecked {{
                border: 1px solid #3A4253;
                background-color: #1B1F2A;
            }}
            QCheckBox::indicator:unchecked:hover {{
                border: 1.5px solid #8B55F6;
                background-color: #222636;
            }}
            QCheckBox::indicator:checked {{
                border: 1.5px solid #8B55F6;
                background-color: #1B1F2A;
                image: url("{assets_dir}/checkbox_check_purple.svg");
            }}
            QCheckBox::indicator:checked:hover {{
                border: 1.5px solid #9D6FF8;
                background-color: #24293A;
                image: url("{assets_dir}/checkbox_check_purple.svg");
            }}
            QCheckBox:disabled {{
                color: rgba(150, 158, 174, 0.5);
            }}
            QCheckBox::indicator:disabled {{
                border: 1px solid rgba(39, 45, 57, 0.6);
                background-color: rgba(23, 27, 34, 0.6);
            }}
            QCheckBox::indicator:checked:disabled {{
                image: url("{assets_dir}/checkbox_check_gray.svg");
            }}
        """
        if hasattr(self, "_central_content") and self._central_content:
            existing = self._central_content.styleSheet() or ""
            self._central_content.setStyleSheet(existing + "\n" + refined_cb_style)

        # Set PointingHandCursor on all checkboxes natively
        for cb in self.findChildren(QCheckBox):
            cb.setCursor(Qt.PointingHandCursor)

    def _update_window_title(self, *args, **kwargs) -> None:
        """Enforce Remote Client title across titlebar timer updates."""
        title_text = "ClashBot AI Pro v2.1.5 [REMOTE CLIENT]"
        self.setWindowTitle(title_text)
        if hasattr(self, "titlebar_title") and self.titlebar_title:
            try:
                self.titlebar_title.setText(title_text)
            except Exception:
                pass

    # -------------------------------------------------------------
    # Action Overrides (Route Actions to Host UI)
    # -------------------------------------------------------------
    def start_bot(self) -> None:
        """Route start action to Host UI."""
        if self.bridge:
            self.bridge.click_button("start")

    def pause_bot(self) -> None:
        """Route pause action to Host UI."""
        if self.bridge:
            self.bridge.click_button("pause")

    def stop_bot(self) -> None:
        """Route stop action to Host UI."""
        if self.bridge:
            self.bridge.click_button("stop")

    def _restart_adb_server(self) -> None:
        """Route ADB restart to Host UI."""
        if self.bridge:
            self.bridge.click_button("restart_adb")

    # -------------------------------------------------------------
    # Control Event Forwarding to Host
    # -------------------------------------------------------------
    def _wire_client_controls(self) -> None:
        """Wire all interactive controls to forward clicks to Host."""
        # 1. Nav Buttons (Page Switching)
        if hasattr(self, "buttons") and isinstance(self.buttons, list):
            for btn in self.buttons:
                if isinstance(btn, QPushButton):
                    page_name = btn.text().strip()
                    def _make_nav_handler(pname=page_name):
                        return lambda: self._on_client_nav_clicked(pname)
                    btn.clicked.connect(_make_nav_handler())

        # 2. Checkboxes, Comboboxes, and Spinboxes
        for attr in dir(self):
            if attr.startswith("_"):
                continue
            try:
                widget = getattr(self, attr, None)
                if isinstance(widget, QCheckBox) and attr not in self._hooked_client_widgets:
                    self._hooked_client_widgets.add(attr)
                    def _make_cb_handler(name=attr):
                        return lambda checked: self._on_client_checkbox_toggled(name, checked)
                    widget.toggled.connect(_make_cb_handler())

                elif isinstance(widget, QComboBox) and attr not in self._hooked_client_widgets:
                    self._hooked_client_widgets.add(attr)
                    def _make_cmb_handler(name=attr):
                        return lambda text: self._on_client_combobox_changed(name, text)
                    widget.currentTextChanged.connect(_make_cmb_handler())

                elif isinstance(widget, QSpinBox) and attr not in self._hooked_client_widgets:
                    self._hooked_client_widgets.add(attr)
                    def _make_sb_handler(name=attr):
                        return lambda val: self._on_client_spinbox_changed(name, val)
                    widget.valueChanged.connect(_make_sb_handler())

            except Exception:
                pass

        # 3. Settings Drawer Toggle
        if hasattr(self, "settings_toggle_btn") and self.settings_toggle_btn:
            self.settings_toggle_btn.clicked.connect(self._on_client_settings_toggle)

    def _on_client_nav_clicked(self, page_name: str) -> None:
        """User clicked a navigation page button in Remote Client."""
        if self._is_syncing:
            return
        if self.bridge:
            self.bridge.switch_page(page_name)

    def _on_client_checkbox_toggled(self, attr_name: str, checked: bool) -> None:
        """User toggled a checkbox in Remote Client."""
        if self._is_syncing:
            return
        if self.bridge:
            self.bridge.set_checkbox(attr_name, checked)

    def _on_client_combobox_changed(self, attr_name: str, text: str) -> None:
        """User changed a combobox in Remote Client."""
        if self._is_syncing:
            return
        if self.bridge:
            self.bridge.set_combobox(attr_name, text)

    def _on_client_spinbox_changed(self, attr_name: str, val: int) -> None:
        """User changed a spinbox in Remote Client."""
        if self._is_syncing:
            return
        if self.bridge:
            self.bridge.set_spinbox(attr_name, val)

    def _on_client_settings_toggle(self) -> None:
        """User clicked settings drawer toggle in Remote Client."""
        if self._is_syncing:
            return
        if self.bridge:
            self.bridge.click_button("settings")

    # -------------------------------------------------------------
    # Bridge Signal Handlers (Host Updates -> Remote Client)
    # -------------------------------------------------------------
    def _wire_bridge(self) -> None:
        """Connect bridge signals to update Remote Client state."""
        if not self.bridge:
            return
        self.bridge.connected.connect(self._on_bridge_connected)
        self.bridge.disconnected.connect(self._on_bridge_disconnected)
        self.bridge.log_received.connect(self._on_bridge_log)
        self.bridge.page_switched.connect(self._on_bridge_page_switched)
        self.bridge.widget_updated.connect(self._on_bridge_widget_updated)
        self.bridge.full_state_received.connect(self._on_bridge_full_state)
        self.bridge.host_ready.connect(self._on_bridge_host_ready)

    def _on_bridge_connected(self) -> None:
        """Bridge connected to Host UI socket."""
        if hasattr(self, "conn_badge") and self.conn_badge:
            self.conn_badge.setText("• Host Connected (Syncing...)")
            self.conn_badge.setStyleSheet(
                "color: #F59E0B; font-weight: bold; font-size: 11px; margin-left: 12px;"
            )
        if hasattr(self, "status") and self.status:
            self.status.setText("Host Connected (Syncing...)")

    def _on_bridge_host_ready(self, ready: bool) -> None:
        """Host MainWindow is ready and active."""
        if hasattr(self, "conn_badge") and self.conn_badge:
            if ready:
                self.conn_badge.setText("• Connected (127.0.0.1:29170)")
                self.conn_badge.setStyleSheet(
                    "color: #10B981; font-weight: bold; font-size: 11px; margin-left: 12px;"
                )
            else:
                self.conn_badge.setText("• Host Starting (Splash)...")
                self.conn_badge.setStyleSheet(
                    "color: #F59E0B; font-weight: bold; font-size: 11px; margin-left: 12px;"
                )
        if hasattr(self, "status") and self.status:
            self.status.setText("Host Ready" if ready else "Host Starting...")

    def _on_bridge_disconnected(self) -> None:
        """Bridge disconnected from Host UI."""
        if hasattr(self, "conn_badge") and self.conn_badge:
            self.conn_badge.setText("• Disconnected (Retrying...)")
            self.conn_badge.setStyleSheet(
                "color: #EF4444; font-weight: bold; font-size: 11px; margin-left: 12px;"
            )
        if hasattr(self, "status") and self.status:
            self.status.setText("Disconnected (Host Offline)")

    def _on_bridge_log(self, text: str) -> None:
        """Append log stream from Host UI to local log viewer."""
        if hasattr(self, "log_view") and self.log_view:
            try:
                self.log_view.append(text)
            except Exception:
                pass

    def _on_bridge_page_switched(self, page_name: str, page_idx: int) -> None:
        """Host switched page -> update Remote Client tab."""
        self._is_syncing = True
        try:
            if hasattr(self, "switch_page") and page_name:
                self.switch_page(page_name)
            elif hasattr(self, "stack") and self.stack:
                self.stack.setCurrentIndex(page_idx)
        finally:
            self._is_syncing = False

    def _on_bridge_widget_updated(self, w_type: str, name: str, val: Any) -> None:
        """Host updated a widget -> sync to local widget."""
        self._is_syncing = True
        try:
            widget = getattr(self, name, None)
            if widget:
                if w_type == "checkbox" and isinstance(widget, QCheckBox):
                    widget.setChecked(bool(val))
                elif w_type == "combobox" and isinstance(widget, QComboBox):
                    widget.setCurrentText(str(val))
                elif w_type == "spinbox" and isinstance(widget, QSpinBox):
                    widget.setValue(int(val))
        finally:
            self._is_syncing = False

    def _on_bridge_full_state(self, state: Dict[str, Any]) -> None:
        """Full state snapshot received from Host UI."""
        self._is_syncing = True
        try:
            # Checkboxes
            for k, v in state.get("checkboxes", {}).items():
                w = getattr(self, k, None)
                if isinstance(w, QCheckBox):
                    w.setChecked(bool(v))

            # Comboboxes
            for k, data in state.get("comboboxes", {}).items():
                w = getattr(self, k, None)
                if isinstance(w, QComboBox):
                    txt = data.get("currentText") if isinstance(data, dict) else str(data)
                    if txt:
                        w.setCurrentText(txt)

            # Spinboxes
            for k, v in state.get("spinboxes", {}).items():
                w = getattr(self, k, None)
                if isinstance(w, QSpinBox):
                    w.setValue(int(v))

            # Active Page
            cur_page = state.get("active_page")
            if cur_page and hasattr(self, "switch_page"):
                self.switch_page(cur_page)

            # Bot Status Label
            if hasattr(self, "status") and self.status:
                st = state.get("labels", {}).get("status") or state.get("bot_status")
                if st:
                    self.status.setText(st)

            # Live Emulator & ADB status in TitleBar connection badge
            adb_conn = state.get("adb_connected", False)
            emu_type = str(state.get("configured_emulator") or "mumu").capitalize()
            port = state.get("configured_port", 16384)
            if hasattr(self, "conn_badge") and self.conn_badge:
                if adb_conn:
                    self.conn_badge.setText(f"• Connected | {emu_type} ({port})")
                    self.conn_badge.setStyleSheet(
                        "color: #10B981; font-weight: bold; font-size: 11px; margin-left: 12px;"
                    )
                else:
                    self.conn_badge.setText(f"• Connected | {emu_type} ({port} Offline)")
                    self.conn_badge.setStyleSheet(
                        "color: #F59E0B; font-weight: bold; font-size: 11px; margin-left: 12px;"
                    )

        finally:
            self._is_syncing = False

