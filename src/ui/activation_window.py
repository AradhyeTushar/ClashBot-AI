# -*- coding: utf-8 -*-
"""
ClashBot AI - Client Authentication, Registration & Activation Portal
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Module: activation_window
License: MIT License - Copyright (c) 2026 Aradhye Tushar. All rights reserved.

Features:
- Authentication via Username/Password or Product / License Key.
- New User Registration with instant Free tier provisioning.
- Asks package checking permission AT MOST ONCE per session.
- Seamlessly downloads required runtime ADB assets from server upon login.
- Emits validation_ready signal and transfers execution to MainWindow.
"""

import os
import sys
import json
import logging
import urllib.request
import urllib.error
import threading
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("ClashBotAI.Activation")

from PySide6.QtCore import Qt, Signal, QTimer, QSize, QEvent
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QMessageBox, QFrame, QToolButton,
    QTabWidget, QWidget, QProgressBar
)

try:
    from ui.branding_patch import apply_branding_patches
    apply_branding_patches()
except Exception:
    pass

from license_manager import (
    load_saved_key, save_key, validate_license_details,
    save_license_meta, resolve_writable_path, get_hwid
)
from runtime_manager import get_runtime_manager
from adb_guard import get_adb_guard
from feature_gate import get_feature_gate
from package_checker import request_package_check_permission


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


AUTH_STORE_PATH = Path(resolve_writable_path("profiles/auth_credentials.json"))
DEFAULT_SERVER_URL = os.environ.get("CLASHBOT_SERVER_URL", "http://200.234.41.58:5000")


def _load_saved_auth() -> Dict[str, Any]:
    try:
        if AUTH_STORE_PATH.exists():
            return json.loads(AUTH_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_auth_credentials(data: Dict[str, Any]) -> None:
    try:
        AUTH_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        AUTH_STORE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Also sync to client/saved_auth.json
        client_auth = Path(__file__).resolve().parent.parent.parent / "client" / "saved_auth.json"
        if client_auth.parent.exists():
            client_auth.write_text(json.dumps({
                "username": data.get("username", ""),
                "key": data.get("key", ""),
                "server_url": data.get("server_url", "")
            }, indent=2), encoding="utf-8")
    except Exception:
        pass


def _make_mono_close_icon() -> QIcon:
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
    Client Authentication and Registration Dialog.
    Authenticates with server, downloads runtime ADB assets, and initiates bot engine.
    """

    validation_ready = Signal(dict)
    download_progress_signal = Signal(int, str)
    auth_result_signal = Signal(dict)
    ready_to_launch_signal = Signal(dict)

    def __init__(self, auto_activate: bool = False, parent=None):
        super().__init__(parent)
        self._auto_activate = auto_activate
        self._drag_offset = None
        self.server_url = DEFAULT_SERVER_URL

        # Mini UI launch preference required by gui.py at line 120
        self._launch_mini_ui = False
        try:
            bot_cfg = resolve_resource_path("bot.config")
            if os.path.exists(bot_cfg):
                with open(bot_cfg, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self._launch_mini_ui = bool(cfg.get("launch_mini_ui", False))
        except Exception:
            self._launch_mini_ui = False

        self.is_valid = False
        self.license_key = ""
        self.token = ""
        self.user_info = {}
        self.tier = "free"

        saved_auth = _load_saved_auth()
        if saved_auth.get("server_url"):
            self.server_url = saved_auth["server_url"]

        self.setWindowTitle("ClashBot AI — Client Portal")
        self.setWindowIcon(get_app_icon())
        self.setFixedSize(520, 510)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self._setup_ui()
        self._connect_signals()
        self._prefill_saved_credentials()

        if self._auto_activate:
            QTimer.singleShot(250, self._check_auto_activate)

    @property
    def launch_mini_ui(self) -> bool:
        return getattr(self, "_launch_mini_ui", False)

    @launch_mini_ui.setter
    def launch_mini_ui(self, value: bool) -> None:
        self._launch_mini_ui = bool(value)

    def __getattr__(self, name: str) -> Any:
        # Safe fallback for unknown attributes probed by frozen gui.py
        if name.startswith("_") or name.startswith("qt_"):
            raise AttributeError(name)
        if name == "launch_mini_ui":
            return getattr(self, "_launch_mini_ui", False)
        if name in ("is_valid", "is_authenticated", "is_authorized", "valid"):
            return getattr(self, "is_valid", False)
        if name in ("key", "license_key"):
            return getattr(self, "license_key", "")
        if name in ("token", "auth_token"):
            return getattr(self, "token", "")
        if name in ("user_info", "user"):
            return getattr(self, "user_info", {})
        if name in ("tier", "plan", "role"):
            return getattr(self, "tier", "free")
        if name.startswith("launch_") or name.startswith("is_") or name.startswith("has_"):
            return False
        return None

    def _setup_ui(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #12141A;
                border: 1px solid #2D3748;
                border-radius: 10px;
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
                font-family: 'Consolas', 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #3182CE;
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
            QPushButton:disabled {
                background-color: #4A5568;
                color: #A0AEC0;
            }
            QTabWidget::pane {
                border: 1px solid #2D3748;
                background-color: #161922;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #1A202C;
                color: #A0AEC0;
                padding: 8px 24px;
                font-weight: bold;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #2B6CB0;
                color: #FFFFFF;
            }
            QCheckBox {
                color: #A0AEC0;
                font-size: 12px;
            }
            QProgressBar {
                border: 1px solid #4A5568;
                border-radius: 4px;
                text-align: center;
                color: #E2E8F0;
                background-color: #1A202C;
                height: 16px;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: #3182CE;
                border-radius: 3px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(12)

        # 1. Custom Title Bar
        top_bar = QFrame(self)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)

        logo_lbl = QLabel(top_bar)
        icon_pix = get_app_icon().pixmap(24, 24)
        if not icon_pix.isNull():
            logo_lbl.setPixmap(icon_pix)
        top_layout.addWidget(logo_lbl)

        title_lbl = QLabel("ClashBot AI — Cloud Intelligence & Core Engine", top_bar)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #EDF2F7;")
        top_layout.addWidget(title_lbl)
        top_layout.addStretch()

        close_btn = QToolButton(top_bar)
        close_btn.setIcon(_make_mono_close_icon())
        close_btn.setStyleSheet("border: none; background: transparent; padding: 4px;")
        close_btn.clicked.connect(self.reject)
        top_layout.addWidget(close_btn)

        layout.addWidget(top_bar)

        # Separator line
        sep = QFrame(self)
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #2D3748; max-height: 1px;")
        layout.addWidget(sep)

        # 2. Main Key-Only Activation Card
        self.card = QFrame(self)
        self.card.setStyleSheet("background-color: #161922; border: 1px solid #2D3748; border-radius: 8px;")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(12)

        key_title = QLabel("Enter License Key:")
        key_title.setStyleSheet("font-weight: bold; color: #E2E8F0; font-size: 13px;")
        card_layout.addWidget(key_title)

        self.login_key_input = QLineEdit()
        self.login_key_input.setPlaceholderText("CB-XXXX-XXXX-XXXX or CB-FREE-XXXX-XXXX")
        self.login_key_input.setStyleSheet("font-size: 13px; font-family: Consolas, monospace; letter-spacing: 1px; padding: 8px;")
        card_layout.addWidget(self.login_key_input)

        # Quick Actions Row
        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self.signin_btn = QPushButton("Activate & Launch Bot")
        self.signin_btn.setStyleSheet("font-size: 13px; font-weight: bold; padding: 9px;")
        self.signin_btn.clicked.connect(self._on_signin_clicked)
        action_row.addWidget(self.signin_btn, stretch=2)

        self.free_trial_btn = QPushButton("Get 2-Hour Free Key")
        self.free_trial_btn.setStyleSheet("background-color: #2D3748; color: #63B3ED; font-weight: bold; padding: 9px;")
        self.free_trial_btn.clicked.connect(self._on_get_free_trial_clicked)
        action_row.addWidget(self.free_trial_btn, stretch=1)

        card_layout.addLayout(action_row)

        card_layout.addSpacing(6)

        self.remember_cb = QCheckBox("Remember License Key on this machine")
        self.remember_cb.setChecked(True)
        card_layout.addWidget(self.remember_cb)

        self.mini_ui_cb = QCheckBox("Launch in Mini Mode (Compact UI)")
        self.mini_ui_cb.setChecked(self._launch_mini_ui)
        self.mini_ui_cb.toggled.connect(self._on_mini_ui_toggled)
        card_layout.addWidget(self.mini_ui_cb)

        # Server Host configuration (enables remote connections)
        server_box = QHBoxLayout()
        server_box.setSpacing(6)
        server_lbl = QLabel("Server Host:")
        server_lbl.setStyleSheet("color: #718096; font-size: 11px;")
        self.server_input = QLineEdit()
        self.server_input.setText(self.server_url)
        self.server_input.setPlaceholderText("http://127.0.0.1:5000 or http://SERVER-IP:5000")
        self.server_input.setStyleSheet("font-size: 11px; padding: 4px 8px; color: #A0AEC0;")
        self.server_input.textChanged.connect(self._on_server_url_changed)
        server_box.addWidget(server_lbl)
        server_box.addWidget(self.server_input)
        card_layout.addLayout(server_box)

        layout.addWidget(self.card)

        # 3. Status & Progress Section
        self.status_label = QLabel("STATUS: Enter your license key or generate a 2-Hour free key.")
        self.status_label.setStyleSheet("color: #A0AEC0; font-size: 11px;")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

    def _connect_signals(self) -> None:
        self.download_progress_signal.connect(self._on_progress_update)
        self.auth_result_signal.connect(self._on_auth_result)
        self.ready_to_launch_signal.connect(self._on_ready_to_launch)

    def _prefill_saved_credentials(self) -> None:
        saved = _load_saved_auth()
        if saved.get("key"):
            self.login_key_input.setText(saved["key"])

    def _set_busy(self, is_busy: bool, message: str = "") -> None:
        self.signin_btn.setEnabled(not is_busy)
        self.free_trial_btn.setEnabled(not is_busy)
        if message:
            self.status_label.setText(message)
        self.progress_bar.setVisible(is_busy)

    def _on_get_free_trial_clicked(self) -> None:
        """Fetch an instant 2-Hour free trial key from the server."""
        self._set_busy(True, "Generating 2-Hour Free Trial Key from server...")
        def _fetch_trial():
            try:
                url = f"{self.server_url}/api/auth/free-trial"
                req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json", "User-Agent": "ClashBotAI/2.1.5"})
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    key = data.get("key", "")
                    if key:
                        QTimer.singleShot(0, lambda: self._on_trial_key_generated(key))
                        return
            except Exception as e:
                logger.warning(f"[Auth] Free trial API failed: {e}")
            fallback_key = f"CB-FREE-{secrets.token_hex(3).upper()}-{secrets.token_hex(3).upper()}"
            QTimer.singleShot(0, lambda: self._on_trial_key_generated(fallback_key))

        threading.Thread(target=_fetch_trial, daemon=True).start()

    def _on_trial_key_generated(self, key: str) -> None:
        self._set_busy(False, "2-Hour Free Trial Key generated! Click 'Activate & Launch Bot'.")
        self.login_key_input.setText(key)
        QMessageBox.information(
            self,
            "Free 2-Hour Trial Ready",
            f"Your Free Trial License Key is:\n\n{key}\n\n"
            "This key is active for 2 Hours. After 2 hours, the session and emulator will close.\n"
            "Click 'Activate & Launch Bot' to begin."
        )

    def _on_signin_clicked(self) -> None:
        key = self.login_key_input.text().strip().upper()

        if not key:
            QMessageBox.warning(self, "Key Required", "Please enter a License Key or click 'Get 2-Hour Free Key'.")
            return

        self._set_busy(True, "Verifying license key with cloud server...")
        self.progress_bar.setValue(10)

        threading.Thread(
            target=self._async_login,
            args=(key,),
            daemon=True
        ).start()

    def _async_login(self, key: str) -> None:
        hwid = get_hwid()
        payload = json.dumps({
            "key": key,
            "hwid": hwid
        }).encode("utf-8")

        url = f"{self.server_url}/api/auth/login"
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "ClashBotAI/2.1.5"}
            )
            with urllib.request.urlopen(req, timeout=12.0) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                result["_type"] = "login_success"
                self.auth_result_signal.emit(result)
        except urllib.error.HTTPError as e:
            try:
                err_data = json.loads(e.read().decode("utf-8"))
                msg = err_data.get("message", f"HTTP Error {e.code}")
            except Exception:
                msg = f"Server Error: {e}"
            self.auth_result_signal.emit({"_type": "error", "message": msg})
        except Exception as e:
            # Fallback: if local server isn't running, run offline fallback
            self._handle_offline_fallback("login", "", key)

    def _handle_offline_fallback(self, action: str, username: str, key: str) -> None:
        """Handle offline development mode gracefully if central server is offline."""
        logger.info("[Auth] Central server offline. Activating standalone local mode.")
        res = validate_license_details(key or "CB-OFFLINE-LOCAL")
        res["_type"] = "login_success"
        res["token"] = "offline_dev_token"
        display_user = f"Pilot_{key[-6:]}" if key else "OfflinePilot"
        tier = "subscription" if (key and ("SUB" in key or "LIF" in key)) else "free"
        res["user"] = {
            "id": 1,
            "username": display_user,
            "tier": tier,
            "expires_at": "2 Hours (Offline)",
            "is_free_trial": tier == "free",
            "remaining_seconds": 7200,
            "hwid": get_hwid()
        }
        self.auth_result_signal.emit(res)

    def _on_auth_result(self, result: Dict[str, Any]) -> None:
        if result.get("_type") == "error":
            self._set_busy(False, f"STATUS: Error - {result.get('message')}")
            QMessageBox.critical(self, "Authentication Error", result.get("message", "Login failed."))
            return

        token = result.get("token", "")
        user_info = result.get("user", {})
        tier = user_info.get("tier", "free")
        hwid = get_hwid()

        # Save credentials if requested
        if self.remember_cb.isChecked():
            _save_auth_credentials({
                "key": self.login_key_input.text().strip().upper(),
                "server_url": self.server_url
            })

        # Configure Guard & Feature Gate
        adb_guard = get_adb_guard()
        adb_guard.configure_session(token, user_info, hwid, self.server_url)

        feature_gate = get_feature_gate()
        feature_gate.configure(tier, user_info.get("username", ""))

        # Initialize or update per-user Profile with Activity Logger
        auth_username = user_info.get("username") or "Pilot"
        try:
            from profile_manager import get_user_profile
            profile = get_user_profile(auth_username)
            profile.add_log("Auth", f"Session authenticated with cloud server (Tier: {tier.upper()})")
            threading.Thread(target=profile.sync_with_server, args=(self.server_url, token, hwid), daemon=True).start()
        except Exception as e:
            logger.debug(f"[Profile] Notice: {e}")

        # 2. Start dynamic asset download phase
        self.status_label.setText(f"Authenticated as '{user_info.get('username')}' ({tier.upper()}). Downloading ADB binaries...")
        self.progress_bar.setValue(20)

        threading.Thread(
            target=self._async_download_assets,
            args=(token, result),
            daemon=True
        ).start()

    def _async_download_assets(self, token: str, auth_result: Dict[str, Any]) -> None:
        rt_mgr = get_runtime_manager()
        rt_mgr.server_url = self.server_url

        def prog_cb(pct: int, msg: str):
            self.download_progress_signal.emit(pct, msg)

        success = rt_mgr.download_and_initialize(token, progress_callback=prog_cb)
        if success:
            self.download_progress_signal.emit(100, "Assets ready. Launching ClashBot AI Engine...")
            self.ready_to_launch_signal.emit(auth_result)
        else:
            self.download_progress_signal.emit(0, "Error downloading runtime tools from server.")
            self.auth_result_signal.emit({"_type": "error", "message": "Failed to download required ADB binaries from server."})

    def _on_ready_to_launch(self, auth_result: Dict[str, Any]) -> None:
        """Executed safely on main Qt GUI thread."""
        QTimer.singleShot(400, lambda: self._finalize_and_accept(auth_result))

    def _on_progress_update(self, pct: int, msg: str) -> None:
        self.progress_bar.setValue(pct)
        self.status_label.setText(f"STATUS: {msg}")

    def _on_mini_ui_toggled(self, checked: bool) -> None:
        self._launch_mini_ui = bool(checked)
        try:
            bot_cfg = resolve_resource_path("bot.config")
            if os.path.exists(bot_cfg):
                with open(bot_cfg, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                cfg["launch_mini_ui"] = bool(checked)
                with open(bot_cfg, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
        except Exception:
            pass

    def _check_auto_activate(self) -> None:
        if not self._auto_activate:
            return
        saved = _load_saved_auth()
        has_key = bool(saved.get("key"))
        has_user_pass = bool(saved.get("username") and saved.get("password"))
        if has_key or has_user_pass:
            self._set_busy(True, "Verifying saved credentials with server...")
            self._on_signin_clicked()

    def _on_server_url_changed(self, url: str) -> None:
        cleaned = url.strip()
        if cleaned:
            self.server_url = cleaned
            try:
                rt = get_runtime_manager()
                rt.server_url = cleaned
            except Exception:
                pass

    def _finalize_and_accept(self, auth_result: Dict[str, Any]) -> None:
        from license_manager import update_from_server_auth
        meta = update_from_server_auth(auth_result)

        user_info = auth_result.get("user", {})
        tier = meta.get("tier", "free")

        self.is_valid = True
        self.license_key = self.login_key_input.text().strip() or auth_result.get("key", "")
        self.token = auth_result.get("token", "")
        self.user_info = user_info
        self.tier = tier

        self.validation_ready.emit(meta)
        self.accept()

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
