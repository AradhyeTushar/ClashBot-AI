# -*- coding: utf-8 -*-
"""
ClashBot AI - Autonomous Game Intelligence and Automation Platform
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Module: activation_window
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar. All rights reserved.

Free & Open Source Edition:
Provides the splash and license dialog interface. In this edition, all licenses
are treated as lifetime community tier, auto-validating and launching immediately.
"""

import os
import sys
import re
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtCore import Qt, Signal, QTimer, QSize, QPointF, QEvent
from PySide6.QtGui import QIcon, QPixmap, QFont, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QMessageBox, QFrame, QToolButton
)

try:
    from ui.branding_patch import apply_branding_patches
    apply_branding_patches()
except Exception:
    pass

from license_manager import (
    load_saved_key, save_key, validate_license_details,
    save_license_meta, resolve_writable_path
)


def is_frozen() -> bool:
    """Check if app is running in a frozen bundle (PyInstaller/Nuitka)."""
    return getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")


def resolve_resource_path(relative_path: str) -> str:
    """Resolve file path to bundled or source asset."""
    base_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate = os.path.join(base_src, relative_path)
    if os.path.exists(candidate):
        return os.path.abspath(candidate)
    
    project_root = os.path.dirname(base_src)
    candidate_root = os.path.join(project_root, relative_path)
    if os.path.exists(candidate_root):
        return os.path.abspath(candidate_root)
        
    return os.path.abspath(candidate)


def get_app_icon() -> QIcon:
    """Retrieve ClashBot AI application icon."""
    for filename in ("icon.ico", "icon.png"):
        path = resolve_resource_path(os.path.join("assets", filename))
        if os.path.exists(path):
            return QIcon(path)
    return QIcon()


BOT_CONFIG_PATH = Path(resolve_writable_path("bot.config"))


def _load_bot_config() -> Dict[str, Any]:
    """Load configuration dictionary from bot.config."""
    try:
        if BOT_CONFIG_PATH.exists():
            return json.loads(BOT_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_bot_config(config: Dict[str, Any]) -> None:
    """Save configuration dictionary to bot.config."""
    try:
        BOT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        BOT_CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    except Exception:
        pass


def _make_mono_close_icon() -> QIcon:
    """Generate monochrome close icon for frameless titlebar."""
    pix = QPixmap(16, 16)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor("#A0AEC0"), 1.5)
    painter.setPen(pen)
    painter.drawLine(4, 4, 12, 12)
    painter.drawLine(12, 4, 4, 12)
    painter.end()
    return QIcon(pix)


class LicenseSplash(QDialog):
    """
    License activation and splash dialog for ClashBot AI.
    In the Free & Open Source Edition, validation succeeds automatically and immediately.
    """

    validation_ready = Signal(dict)
    _KEY_GROUPS = 5

    def __init__(self, auto_activate: bool = False, parent=None):
        super().__init__(parent)
        self._auto_activate = auto_activate
        self._formatting_key = False
        self._drag_offset = None
        self._validation_thread = None

        bot_cfg = _load_bot_config()
        self.launch_mini_ui = bool(bot_cfg.get("launch_mini_ui", False))

        self.setWindowTitle("ClashBot AI - License Verification")
        self.setWindowIcon(get_app_icon())
        self.setFixedSize(480, 290)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self._setup_ui()

        # Apply saved license key
        saved_key = load_saved_key()
        self.key_input.setText(saved_key)

    def _setup_ui(self) -> None:
        """Construct the splash UI."""
        self.setStyleSheet("""
            QDialog {
                background-color: #12141A;
                border: 1px solid #2D3748;
                border-radius: 8px;
            }
            QLabel {
                color: #E2E8F0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLineEdit {
                background-color: #1A202C;
                color: #63B3ED;
                border: 1px solid #4A5568;
                border-radius: 6px;
                padding: 8px 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QLineEdit:focus {
                border: 1px solid #63B3ED;
            }
            QPushButton {
                background-color: #3182CE;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2B6CB0;
            }
            QPushButton:pressed {
                background-color: #2C5282;
            }
            QCheckBox {
                color: #A0AEC0;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(14)

        # Title bar
        self._top_bar = QFrame(self)
        top_layout = QHBoxLayout(self._top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)

        self.titlebar_logo = QLabel(self._top_bar)
        icon_pix = get_app_icon().pixmap(24, 24)
        if not icon_pix.isNull():
            self.titlebar_logo.setPixmap(icon_pix)
        top_layout.addWidget(self.titlebar_logo)

        self.titlebar_title = QLabel("ClashBot AI — Autonomous Intelligence", self._top_bar)
        self.titlebar_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #EDF2F7;")
        top_layout.addWidget(self.titlebar_title)
        top_layout.addStretch()

        close_btn = QToolButton(self._top_bar)
        close_btn.setIcon(_make_mono_close_icon())
        close_btn.setStyleSheet("border: none; background: transparent; padding: 4px;")
        close_btn.clicked.connect(self.reject)
        top_layout.addWidget(close_btn)

        layout.addWidget(self._top_bar)

        # Separator
        line = QFrame(self)
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #2D3748; max-height: 1px;")
        layout.addWidget(line)

        # Status info
        status_layout = QHBoxLayout()
        badge_label = QLabel("STATUS: LIFETIME COMMUNITY EDITION (ACTIVE)", self)
        badge_label.setStyleSheet("color: #48BB78; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
        status_layout.addWidget(badge_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        # Key Input Label & Field
        key_label = QLabel("License / Product Key:", self)
        key_label.setStyleSheet("color: #CBD5E0; font-size: 12px;")
        layout.addWidget(key_label)

        self.key_input = QLineEdit(self)
        self.key_input.textChanged.connect(self._on_key_changed)
        layout.addWidget(self.key_input)

        # Mini UI Checkbox
        self.mini_ui_checkbox = QCheckBox("Launch in Compact Mini-UI mode", self)
        self.mini_ui_checkbox.setChecked(self.launch_mini_ui)
        self.mini_ui_checkbox.toggled.connect(self._on_mini_ui_toggled)
        layout.addWidget(self.mini_ui_checkbox)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.activate_btn = QPushButton("Launch Bot Engine", self)
        self.activate_btn.clicked.connect(self._on_activate_clicked)
        btn_layout.addWidget(self.activate_btn)

        layout.addLayout(btn_layout)

    def _on_mini_ui_toggled(self, checked: bool) -> None:
        self.launch_mini_ui = checked
        cfg = _load_bot_config()
        cfg["launch_mini_ui"] = checked
        _save_bot_config(cfg)

    def _on_key_changed(self, text: str) -> None:
        pass

    def _apply_key_format(self, text: str) -> str:
        return text.strip().upper()

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Validation Error", message)

    def _show_warning(self, message: str) -> None:
        QMessageBox.warning(self, "Validation Warning", message)

    def _on_activate_clicked(self) -> None:
        key = self.key_input.text().strip() or load_saved_key()
        save_key(key)
        result = validate_license_details(key)
        self._on_validation_result(result)

    def _on_validation_result(self, result: Dict[str, Any]) -> None:
        save_license_meta(result)
        self.validation_ready.emit(result)
        self.accept()

    def showEvent(self, event: QEvent) -> None:
        super().showEvent(event)
        if self._auto_activate:
            QTimer.singleShot(10, self._auto_accept_flow)

    def _auto_accept_flow(self) -> None:
        result = validate_license_details(self.key_input.text())
        self._on_validation_result(result)

    def exec(self) -> int:
        """
        Execute dialog. In Free/Unlocked mode, auto-activates and returns
        Accepted immediately without modal blocking.
        """
        result = validate_license_details(load_saved_key())
        save_license_meta(result)
        self.validation_ready.emit(result)
        self.setResult(QDialog.Accepted)
        return QDialog.Accepted

    def exec_(self) -> int:
        """Qt compatibility alias for exec."""
        return self.exec()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
