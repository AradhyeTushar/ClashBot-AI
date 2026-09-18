# -*- coding: utf-8 -*-
"""
ClashBot AI - 100% Standalone Remote Client User Interface
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar. All rights reserved.

This is a 100% standalone desktop client interface with ZERO proprietary Host imports.
It provides full UI parity with all 11 pages, 66 refined checkboxes, dropdowns,
spinboxes, and settings drawer, communicating exclusively over TCP sockets.
"""

import os
import sys
import json
from typing import Optional, Dict, Any, List

from PySide6.QtCore import Qt, QPoint, QSize, QTimer, Signal
from PySide6.QtGui import QIcon, QPixmap, QFont, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QToolButton, QCheckBox, QComboBox,
    QSpinBox, QLineEdit, QTextEdit, QStackedWidget, QGroupBox, QScrollArea,
    QSizePolicy, QButtonGroup
)

from client_bridge import ClientBridge
import styles

CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(CLIENT_DIR, "assets")


def get_asset(filename: str) -> str:
    """Get absolute path to local client asset."""
    return os.path.join(ASSETS_DIR, filename)


class TitleBar(QFrame):
    """Modern Frameless Custom TitleBar with Server Connection Badge & Controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(42)
        self._parent = parent
        self._drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(10)

        # App Icon
        self.icon_lbl = QLabel()
        icon_path = get_asset("icon.png")
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_lbl.setPixmap(pix)
        layout.addWidget(self.icon_lbl)

        # App Title
        self.title_lbl = QLabel("ClashBot AI Pro - Remote Client")
        self.title_lbl.setObjectName("TitleBarTitle")
        layout.addWidget(self.title_lbl)

        # Connection Status Badge
        self.conn_badge = QLabel("• Connecting to Server...")
        self.conn_badge.setObjectName("RemoteConnBadge")
        self.conn_badge.setStyleSheet(
            "color: #F59E0B; font-weight: bold; font-size: 11px; margin-left: 10px;"
        )
        layout.addWidget(self.conn_badge)

        layout.addStretch()

        # Server Host Info
        self.server_info_lbl = QLabel("")
        self.server_info_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 500;")
        layout.addWidget(self.server_info_lbl)

        # Settings Toggle Button
        self.settings_btn = QPushButton("⚙ Settings ▾")
        self.settings_btn.setObjectName("SettingsToggleBtn")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setFixedHeight(28)
        self.settings_btn.setStyleSheet("""
            QPushButton#SettingsToggleBtn {
                background-color: rgba(139, 85, 246, 0.18);
                color: #DDD6FE;
                border: 1px solid #8B55F6;
                border-radius: 5px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton#SettingsToggleBtn:hover {
                background-color: rgba(139, 85, 246, 0.40);
                color: #FFFFFF;
            }
        """)
        layout.addWidget(self.settings_btn)

        # Minimize Button
        self.min_btn = QPushButton("🗕")
        self.min_btn.setObjectName("TitleMinBtn")
        self.min_btn.setCursor(Qt.PointingHandCursor)
        self.min_btn.clicked.connect(self._on_minimize)
        layout.addWidget(self.min_btn)

        # Close Button
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("TitleCloseBtn")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.clicked.connect(self._on_close)
        layout.addWidget(self.close_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self._parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self._parent.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def _on_minimize(self):
        if self._parent:
            self._parent.showMinimized()

    def _on_close(self):
        if self._parent:
            self._parent.close()


class RemoteMainWindow(QMainWindow):
    """
    100% Standalone Remote Client Main Window.
    Operates without any dependency on Host engine code, connecting via TCP to the Server.
    """

    def __init__(self, bridge: Optional[ClientBridge] = None, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self._is_syncing = False
        self.settings_drawer_expanded = False

        # Configure Frameless Window with Rounded Corners
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.resize(1020, 680)
        self.setMinimumSize(960, 620)
        self.setWindowTitle("ClashBot AI Pro - Remote Client")

        # Set App Icon
        icon_path = get_asset("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Build Full UI Hierarchy
        self._build_ui()

        # Apply Global Stylesheet
        self.setStyleSheet(styles.get_base_stylesheet())

        # Wire Bridge Signals & Slots
        if self.bridge:
            self._wire_bridge()

        # Initial UI State & Title Bar Sync
        self._update_worker_badge(False, "", False, "")

    # =========================================================================
    # UI BUILDER: HIERARCHY, PAGES, WIDGETS
    # =========================================================================

    def _build_ui(self):
        """Construct central widget, TitleBar, NavPanel, PageStack, BottomBar, and Settings."""
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Custom TitleBar
        self.title_bar = TitleBar(self)
        self.title_bar.settings_btn.clicked.connect(self._toggle_settings_drawer)
        self.main_layout.addWidget(self.title_bar)

        # 2. Middle Body: NavPanel + PageStack + SettingsDrawer Overlay
        self.body_widget = QWidget()
        self.body_layout = QHBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)

        # Sidebar NavPanel
        self._build_nav_panel()
        self.body_layout.addWidget(self.nav_panel)

        # Central Area (Pages Stack + Settings Drawer)
        self.center_area = QWidget()
        self.center_layout = QVBoxLayout(self.center_area)
        self.center_layout.setContentsMargins(0, 0, 0, 0)
        self.center_layout.setSpacing(0)

        # Settings Drawer (Collapsible)
        self._build_settings_drawer()
        self.center_layout.addWidget(self.settings_drawer)
        self.settings_drawer.hide()

        # Page Stack
        self.stack = QStackedWidget()
        self.stack.setObjectName("PageStack")
        self._build_all_pages()
        self.center_layout.addWidget(self.stack)

        self.body_layout.addWidget(self.center_area)
        self.main_layout.addWidget(self.body_widget, stretch=1)

        # 3. Bottom Control Bar
        self._build_bottom_bar()
        self.main_layout.addWidget(self.bottom_bar)

    def _build_nav_panel(self):
        """Build left sidebar with 11 navigation buttons."""
        self.nav_panel = QFrame()
        self.nav_panel.setObjectName("NavPanel")
        self.nav_panel.setFixedWidth(190)

        layout = QVBoxLayout(self.nav_panel)
        layout.setContentsMargins(8, 14, 8, 14)
        layout.setSpacing(4)

        # Logo / Header Brand
        logo_path = get_asset("logo.png")
        if os.path.exists(logo_path):
            logo_lbl = QLabel()
            pix = QPixmap(logo_path).scaled(160, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
            logo_lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(logo_lbl)
            layout.addSpacing(10)

        # Nav Buttons Group
        self.nav_btn_group = QButtonGroup(self)
        self.nav_btn_group.setExclusive(True)
        self.nav_buttons: Dict[str, QPushButton] = {}

        self.PAGE_NAMES = [
            "General", "Attack Army", "Multi Village", "Builder Base",
            "Clan Capital", "Upgrades/Research", "XP Farming", "Extra Modes",
            "Bot Runtime", "Statistics", "Log"
        ]

        for idx, name in enumerate(self.PAGE_NAMES):
            btn = QPushButton(f"  {name}")
            btn.setProperty("nav_button", "true")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(34)
            btn.clicked.connect(lambda chk, n=name: self._on_nav_btn_clicked(n))
            layout.addWidget(btn)
            self.nav_btn_group.addButton(btn, idx)
            self.nav_buttons[name] = btn

        layout.addStretch()

        # Set first page active
        if self.PAGE_NAMES:
            self.nav_buttons[self.PAGE_NAMES[0]].setChecked(True)

    def _build_settings_drawer(self):
        """Collapsible Settings Drawer for Emulator & Server IP/Port configuration."""
        self.settings_drawer = QFrame()
        self.settings_drawer.setObjectName("SettingsDrawer")
        self.settings_drawer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.settings_drawer.setStyleSheet("""
            QFrame#SettingsDrawer {
                background-color: #171A22;
                border-bottom: 2px solid #8B55F6;
                padding: 12px;
            }
        """)


        layout = QGridLayout(self.settings_drawer)
        layout.setColumnStretch(1, 2)
        layout.setColumnStretch(3, 2)

        # Title
        title = QLabel("⚙ Settings & Server Connection")
        title.setStyleSheet("color: #DDD6FE; font-weight: bold; font-size: 13px; margin-bottom: 4px;")
        layout.addWidget(title, 0, 0, 1, 4)

        # Row 1: Emulator Selection
        lbl1 = QLabel("Emulator:")
        lbl1.setFixedWidth(80)
        self.emulator_select = QComboBox()
        self.emulator_select.setObjectName("emulator_select")
        self.emulator_select.addItems(["MuMu Player", "LDPlayer", "BlueStacks", "NoxPlayer", "MEmu"])
        self.emulator_select.setCursor(Qt.PointingHandCursor)
        self.emulator_select.currentTextChanged.connect(
            lambda t: self._on_cmb_changed("emulator_select", t)
        )
        layout.addWidget(lbl1, 1, 0)
        layout.addWidget(self.emulator_select, 1, 1)

        lbl2 = QLabel("Instance:")
        lbl2.setFixedWidth(70)
        self.emulator_instance_select = QComboBox()
        self.emulator_instance_select.setObjectName("emulator_instance_select")
        self.emulator_instance_select.addItems(["0 (Default)", "1", "2", "3"])
        self.emulator_instance_select.setCursor(Qt.PointingHandCursor)
        self.emulator_instance_select.currentTextChanged.connect(
            lambda t: self._on_cmb_changed("emulator_instance_select", t)
        )
        layout.addWidget(lbl2, 1, 2)
        layout.addWidget(self.emulator_instance_select, 1, 3)

        # Row 2: Server Host & Port
        lbl3 = QLabel("Server Host:")
        lbl3.setFixedWidth(80)
        self.server_ip_input = QLineEdit("127.0.0.1")
        self.server_ip_input.setPlaceholderText("IP or Domain (e.g. 192.168.1.100)")
        layout.addWidget(lbl3, 2, 0)
        layout.addWidget(self.server_ip_input, 2, 1)

        lbl4 = QLabel("Port:")
        lbl4.setFixedWidth(70)
        self.server_port_input = QLineEdit("29170")
        layout.addWidget(lbl4, 2, 2)
        layout.addWidget(self.server_port_input, 2, 3)

        # Row 3: Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.restart_adb_btn = QPushButton("Restart ADB")
        self.restart_adb_btn.setObjectName("RestartAdbBtn")
        self.restart_adb_btn.setCursor(Qt.PointingHandCursor)
        self.restart_adb_btn.clicked.connect(lambda: self._on_btn_clicked("restart_adb"))
        btn_layout.addWidget(self.restart_adb_btn)

        self.reconnect_server_btn = QPushButton("Reconnect Server")
        self.reconnect_server_btn.setCursor(Qt.PointingHandCursor)
        self.reconnect_server_btn.clicked.connect(self._on_reconnect_clicked)
        btn_layout.addWidget(self.reconnect_server_btn)

        self.close_drawer_btn = QPushButton("Close Settings")
        self.close_drawer_btn.setCursor(Qt.PointingHandCursor)
        self.close_drawer_btn.clicked.connect(self._toggle_settings_drawer)
        btn_layout.addWidget(self.close_drawer_btn)
        btn_layout.addStretch()


        layout.addLayout(btn_layout, 3, 0, 1, 4)

    def _build_bottom_bar(self):
        """Construct bottom control bar with circular Start/Pause/Stop and telemetry."""
        self.bottom_bar = QFrame()
        self.bottom_bar.setObjectName("BottomBar")
        self.bottom_bar.setFixedHeight(64)

        layout = QHBoxLayout(self.bottom_bar)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        # Profile Selector
        lbl_p = QLabel("Profile:")
        lbl_p.setStyleSheet("font-weight: bold; color: #94A3B8;")
        layout.addWidget(lbl_p)

        self.start_profile = QComboBox()
        self.start_profile.setObjectName("start_profile")
        self.start_profile.setFixedWidth(160)
        self.start_profile.addItems(["Default Profile", "Account 1", "Account 2"])
        self.start_profile.currentTextChanged.connect(
            lambda t: self._on_cmb_changed("start_profile", t)
        )
        layout.addWidget(self.start_profile)

        layout.addSpacing(10)

        # Circular Controls: Start, Pause, Stop
        self.start_btn = QPushButton("▶")
        self.start_btn.setObjectName("StartBtn")
        self.start_btn.setToolTip("Start ClashBot AI Automation")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setFixedSize(44, 44)
        self.start_btn.setStyleSheet("""
            QPushButton#StartBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #10B981, stop:1 #059669);
                color: #FFFFFF;
                border-radius: 22px;
                font-size: 18px;
                font-weight: bold;
                border: 2px solid #34D399;
            }
            QPushButton#StartBtn:hover {
                background: #059669;
                border: 2px solid #6EE7B7;
            }
        """)
        self.start_btn.clicked.connect(lambda: self._on_btn_clicked("start"))
        layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton("⏸")
        self.pause_btn.setObjectName("PauseBtn")
        self.pause_btn.setToolTip("Pause Bot")
        self.pause_btn.setCursor(Qt.PointingHandCursor)
        self.pause_btn.setFixedSize(44, 44)
        self.pause_btn.setStyleSheet("""
            QPushButton#PauseBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #F59E0B, stop:1 #D97706);
                color: #FFFFFF;
                border-radius: 22px;
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #FBBF24;
            }
            QPushButton#PauseBtn:hover {
                background: #D97706;
                border: 2px solid #FCD34D;
            }
        """)
        self.pause_btn.clicked.connect(lambda: self._on_btn_clicked("pause"))
        layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setObjectName("StopBtn")
        self.stop_btn.setToolTip("Stop Bot")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setFixedSize(44, 44)
        self.stop_btn.setStyleSheet("""
            QPushButton#StopBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #EF4444, stop:1 #DC2626);
                color: #FFFFFF;
                border-radius: 22px;
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #F87171;
            }
            QPushButton#StopBtn:hover {
                background: #DC2626;
                border: 2px solid #FCA5A5;
            }
        """)
        self.stop_btn.clicked.connect(lambda: self._on_btn_clicked("stop"))
        layout.addWidget(self.stop_btn)

        layout.addSpacing(16)

        # Bot Status & Worker Telemetry Labels
        status_box = QVBoxLayout()
        status_box.setSpacing(2)

        self.status = QLabel("Ready")
        self.status.setObjectName("status")
        self.status.setStyleSheet("font-weight: bold; color: #F1F5F9; font-size: 13px;")
        status_box.addWidget(self.status)

        self.mode_label = QLabel("Idle • Waiting to Start")
        self.mode_label.setObjectName("mode_label")
        self.mode_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        status_box.addWidget(self.mode_label)

        layout.addLayout(status_box)
        layout.addStretch()

        # Worker Telemetry Badges (ADB + Emulator)
        self.adb_badge = QLabel("ADB: Waiting")
        self.adb_badge.setStyleSheet("""
            background-color: rgba(30, 41, 59, 0.8);
            color: #94A3B8;
            border: 1px solid #334155;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 11px;
            font-weight: bold;
        """)
        layout.addWidget(self.adb_badge)

        self.emu_badge = QLabel("Emulator: Waiting")
        self.emu_badge.setStyleSheet("""
            background-color: rgba(30, 41, 59, 0.8);
            color: #94A3B8;
            border: 1px solid #334155;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 11px;
            font-weight: bold;
        """)
        layout.addWidget(self.emu_badge)

    # =========================================================================
    # BUILD ALL 11 PAGES (EXACT PARITY WITH HOST UI)
    # =========================================================================

    def _build_all_pages(self):
        """Instantiate all 11 pages into the QStackedWidget."""
        self.pages: Dict[str, QWidget] = {}

        self.pages["General"] = self._create_general_page()
        self.pages["Attack Army"] = self._create_attack_army_page()
        self.pages["Multi Village"] = self._create_multi_village_page()
        self.pages["Builder Base"] = self._create_builder_base_page()
        self.pages["Clan Capital"] = self._create_clan_capital_page()
        self.pages["Upgrades/Research"] = self._create_upgrades_research_page()
        self.pages["XP Farming"] = self._create_xp_farming_page()
        self.pages["Extra Modes"] = self._create_extra_modes_page()
        self.pages["Bot Runtime"] = self._create_bot_runtime_page()
        self.pages["Statistics"] = self._create_statistics_page()
        self.pages["Log"] = self._create_log_page()

        for name in self.PAGE_NAMES:
            if name in self.pages:
                self.stack.addWidget(self.pages[name])

    def _wrap_scrollable(self, widget: QWidget) -> QScrollArea:
        """Wrap page widget inside a sleek dark scroll area."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setWidget(widget)
        return scroll

    # --- 1. General Page ---
    def _create_general_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # Farming Enabled
        self.farming_enabled = self._create_checkbox("Enable Farming", "farming_enabled", True)
        layout.addWidget(self.farming_enabled)

        # Group 1: Wall Upgrades
        gb_walls = QGroupBox("Wall Upgrades")
        gbl_walls = QHBoxLayout(gb_walls)
        self.upgrade_walls = self._create_checkbox("Upgrade Walls", "upgrade_walls", False)
        gbl_walls.addWidget(self.upgrade_walls)

        lbl_wall_stop = QLabel("Stop At Level:")
        gbl_walls.addWidget(lbl_wall_stop)
        self.wall_stop_level = self._create_combobox(
            "wall_stop_level", [str(i) for i in range(1, 20)], "15"
        )
        gbl_walls.addWidget(self.wall_stop_level)
        gbl_walls.addStretch()
        layout.addWidget(gb_walls)

        # Group 2: Attack Filter
        gb_filter = QGroupBox("Attack Filter")
        gbl_filter = QGridLayout(gb_filter)
        gbl_filter.addWidget(QLabel("Min Gold:"), 0, 0)
        self.attack_gold = self._create_spinbox("attack_gold", 0, 50000000, 750000)
        gbl_filter.addWidget(self.attack_gold, 0, 1)

        gbl_filter.addWidget(QLabel("Min Elixir:"), 0, 2)
        self.attack_elixir = self._create_spinbox("attack_elixir", 0, 50000000, 510000)
        gbl_filter.addWidget(self.attack_elixir, 0, 3)

        gbl_filter.addWidget(QLabel("Min Dark:"), 1, 0)
        self.attack_dark = self._create_spinbox("attack_dark", 0, 50000, 5000)
        gbl_filter.addWidget(self.attack_dark, 1, 1)

        self.dead_bases_only = self._create_checkbox("Dead Bases Only", "dead_bases_only", True)
        gbl_filter.addWidget(self.dead_bases_only, 1, 2, 1, 2)
        layout.addWidget(gb_filter)

        # Group 3: Donations
        gb_don = QGroupBox("Donations")
        gbl_don = QHBoxLayout(gb_don)
        self.request_donations = self._create_checkbox("Request Donations", "request_donations", True)
        self.wait_cc_troops = self._create_checkbox("Wait 60s for CC", "wait_cc_troops", False)
        self.enable_donations = self._create_checkbox("Enable Donating", "enable_donations", False)
        gbl_don.addWidget(self.request_donations)
        gbl_don.addWidget(self.wait_cc_troops)
        gbl_don.addWidget(self.enable_donations)
        gbl_don.addStretch()
        layout.addWidget(gb_don)

        # Group 4: Battle Conditions
        gb_cond = QGroupBox("Battle Conditions")
        gbl_cond = QHBoxLayout(gb_cond)
        self.end_on_stars = self._create_checkbox("End Battle On Stars", "end_on_stars", False)
        self.target_stars = self._create_combobox("target_stars", ["1", "2", "3"], "1")
        gbl_cond.addWidget(self.end_on_stars)
        gbl_cond.addWidget(QLabel("Stars:"))
        gbl_cond.addWidget(self.target_stars)
        gbl_cond.addStretch()
        layout.addWidget(gb_cond)

        # Group 5: Extras
        gb_extra = QGroupBox("Extras")
        gbl_extra = QGridLayout(gb_extra)
        self.collect_collectors = self._create_checkbox("Collect Collectors", "collect_collectors", True)
        self.start_helpers = self._create_checkbox("Start Helpers", "start_helpers", True)
        self.collect_cart = self._create_checkbox("Collect Loot Cart", "collect_cart", True)
        self.clear_tombs = self._create_checkbox("Clear Tombs", "clear_tombs", True)
        self.remove_obstacles = self._create_checkbox("Remove Obstacles", "remove_obstacles", False)
        self.collect_achievements = self._create_checkbox("Collect Achievements", "collect_achievements", True)
        self.collect_cc_loot = self._create_checkbox("Collect Clan Castle", "collect_cc_loot", True)
        self.claim_weekly_deal = self._create_checkbox("Claim Weekly Deal", "claim_weekly_deal", False)

        extras_cbs = [
            self.collect_collectors, self.start_helpers, self.collect_cart, self.clear_tombs,
            self.remove_obstacles, self.collect_achievements, self.collect_cc_loot, self.claim_weekly_deal
        ]
        for i, cb in enumerate(extras_cbs):
            gbl_extra.addWidget(cb, i // 4, i % 4)
        layout.addWidget(gb_extra)

        layout.addStretch()
        return self._wrap_scrollable(container)

    # --- 2. Attack Army Page ---
    def _create_attack_army_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        gb_train = QGroupBox("Army Training & Deployment")
        gbl_train = QGridLayout(gb_train)
        gbl_train.addWidget(QLabel("Attack Strategy:"), 0, 0)
        self.strategy = self._create_combobox(
            "strategy", ["Electro Dragon/Loon", "Barch", "Sneaky Goblins", "Baby Dragons", "Zap Dragons", "Witches"], "Electro Dragon/Loon"
        )
        gbl_train.addWidget(self.strategy, 0, 1)

        gbl_train.addWidget(QLabel("Quick Train Slot:"), 0, 2)
        self.army_slot = self._create_combobox(
            "army_slot", ["Slot 1", "Slot 2", "Slot 3"], "Slot 1"
        )
        gbl_train.addWidget(self.army_slot, 0, 3)
        layout.addWidget(gb_train)

        gb_settings = QGroupBox("Attack Settings")
        gbl_settings = QGridLayout(gb_settings)
        self.hero_tap_delay_enabled = self._create_checkbox("Hero Re-Tap Delay", "hero_tap_delay_enabled", True)
        self.hero_tap_delay_seconds = self._create_spinbox("hero_tap_delay_seconds", 0, 10, 1)
        gbl_settings.addWidget(self.hero_tap_delay_enabled, 0, 0)
        gbl_settings.addWidget(self.hero_tap_delay_seconds, 0, 1)

        self.air_troop_width_enabled = self._create_checkbox("Air Troop Spread (%)", "air_troop_width_enabled", True)
        self.air_troop_width = self._create_spinbox("air_troop_width", 10, 100, 60)
        gbl_settings.addWidget(self.air_troop_width_enabled, 1, 0)
        gbl_settings.addWidget(self.air_troop_width, 1, 1)
        layout.addWidget(gb_settings)

        layout.addStretch()
        return self._wrap_scrollable(container)

    # --- 3. Multi Village Page ---
    def _create_multi_village_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        gb_multi = QGroupBox("Multi Village Configuration")
        gbl_multi = QVBoxLayout(gb_multi)
        self.multi_enabled = self._create_checkbox("Enable Multi Village", "multi_enabled", False)
        self.use_root_profile_swap = self._create_checkbox("Use Root Profile Swap", "use_root_profile_swap", False)
        gbl_multi.addWidget(self.multi_enabled)
        gbl_multi.addWidget(self.use_root_profile_swap)
        layout.addWidget(gb_multi)

        gb_settings = QGroupBox("Village Switch Settings")
        gbl_settings = QGridLayout(gb_settings)
        gbl_settings.addWidget(QLabel("Switch Condition:"), 0, 0)
        self.switch_condition = self._create_combobox(
            "switch_condition", ["After time", "After attacks", "Loot full"], "After time"
        )
        gbl_settings.addWidget(self.switch_condition, 0, 1)

        gbl_settings.addWidget(QLabel("Switch Minutes:"), 0, 2)
        self.switch_minutes = self._create_spinbox("switch_minutes", 1, 300, 10)
        gbl_settings.addWidget(self.switch_minutes, 0, 3)

        gbl_settings.addWidget(QLabel("Total Village Count:"), 1, 0)
        self.village_count = self._create_spinbox("village_count", 1, 50, 10)
        gbl_settings.addWidget(self.village_count, 1, 1)
        layout.addWidget(gb_settings)

        layout.addStretch()
        return self._wrap_scrollable(container)

    # --- 4. Builder Base Page ---
    def _create_builder_base_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        gb_bb = QGroupBox("Builder Base Configuration")
        gbl_bb = QGridLayout(gb_bb)
        self.builder_enabled = self._create_checkbox("Enable Builder Base", "builder_enabled", False)
        gbl_bb.addWidget(self.builder_enabled, 0, 0, 1, 2)

        gbl_bb.addWidget(QLabel("Return Policy:"), 1, 0)
        self.builder_return_policy = self._create_combobox(
            "builder_return_policy", ["Gold + Elixir Full", "Always Return", "Target Attacks"], "Gold + Elixir Full"
        )
        gbl_bb.addWidget(self.builder_return_policy, 1, 1)

        gbl_bb.addWidget(QLabel("Troop Strategy:"), 1, 2)
        self.builder_army_troop = self._create_combobox(
            "builder_army_troop", ["Baby Dragon", "Night Witch", "Minion", "Barbarian"], "Baby Dragon"
        )
        gbl_bb.addWidget(self.builder_army_troop, 1, 3)
        layout.addWidget(gb_bb)

        gb_cond = QGroupBox("Attack Conditions")
        gbl_cond = QGridLayout(gb_cond)
        gbl_cond.addWidget(QLabel("Target Stars:"), 0, 0)
        self.builder_target_stars = self._create_combobox("builder_target_stars", ["1", "2", "3", "Any"], "1")
        gbl_cond.addWidget(self.builder_target_stars, 0, 1)

        gbl_cond.addWidget(QLabel("Max Attacks:"), 0, 2)
        self.builder_max_attacks = self._create_spinbox("builder_max_attacks", 1, 100, 10)
        gbl_cond.addWidget(self.builder_max_attacks, 0, 3)

        self.builder_end_after_drop = self._create_checkbox("End battle after troop drop", "builder_end_after_drop", True)
        gbl_cond.addWidget(self.builder_end_after_drop, 1, 0, 1, 4)
        layout.addWidget(gb_cond)

        gb_extras = QGroupBox("Builder Base Extras")
        gbl_extras = QGridLayout(gb_extras)
        self.builderbase_upgrade_walls = self._create_checkbox("Upgrade Walls", "builderbase_upgrade_walls", False)
        self.builder_collect_resources_first_run = self._create_checkbox("Collect Resources", "builder_collect_resources_first_run", True)
        self.builder_collect_gem_mine = self._create_checkbox("Collect Gem Mine", "builder_collect_gem_mine", True)
        self.builder_collect_star_bonus = self._create_checkbox("Boost Clock Tower", "builder_collect_star_bonus", True)
        self.bb_remove_obstacles = self._create_checkbox("Remove Obstacles", "bb_remove_obstacles", False)

        gbl_extras.addWidget(self.builderbase_upgrade_walls, 0, 0)
        gbl_extras.addWidget(self.builder_collect_resources_first_run, 0, 1)
        gbl_extras.addWidget(self.builder_collect_gem_mine, 1, 0)
        gbl_extras.addWidget(self.builder_collect_star_bonus, 1, 1)
        gbl_extras.addWidget(self.bb_remove_obstacles, 2, 0)
        layout.addWidget(gb_extras)

        layout.addStretch()
        return self._wrap_scrollable(container)

    # --- 5. Clan Capital Page ---
    def _create_clan_capital_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        gb_raid = QGroupBox("Capital Raid")
        gbl_raid = QHBoxLayout(gb_raid)
        self.clan_capital_enable = self._create_checkbox("Enable Capital Raid", "clan_capital_enable", False)
        gbl_raid.addWidget(self.clan_capital_enable)
        gbl_raid.addWidget(QLabel("Troop:"))
        self.clan_capital_troop = self._create_combobox(
            "clan_capital_troop", ["Miner", "Super Dragon", "Super Wizard", "Pekka"], "Miner"
        )
        gbl_raid.addWidget(self.clan_capital_troop)
        gbl_raid.addStretch()
        layout.addWidget(gb_raid)

        gb_gold = QGroupBox("Capital Gold")
        gbl_gold = QVBoxLayout(gb_gold)
        self.clan_capital_dump_gold_treasury_if_full = self._create_checkbox(
            "Dump gold in treasury if full", "clan_capital_dump_gold_treasury_if_full", True
        )
        gbl_gold.addWidget(self.clan_capital_dump_gold_treasury_if_full)
        layout.addWidget(gb_gold)

        layout.addStretch()
        return self._wrap_scrollable(container)

    # --- 6. Upgrades / Research Page ---
    def _create_upgrades_research_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # Home Village Upgrades & Research
        gb_home = QGroupBox("Home Village Upgrades & Lab")
        gbl_home = QGridLayout(gb_home)

        self.home_upgrade_enabled = self._create_checkbox("Upgrades", "home_upgrade_enabled", True)
        self.home_upgrade_perform_suggested = self._create_checkbox("Perform Suggested", "home_upgrade_perform_suggested", True)
        self.home_save_1_builder = self._create_checkbox("Save 1 Builder", "home_save_1_builder", False)
        self.home_upgrade_suggested_ignore_townhall = self._create_checkbox("Ignore Townhall", "home_upgrade_suggested_ignore_townhall", True)
        self.home_upgrade_suggested_rotate = self._create_checkbox("Rotate Suggested Upgrades", "home_upgrade_suggested_rotate", False)
        self.home_rush_th = self._create_checkbox("Rush TH", "home_rush_th", False)

        gbl_home.addWidget(self.home_upgrade_enabled, 0, 0)
        gbl_home.addWidget(self.home_upgrade_perform_suggested, 0, 1)
        gbl_home.addWidget(self.home_save_1_builder, 0, 2)
        gbl_home.addWidget(self.home_upgrade_suggested_ignore_townhall, 1, 0)
        gbl_home.addWidget(self.home_upgrade_suggested_rotate, 1, 1)
        gbl_home.addWidget(self.home_rush_th, 1, 2)

        self.home_research_enabled = self._create_checkbox("Research", "home_research_enabled", True)
        self.home_research_perform_suggested = self._create_checkbox("Perform Suggested", "home_research_perform_suggested", True)
        self.home_research_use_1_gem_helper = self._create_checkbox("Use 1 Gem Helper", "home_research_use_1_gem_helper", False)
        self.home_research_suggested_rotate = self._create_checkbox("Rotate Suggested Upgrades", "home_research_suggested_rotate", False)
        self.home_research_pets = self._create_checkbox("Pets", "home_research_pets", False)

        gbl_home.addWidget(self.home_research_enabled, 2, 0)
        gbl_home.addWidget(self.home_research_perform_suggested, 2, 1)
        gbl_home.addWidget(self.home_research_use_1_gem_helper, 2, 2)
        gbl_home.addWidget(self.home_research_suggested_rotate, 3, 0)
        gbl_home.addWidget(self.home_research_pets, 3, 1)

        self.home_research_pet_target = self._create_combobox(
            "home_research_pet_target", ["Angry Jelly", "L.A.S.S.I", "Electro Owl", "Mighty Yak", "Unicorn", "Frosty", "Diggy", "Poison Lizard", "Phoenix", "Spirit Fox"], "Angry Jelly"
        )
        gbl_home.addWidget(self.home_research_pet_target, 3, 2)
        layout.addWidget(gb_home)

        # Builder Base Upgrades & Research
        gb_bb_upg = QGroupBox("Builder Base Upgrades & Lab")
        gbl_bb_upg = QGridLayout(gb_bb_upg)

        self.bb_upgrade_enabled = self._create_checkbox("Upgrades", "bb_upgrade_enabled", True)
        self.bb_upgrade_perform_suggested = self._create_checkbox("Perform Suggested", "bb_upgrade_perform_suggested", True)
        self.bb_save_1_builder = self._create_checkbox("Save 1 Builder", "bb_save_1_builder", False)
        self.bb_upgrade_suggested_rotate = self._create_checkbox("Rotate Suggested Upgrades", "bb_upgrade_suggested_rotate", False)

        gbl_bb_upg.addWidget(self.bb_upgrade_enabled, 0, 0)
        gbl_bb_upg.addWidget(self.bb_upgrade_perform_suggested, 0, 1)
        gbl_bb_upg.addWidget(self.bb_save_1_builder, 0, 2)
        gbl_bb_upg.addWidget(self.bb_upgrade_suggested_rotate, 1, 0)

        self.bb_research_enabled = self._create_checkbox("Research", "bb_research_enabled", True)
        self.bb_research_perform_suggested = self._create_checkbox("Perform Suggested", "bb_research_perform_suggested", True)
        self.bb_research_suggested_rotate = self._create_checkbox("Rotate Suggested Upgrades", "bb_research_suggested_rotate", False)

        gbl_bb_upg.addWidget(self.bb_research_enabled, 2, 0)
        gbl_bb_upg.addWidget(self.bb_research_perform_suggested, 2, 1)
        gbl_bb_upg.addWidget(self.bb_research_suggested_rotate, 2, 2)
        layout.addWidget(gb_bb_upg)

        layout.addStretch()
        return self._wrap_scrollable(container)

    # --- 7. XP Farming Page ---
    def _create_xp_farming_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        gb_req = QGroupBox("Request and Dump Troops")
        gbl_req = QGridLayout(gb_req)
        self.request_leave_enabled = self._create_checkbox("Enable Request and Dump", "request_leave_enabled", False)
        self.request_leave_join = self._create_checkbox("Join Clan", "request_leave_join", True)
        self.request_leave_leave = self._create_checkbox("Leave Clan", "request_leave_leave", True)
        self.request_leave_wait_cooldown = self._create_checkbox("Wait for Cooldown", "request_leave_wait_cooldown", True)
        self.request_leave_set_army_slot1 = self._create_checkbox("Set Army Slot 1", "request_leave_set_army_slot1", True)

        gbl_req.addWidget(self.request_leave_enabled, 0, 0)
        gbl_req.addWidget(self.request_leave_join, 0, 1)
        gbl_req.addWidget(self.request_leave_leave, 1, 0)
        gbl_req.addWidget(self.request_leave_wait_cooldown, 1, 1)
        gbl_req.addWidget(self.request_leave_set_army_slot1, 2, 0)
        layout.addWidget(gb_req)

        gb_don = QGroupBox("Donate Only")
        gbl_don = QHBoxLayout(gb_don)
        self.donate_only_enabled = self._create_checkbox("Enable Donate Only", "donate_only_enabled", False)
        self.donate_only_speed_mode = self._create_checkbox("Speed Mode", "donate_only_speed_mode", False)
        gbl_don.addWidget(self.donate_only_enabled)
        gbl_don.addWidget(self.donate_only_speed_mode)
        gbl_don.addStretch()
        layout.addWidget(gb_don)

        layout.addStretch()
        return self._wrap_scrollable(container)

    # --- 8. Extra Modes Page ---
    def _create_extra_modes_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # Ranked
        gb_ranked = QGroupBox("Ranked Attacks")
        gbl_ranked = QGridLayout(gb_ranked)
        self.rank_first = self._create_checkbox("Enable Ranked Attacks", "rank_first", False)
        self.ranked_request_donations = self._create_checkbox("Request Donations", "ranked_request_donations", True)
        self.ranked_wait_cc_troops = self._create_checkbox("Wait 60s for CC", "ranked_wait_cc_troops", False)
        gbl_ranked.addWidget(self.rank_first, 0, 0)
        gbl_ranked.addWidget(self.ranked_request_donations, 0, 1)
        gbl_ranked.addWidget(self.ranked_wait_cc_troops, 0, 2)
        layout.addWidget(gb_ranked)

        # Clan Games
        gb_cg = QGroupBox("Clan Games")
        gbl_cg = QGridLayout(gb_cg)
        self.clan_games_enable = self._create_checkbox("Enable Clan Games", "clan_games_enable", False)
        self.cg_troop_challenges = self._create_checkbox("Enable Super Troop Challenges", "cg_troop_challenges", True)
        self.cg_claim_rewards_for_gems = self._create_checkbox("Claim Rewards for Gems", "cg_claim_rewards_for_gems", False)
        gbl_cg.addWidget(self.clan_games_enable, 0, 0)
        gbl_cg.addWidget(self.cg_troop_challenges, 0, 1)
        gbl_cg.addWidget(self.cg_claim_rewards_for_gems, 0, 2)
        layout.addWidget(gb_cg)

        # War Attacks
        gb_war = QGroupBox("War Attacks")
        gbl_war = QGridLayout(gb_war)
        self.war_attacks_enabled = self._create_checkbox("Enable War Attacks", "war_attacks_enabled", False)
        gbl_war.addWidget(self.war_attacks_enabled, 0, 0)

        gbl_war.addWidget(QLabel("War Mode:"), 0, 1)
        self.war_mode = self._create_combobox("war_mode", ["FWA", "Regular War", "CWL"], "FWA")
        gbl_war.addWidget(self.war_mode, 0, 2)

        self.war_request_cc = self._create_checkbox("Request Donations", "war_request_cc", True)
        self.war_wait_cc = self._create_checkbox("Wait 60s for CC", "war_wait_cc", False)
        self.war_one_attack_per_session = self._create_checkbox("Use 1 Attack Per Session", "war_one_attack_per_session", False)
        gbl_war.addWidget(self.war_request_cc, 1, 0)
        gbl_war.addWidget(self.war_wait_cc, 1, 1)
        gbl_war.addWidget(self.war_one_attack_per_session, 1, 2)
        layout.addWidget(gb_war)

        # Account Creation
        gb_acc = QGroupBox("Account Creation")
        gbl_acc = QHBoxLayout(gb_acc)
        gbl_acc.addWidget(QLabel("Count:"))
        self.account_creation_count = self._create_spinbox("account_creation_count", 1, 100, 1)
        gbl_acc.addWidget(self.account_creation_count)

        self.account_creation_numeral_suffix = self._create_checkbox("Numeral Suffix", "account_creation_numeral_suffix", True)
        gbl_acc.addWidget(self.account_creation_numeral_suffix)

        self.account_creation_start_btn = QPushButton("Start Creation")
        self.account_creation_start_btn.setCursor(Qt.PointingHandCursor)
        self.account_creation_start_btn.clicked.connect(lambda: self._on_btn_clicked("account_creation_start"))
        gbl_acc.addWidget(self.account_creation_start_btn)

        self.account_creation_stop_btn = QPushButton("Stop Creation")
        self.account_creation_stop_btn.setCursor(Qt.PointingHandCursor)
        self.account_creation_stop_btn.clicked.connect(lambda: self._on_btn_clicked("account_creation_stop"))
        gbl_acc.addWidget(self.account_creation_stop_btn)
        gbl_acc.addStretch()
        layout.addWidget(gb_acc)

        layout.addStretch()
        return self._wrap_scrollable(container)

    # --- 9. Bot Runtime Page ---
    def _create_bot_runtime_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # Bot End Condition
        gb_end = QGroupBox("Bot End Condition")
        gbl_end = QGridLayout(gb_end)
        self.bot_end_condition_enabled = self._create_checkbox("Enable Bot End Condition", "bot_end_condition_enabled", False)
        gbl_end.addWidget(self.bot_end_condition_enabled, 0, 0, 1, 2)

        gbl_end.addWidget(QLabel("Condition:"), 1, 0)
        self.bot_end_condition_type = self._create_combobox(
            "bot_end_condition_type",
            ["End when all active account(s) are loot full", "End after time", "End after attacks"],
            "End when all active account(s) are loot full"
        )
        gbl_end.addWidget(self.bot_end_condition_type, 1, 1)

        gbl_end.addWidget(QLabel("Minutes:"), 1, 2)
        self.bot_end_time_minutes = self._create_spinbox("bot_end_time_minutes", 1, 1440, 120)
        gbl_end.addWidget(self.bot_end_time_minutes, 1, 3)
        layout.addWidget(gb_end)

        # Active Hours
        gb_hours = QGroupBox("Active Hours")
        gbl_hours = QHBoxLayout(gb_hours)
        self.active_hours_enabled = self._create_checkbox("Enable Active Hours", "active_hours_enabled", False)
        gbl_hours.addWidget(self.active_hours_enabled)

        gbl_hours.addWidget(QLabel("Start:"))
        self.active_hours_start = QLineEdit("00:00")
        self.active_hours_start.setFixedWidth(70)
        gbl_hours.addWidget(self.active_hours_start)

        gbl_hours.addWidget(QLabel("End:"))
        self.active_hours_end = QLineEdit("23:59")
        self.active_hours_end.setFixedWidth(70)
        gbl_hours.addWidget(self.active_hours_end)
        gbl_hours.addStretch()
        layout.addWidget(gb_hours)

        # Humanized Breaks
        gb_breaks = QGroupBox("Humanized Breaks")
        gbl_breaks = QGridLayout(gb_breaks)
        self.humanized_breaks_enabled = self._create_checkbox("Enable Humanized Breaks", "humanized_breaks_enabled", False)
        gbl_breaks.addWidget(self.humanized_breaks_enabled, 0, 0, 1, 4)

        gbl_breaks.addWidget(QLabel("Run Min:"), 1, 0)
        self.humanized_run_min = self._create_spinbox("humanized_run_min", 5, 300, 30)
        gbl_breaks.addWidget(self.humanized_run_min, 1, 1)

        gbl_breaks.addWidget(QLabel("Run Max:"), 1, 2)
        self.humanized_run_max = self._create_spinbox("humanized_run_max", 10, 600, 90)
        gbl_breaks.addWidget(self.humanized_run_max, 1, 3)

        gbl_breaks.addWidget(QLabel("Break Min:"), 2, 0)
        self.humanized_break_min = self._create_spinbox("humanized_break_min", 1, 120, 5)
        gbl_breaks.addWidget(self.humanized_break_min, 2, 1)

        gbl_breaks.addWidget(QLabel("Break Max:"), 2, 2)
        self.humanized_break_max = self._create_spinbox("humanized_break_max", 5, 240, 50)
        gbl_breaks.addWidget(self.humanized_break_max, 2, 3)
        layout.addWidget(gb_breaks)

        layout.addStretch()
        return self._wrap_scrollable(container)

    # --- 10. Statistics Page ---
    def _create_statistics_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # Top Filter
        top_h = QHBoxLayout()
        top_h.addWidget(QLabel("Range Filter:"))
        self.stats_range_filter = self._create_combobox(
            "stats_range_filter", ["Current Session", "Today", "Last 7 Days", "All Time"], "Current Session"
        )
        top_h.addWidget(self.stats_range_filter)
        top_h.addStretch()
        layout.addLayout(top_h)

        # Cards Grid: Loot & Attacks
        cards_grid = QGridLayout()
        cards_grid.setSpacing(14)

        self.stat_gold = self._create_stat_card("Gold Farmed", "0", "#F59E0B", "gold.png")
        self.stat_elixir = self._create_stat_card("Elixir Farmed", "0", "#EC4899", "elixir.png")
        self.stat_dark = self._create_stat_card("Dark Elixir", "0", "#10B981", "dark.png")
        self.stat_attacks = self._create_stat_card("Attacks Won", "0", "#8B55F6", "attack.png")

        cards_grid.addWidget(self.stat_gold, 0, 0)
        cards_grid.addWidget(self.stat_elixir, 0, 1)
        cards_grid.addWidget(self.stat_dark, 1, 0)
        cards_grid.addWidget(self.stat_attacks, 1, 1)
        layout.addLayout(cards_grid)

        # Misc Stats Group
        gb_misc = QGroupBox("Session Details")
        gbl_misc = QGridLayout(gb_misc)
        self.stat_session_time = QLabel("00:00:00")
        self.stat_walls = QLabel("0")
        self.stat_obstacles = QLabel("0")

        gbl_misc.addWidget(QLabel("Session Time:"), 0, 0)
        gbl_misc.addWidget(self.stat_session_time, 0, 1)
        gbl_misc.addWidget(QLabel("Walls Upgraded:"), 0, 2)
        gbl_misc.addWidget(self.stat_walls, 0, 3)
        gbl_misc.addWidget(QLabel("Obstacles Cleared:"), 1, 0)
        gbl_misc.addWidget(self.stat_obstacles, 1, 1)
        layout.addWidget(gb_misc)

        layout.addStretch()
        return self._wrap_scrollable(container)

    def _create_stat_card(self, title: str, value: str, color: str, icon_name: str) -> QFrame:
        """Create a modern card widget for statistics."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #171B24;
                border: 1px solid #282D3C;
                border-left: 4px solid {color};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        cl = QHBoxLayout(card)
        cl.setContentsMargins(8, 8, 8, 8)

        # Icon
        icon_path = get_asset(icon_name)
        if os.path.exists(icon_path):
            icon_lbl = QLabel()
            pix = QPixmap(icon_path).scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_lbl.setPixmap(pix)
            cl.addWidget(icon_lbl)

        # Labels
        vl = QVBoxLayout()
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 500;")
        v_lbl = QLabel(value)
        v_lbl.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: bold;")
        v_lbl.setObjectName(f"val_{title.lower().replace(' ', '_')}")
        vl.addWidget(t_lbl)
        vl.addWidget(v_lbl)
        cl.addLayout(vl)
        cl.addStretch()
        return card

    # --- 11. Log Page ---
    def _create_log_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        # Header controls
        ctrl_h = QHBoxLayout()
        title = QLabel("Bot Execution Logs")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #ECEFF4;")
        ctrl_h.addWidget(title)
        ctrl_h.addStretch()

        self.clear_logs_btn = QPushButton("Clear Log")
        self.clear_logs_btn.setCursor(Qt.PointingHandCursor)
        self.clear_logs_btn.clicked.connect(self._clear_logs)
        ctrl_h.addWidget(self.clear_logs_btn)
        layout.addLayout(ctrl_h)

        # Text Area
        self.log_textbox = QTextEdit()
        self.log_textbox.setObjectName("log_textbox")
        self.log_textbox.setReadOnly(True)
        self.log_textbox.setStyleSheet("""
            QTextEdit#log_textbox {
                background-color: #0E1118;
                color: #A6ACCD;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                border: 1px solid #1F2430;
                border-radius: 8px;
                padding: 8px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(self.log_textbox, stretch=1)
        return container

    # =========================================================================
    # WIDGET FACTORY HELPERS
    # =========================================================================

    def _create_checkbox(self, text: str, attr_name: str, default: bool = False) -> QCheckBox:
        """Create a themed QCheckBox with hand cursor and automatic sync hook."""
        cb = QCheckBox(text)
        cb.setObjectName(attr_name)
        cb.setChecked(default)
        cb.setCursor(Qt.PointingHandCursor)
        cb.toggled.connect(lambda checked, n=attr_name: self._on_cb_toggled(n, checked))
        return cb

    def _create_combobox(self, attr_name: str, items: List[str], default: str = "") -> QComboBox:
        """Create a themed QComboBox with items and automatic sync hook."""
        cmb = QComboBox()
        cmb.setObjectName(attr_name)
        cmb.addItems(items)
        if default and default in items:
            cmb.setCurrentText(default)
        cmb.setCursor(Qt.PointingHandCursor)
        cmb.currentTextChanged.connect(lambda text, n=attr_name: self._on_cmb_changed(n, text))
        return cmb

    def _create_spinbox(self, attr_name: str, min_val: int, max_val: int, default: int) -> QSpinBox:
        """Create a themed QSpinBox with range and automatic sync hook."""
        sb = QSpinBox()
        sb.setObjectName(attr_name)
        sb.setRange(min_val, max_val)
        sb.setValue(default)
        sb.setCursor(Qt.PointingHandCursor)
        sb.valueChanged.connect(lambda val, n=attr_name: self._on_sb_changed(n, val))
        return sb

    # =========================================================================
    # ACTIONS & EVENT DISPATCHING (CLIENT -> SERVER BRIDGE)
    # =========================================================================

    def _on_nav_btn_clicked(self, page_name: str):
        """Handle sidebar page navigation click."""
        self.switch_page(page_name)
        if not self._is_syncing and self.bridge:
            self.bridge.send_action({"action": "switch_page", "target": page_name})

    def switch_page(self, page_name: str):
        """Switch active page in stack and highlight navigation button."""
        if page_name in self.pages:
            self.stack.setCurrentWidget(self.pages[page_name])
        if page_name in self.nav_buttons:
            self.nav_buttons[page_name].setChecked(True)

    def _on_cb_toggled(self, attr_name: str, checked: bool):
        """User toggled a checkbox on the client interface."""
        if self._is_syncing or not self.bridge:
            return
        self.bridge.send_action({
            "action": "toggle_checkbox",
            "target": attr_name,
            "value": checked
        })

    def _on_cmb_changed(self, attr_name: str, text: str):
        """User changed a combobox selection."""
        if self._is_syncing or not self.bridge:
            return
        self.bridge.send_action({
            "action": "set_combobox",
            "target": attr_name,
            "value": text
        })

    def _on_sb_changed(self, attr_name: str, val: int):
        """User adjusted a spinbox value."""
        if self._is_syncing or not self.bridge:
            return
        self.bridge.send_action({
            "action": "set_spinbox",
            "target": attr_name,
            "value": val
        })

    def _on_btn_clicked(self, btn_name: str):
        """User clicked a control button (Start, Pause, Stop, Restart ADB)."""
        if self._is_syncing or not self.bridge:
            return
        self.bridge.send_action({
            "action": "click_button",
            "target": btn_name
        })

    def _toggle_settings_drawer(self):
        """Slide/toggle settings drawer."""
        self.settings_drawer_expanded = not self.settings_drawer_expanded
        self.settings_drawer.setVisible(self.settings_drawer_expanded)
        self.title_bar.settings_btn.setText("⚙ Settings ▴" if self.settings_drawer_expanded else "⚙ Settings ▾")

    def _on_reconnect_clicked(self):
        """Handle user reconnect request with custom IP/Port."""
        new_host = self.server_ip_input.text().strip()
        try:
            new_port = int(self.server_port_input.text().strip())
        except ValueError:
            new_port = 29170

        if self.bridge:
            self.bridge.stop()
            self.bridge.host = new_host
            self.bridge.port = new_port
            self.bridge.start()
            self._update_server_info(new_host, new_port)

    def _clear_logs(self):
        """Clear local log viewer text."""
        self.log_textbox.clear()

    def append_log(self, text: str):
        """Append log line with auto-scrolling."""
        self.log_textbox.append(text)
        sb = self.log_textbox.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    # =========================================================================
    # BRIDGE SIGNAL HANDLERS (SERVER -> CLIENT)
    # =========================================================================

    def _wire_bridge(self):
        """Connect Qt signals from ClientBridge to UI updating methods."""
        self.bridge.connected.connect(self._on_server_connected)
        self.bridge.disconnected.connect(self._on_server_disconnected)
        self.bridge.status_message.connect(self._on_bridge_status)
        self.bridge.full_state_received.connect(self._on_full_state)
        self.bridge.widget_updated.connect(self._on_widget_updated)
        self.bridge.page_switched.connect(self._on_remote_page_switched)
        self.bridge.log_received.connect(self.append_log)

    def _on_server_connected(self):
        """Server is online and connection is established."""
        self.title_bar.conn_badge.setText("🟢 • Connected")
        self.title_bar.conn_badge.setStyleSheet(
            "color: #10B981; font-weight: bold; font-size: 11px; margin-left: 10px;"
        )
        self._update_server_info(self.bridge.host, self.bridge.port)

    def _on_server_disconnected(self):
        """Server went offline or connection dropped."""
        self.title_bar.conn_badge.setText("🔴 • Server Offline (Reconnecting...)")
        self.title_bar.conn_badge.setStyleSheet(
            "color: #EF4444; font-weight: bold; font-size: 11px; margin-left: 10px;"
        )
        self._update_worker_badge(False, "", False, "")

    def _on_bridge_status(self, msg: str):
        """Display network status line in mode_label."""
        if "Connecting" in msg or "Disconnected" in msg:
            self.mode_label.setText(msg)

    def _update_server_info(self, host: str, port: int):
        self.title_bar.server_info_lbl.setText(f"Server: {host}:{port}")

    def _on_full_state(self, state: Dict[str, Any]):
        """Receive full state snapshot from Server and synchronize all UI controls."""
        self._is_syncing = True
        try:
            # Checkboxes
            cbs = state.get("checkboxes", {})
            for name, val in cbs.items():
                w = getattr(self, name, None)
                if isinstance(w, QCheckBox) and w.isChecked() != bool(val):
                    w.setChecked(bool(val))

            # Comboboxes
            cmbs = state.get("comboboxes", {})
            for name, c_data in cmbs.items():
                w = getattr(self, name, None)
                if isinstance(w, QComboBox):
                    items = c_data.get("items", [])
                    if items and w.count() != len(items):
                        w.clear()
                        w.addItems(items)
                    cur = c_data.get("currentText", "")
                    if cur and w.currentText() != cur:
                        w.setCurrentText(cur)

            # Spinboxes
            spins = state.get("spinboxes", {})
            for name, val in spins.items():
                w = getattr(self, name, None)
                if isinstance(w, QSpinBox) and w.value() != int(val):
                    w.setValue(int(val))

            # Active Page
            page = state.get("active_page", "")
            if page and page in self.pages:
                self.switch_page(page)

            # Bot Status & Mode
            bot_st = state.get("bot_status", "Ready")
            self.status.setText(bot_st)

            # Logs backlog
            logs = state.get("logs", [])
            if logs and self.log_textbox.toPlainText().strip() == "":
                self.log_textbox.setPlainText("\n".join(logs))

            # ADB & Emulator telemetry
            adb_ok = state.get("adb_connected", False)
            adb_tgt = state.get("adb_target", "")
            emu_type = state.get("configured_emulator", "")
            emu_port = state.get("configured_port", "")
            emu_running = state.get("emulator_running", False)
            self._update_worker_badge(adb_ok, adb_tgt, emu_running, f"{emu_type} ({emu_port})")

        finally:
            self._is_syncing = False

    def _on_widget_updated(self, w_type: str, name: str, value: Any):
        """Receive individual widget update from Host."""
        self._is_syncing = True
        try:
            w = getattr(self, name, None)
            if w_type == "checkbox" and isinstance(w, QCheckBox):
                w.setChecked(bool(value))
            elif w_type == "combobox" and isinstance(w, QComboBox):
                w.setCurrentText(str(value))
            elif w_type == "spinbox" and isinstance(w, QSpinBox):
                w.setValue(int(value))
        finally:
            self._is_syncing = False

    def _on_remote_page_switched(self, page_name: str, page_idx: int):
        """Server changed page."""
        self._is_syncing = True
        try:
            self.switch_page(page_name)
        finally:
            self._is_syncing = False

    def _update_worker_badge(self, adb_connected: bool, adb_target: str, emu_running: bool, emu_name: str):
        """Update top and bottom telemetry badges."""
        # Bottom Badges
        if adb_connected:
            self.adb_badge.setText(f"ADB: Connected ({adb_target or 'Active'})")
            self.adb_badge.setStyleSheet("""
                background-color: rgba(16, 185, 129, 0.15);
                color: #34D399;
                border: 1px solid #10B981;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            """)
        else:
            self.adb_badge.setText("ADB: Disconnected")
            self.adb_badge.setStyleSheet("""
                background-color: rgba(239, 68, 68, 0.15);
                color: #F87171;
                border: 1px solid #EF4444;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            """)

        if emu_running:
            self.emu_badge.setText(f"Emulator: {emu_name or 'Active'}")
            self.emu_badge.setStyleSheet("""
                background-color: rgba(139, 85, 246, 0.15);
                color: #A78BFA;
                border: 1px solid #8B55F6;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            """)
        else:
            self.emu_badge.setText("Emulator: Offline")
            self.emu_badge.setStyleSheet("""
                background-color: rgba(100, 116, 139, 0.15);
                color: #94A3B8;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            """)

        # Title Bar Badge
        if self.bridge and self.bridge.is_connected():
            info = f" • Connected"
            if emu_name and emu_name.strip():
                info += f" | {emu_name}"
            elif adb_connected:
                info += f" | ADB ({adb_target})"
            self.title_bar.conn_badge.setText(f"🟢{info}")
            self.title_bar.conn_badge.setStyleSheet(
                "color: #10B981; font-weight: bold; font-size: 11px; margin-left: 10px;"
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RemoteMainWindow()
    window.show()
    sys.exit(app.exec())
