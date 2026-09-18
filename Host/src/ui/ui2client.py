# -*- coding: utf-8 -*-
"""
ClashBot AI - Host UI to Remote Client Bridge (ui2client)
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar. All rights reserved.

This module acts as a high-speed local IPC/socket server in the Host UI,
enabling two-way real-time communication with the Remote Client.
Actions from the Remote Client (clicks, page switches, checkbox toggles, start/stop)
are dispatched directly and safely onto Host UI widgets on Qt's main GUI thread,
providing immediate visual click feedback on the Host UI window.
"""

import os
import sys
import json
import base64
import asyncio
import websockets
import threading
import traceback
from typing import Optional, Dict, Any, List

from PySide6.QtCore import QTimer, QMetaObject, Qt, QObject, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QPushButton, QToolButton, QCheckBox, QRadioButton,
    QLineEdit, QComboBox, QSpinBox, QSlider, QTextEdit, QLabel
)

HOST_PORT = 29170
HOST_IP = os.environ.get("CLASHBOT_HOST_IP", "0.0.0.0")

_ws_loop: Optional[asyncio.AbstractEventLoop] = None
_server_thread: Optional[threading.Thread] = None
_server_running = False

_clients_lock = threading.Lock()
_connected_clients: set = set()

_host_window: Optional[Any] = None
_is_updating_from_remote = False
_log_buffer: List[str] = []
_MAX_LOG_BUFFER = 200
_latest_client_frame: Optional[bytes] = None

# Mapping of page names to their indices or attributes
PAGE_NAMES = [
    "General", "Attack Army", "Multi Village", "Builder Base",
    "Clan Capital", "Upgrades/Research", "XP Farming", "Extra Modes",
    "Bot Runtime", "Statistics", "Log"
]

# Track connected widget signals to avoid duplicate connections
_hooked_widgets = set()


class HostBridgeDispatcher(QObject):
    """Qt Object to bridge worker thread actions to Qt main GUI thread."""
    dispatch_action = Signal(dict)

    @Slot(dict)
    def on_dispatch(self, action_data: dict) -> None:
        try:
            execute_remote_action_on_gui_thread(action_data)
        except Exception as e:
            print(f"[ui2client] Error in on_dispatch: {e}")

_dispatcher = HostBridgeDispatcher()


def _json_serialize(data: Dict[str, Any]) -> bytes:
    """Encode dictionary as newline-delimited UTF-8 JSON bytes."""
    return (json.dumps(data, ensure_ascii=False) + "\n").encode("utf-8")


async def _broadcast_async(raw: str) -> None:
    if _connected_clients:
        websockets.broadcast(_connected_clients, raw)

def broadcast(message_dict: Dict[str, Any]) -> None:
    """Send a message to all connected Remote Clients."""
    raw = _json_serialize(message_dict).decode('utf-8')
    global _ws_loop
    if _ws_loop and _ws_loop.is_running():
        asyncio.run_coroutine_threadsafe(_broadcast_async(raw), _ws_loop)


def broadcast_log(text: str) -> None:
    """Send live console log line to all connected Remote Clients."""
    if not isinstance(text, str):
        text = str(text)
    
    # Store in memory buffer for new clients
    _log_buffer.append(text)
    if len(_log_buffer) > _MAX_LOG_BUFFER:
        _log_buffer.pop(0)

    broadcast({
        "type": "log",
        "text": text
    })


def broadcast_title(title: str) -> None:
    """Send live window title to all connected Remote Clients."""
    broadcast({
        "type": "window_title",
        "title": str(title)
    })


def get_latest_client_frame() -> Optional[bytes]:
    """Retrieve the latest frame received from the Remote Client."""
    global _latest_client_frame
    return _latest_client_frame


def send_device_action(action_dict: Dict[str, Any]) -> None:
    """Send a raw device action (tap/swipe/keyevent) to the Remote Client."""
    # Tag it for the RemoteAdbWorker to pick up
    action_dict["type"] = "device_action"
    broadcast(action_dict)


def get_host_window() -> Optional[Any]:
    """Retrieve or discover active Host MainWindow."""
    global _host_window
    if _host_window is not None:
        return _host_window
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            for widget in app.topLevelWidgets():
                if "MainWindow" in type(widget).__name__:
                    bind_host_main_window(widget)
                    return widget
    except Exception:
        pass
    return None


def get_full_state_snapshot() -> Dict[str, Any]:
    """Capture complete snapshot of Host UI state."""
    state: Dict[str, Any] = {
        "type": "full_state",
        "ready": False,
        "logs": list(_log_buffer)
    }

    # ADB & Emulator Worker status (available even during startup)
    try:
        from network.adb_worker import get_adb_worker
        from network.emulator_worker import get_emulator_worker
        adb_w = get_adb_worker()
        emu_w = get_emulator_worker()
        state["adb_connected"] = adb_w.is_connected()
        state["adb_target"] = adb_w.target_device
        emu_type, inst_id, host, port = emu_w.get_configured_emulator()
        state["configured_emulator"] = emu_type
        state["configured_port"] = port
        state["emulator_running"] = emu_w.is_port_open("127.0.0.1", port)
        state["detected_emulators"] = list(emu_w.discover_installed_emulators().keys())
    except Exception:
        pass

    w = get_host_window()
    if not w:
        state["status"] = "no_window"
        return state

    state["ready"] = True
    state["window_title"] = w.windowTitle() if hasattr(w, "windowTitle") else "ClashBot AI Pro v2.1.5 | Android Device (16384)"
    state["bot_status"] = getattr(w, "_last_worker_status", "Idle")
    state["active_page"] = ""
    state["active_page_idx"] = 0
    state["settings_drawer_expanded"] = getattr(w, "settings_drawer_expanded", False)
    state["checkboxes"] = {}
    state["comboboxes"] = {}
    state["spinboxes"] = {}
    state["labels"] = {}


    try:
        if hasattr(w, "stack") and w.stack:
            state["active_page_idx"] = w.stack.currentIndex()
            if hasattr(w, "pages") and isinstance(w.pages, dict):
                cur_widget = w.stack.currentWidget()
                for name, page_widget in w.pages.items():
                    if page_widget == cur_widget:
                        state["active_page"] = name
                        break

        # Checkboxes
        for cb_attr in [
            "farming_enabled", "upgrade_walls", "request_donations", "wait_cc_troops",
            "enable_donations", "end_on_stars", "collect_collectors", "start_helpers",
            "collect_cart", "clear_tombs", "remove_obstacles", "collect_achievements",
            "collect_cc_loot", "claim_weekly_deal", "hero_tap_delay_enabled",
            "air_troop_width_enabled", "multi_enabled", "use_root_profile_swap",
            "builder_enabled", "builder_end_after_drop", "builderbase_upgrade_walls",
            "builder_collect_resources_first_run", "builder_collect_gem_mine",
            "builder_collect_star_bonus", "bb_remove_obstacles",
            "clan_capital_enable", "clan_capital_dump_gold_treasury_if_full",
            "home_upgrade_enabled", "home_upgrade_perform_suggested",
            "home_save_1_builder", "home_upgrade_suggested_ignore_townhall",
            "home_upgrade_suggested_rotate", "home_research_enabled",
            "home_research_perform_suggested", "home_research_use_1_gem_helper",
            "home_research_suggested_rotate", "home_research_pets", "home_rush_th",
            "bb_upgrade_enabled", "bb_upgrade_perform_suggested", "bb_save_1_builder",
            "bb_upgrade_suggested_rotate", "bb_research_enabled",
            "bb_research_perform_suggested", "bb_research_suggested_rotate",
            "donate_only_enabled", "donate_only_speed_mode", "request_leave_enabled",
            "request_leave_join", "request_leave_leave", "request_leave_wait_cooldown",
            "request_leave_set_army_slot1", "clan_games_enable", "cg_troop_challenges",
            "cg_claim_rewards_for_gems", "war_attacks_enabled", "war_request_cc",
            "war_wait_cc", "war_one_attack_per_session", "rank_first",
            "ranked_request_donations", "ranked_wait_cc_troops",
            "bot_end_condition_enabled", "active_hours_enabled", "humanized_breaks_enabled"
        ]:
            if hasattr(w, cb_attr):
                cb = getattr(w, cb_attr)
                if isinstance(cb, QCheckBox):
                    state["checkboxes"][cb_attr] = cb.isChecked()

        # Comboboxes
        for cmb_attr in [
            "strategy", "army_slot", "target_stars", "wall_stop_level",
            "builder_army_troop", "builder_return_policy", "builder_target_stars",
            "clan_capital_troop", "home_research_pet_target", "war_mode",
            "ranked_army_slot", "ranked_strategy", "bot_end_condition_type",
            "emulator_select", "emulator_instance_select", "start_profile"
        ]:
            if hasattr(w, cmb_attr):
                cmb = getattr(w, cmb_attr)
                if isinstance(cmb, QComboBox):
                    state["comboboxes"][cmb_attr] = {
                        "currentText": cmb.currentText(),
                        "currentIndex": cmb.currentIndex(),
                        "items": [cmb.itemText(i) for i in range(cmb.count())]
                    }

        # Spinboxes
        for sb_attr in [
            "attack_gold", "attack_elixir", "attack_dark",
            "hero_tap_delay_seconds", "air_troop_width", "village_count",
            "switch_minutes", "builder_max_attacks", "bot_end_time_minutes",
            "humanized_run_min", "humanized_run_max",
            "humanized_break_min", "humanized_break_max"
        ]:
            if hasattr(w, sb_attr):
                sb = getattr(w, sb_attr)
                if isinstance(sb, QSpinBox):
                    state["spinboxes"][sb_attr] = sb.value()

        # Labels / Status
        if hasattr(w, "status") and isinstance(w.status, QLabel):
            state["labels"]["status"] = w.status.text()
        if hasattr(w, "key_status_label") and isinstance(w.key_status_label, QLabel):
            state["labels"]["key_status"] = w.key_status_label.text()
        if hasattr(w, "mode_label") and isinstance(w.mode_label, QLabel):
            state["labels"]["mode"] = w.mode_label.text()

        # Buttons states
        state["start_enabled"] = getattr(w, "start_btn", None) and w.start_btn.isEnabled()
        state["stop_enabled"] = getattr(w, "stop_btn", None) and w.stop_btn.isEnabled()
        state["pause_enabled"] = getattr(w, "pause_btn", None) and w.pause_btn.isEnabled()

        # ADB & Emulator Worker status
        try:
            from network.adb_worker import get_adb_worker
            from network.emulator_worker import get_emulator_worker
            adb_w = get_adb_worker()
            state["adb_connected"] = adb_w.is_connected()
            state["adb_target"] = adb_w.target_device
            state["detected_emulators"] = list(get_emulator_worker().discover_installed_emulators().keys())
        except Exception:
            pass

    except Exception as e:
        state["error"] = str(e)

    return state


def _on_host_checkbox_toggled(attr_name: str, checked: bool) -> None:
    """Callback when a checkbox is toggled on Host UI directly."""
    global _is_updating_from_remote
    if _is_updating_from_remote:
        return
    broadcast({
        "type": "widget_update",
        "widget_type": "checkbox",
        "name": attr_name,
        "value": checked
    })


def _on_host_combobox_changed(attr_name: str, text: str) -> None:
    """Callback when a combobox is changed on Host UI directly."""
    global _is_updating_from_remote
    if _is_updating_from_remote:
        return
    broadcast({
        "type": "widget_update",
        "widget_type": "combobox",
        "name": attr_name,
        "value": text
    })


def _on_host_spinbox_changed(attr_name: str, val: int) -> None:
    """Callback when a spinbox is changed on Host UI directly."""
    global _is_updating_from_remote
    if _is_updating_from_remote:
        return
    broadcast({
        "type": "widget_update",
        "widget_type": "spinbox",
        "name": attr_name,
        "value": val
    })


def _on_host_page_switched(index: int) -> None:
    """Callback when the page is switched on Host UI directly."""
    global _is_updating_from_remote, _host_window
    if _is_updating_from_remote or not _host_window:
        return
    page_name = ""
    if hasattr(_host_window, "pages") and isinstance(_host_window.pages, dict):
        cur = _host_window.stack.currentWidget()
        for k, v in _host_window.pages.items():
            if v == cur:
                page_name = k
                break
    broadcast({
        "type": "page_switched",
        "page_index": index,
        "page_name": page_name
    })


def bind_host_main_window(window: Any) -> None:
    """
    Binds the active Host MainWindow to the ui2client server.
    Hooks into widget signals to detect user interaction in Host UI,
    and enables remote click execution.
    """
    global _host_window, _hooked_widgets
    _host_window = window
    print(f"[ui2client] Successfully bound Host MainWindow: {window}")

    # Hook PageStack change
    if hasattr(window, "stack") and window.stack and "stack" not in _hooked_widgets:
        _hooked_widgets.add("stack")
        try:
            window.stack.currentChanged.connect(_on_host_page_switched)
        except Exception:
            pass

    # Hook Checkboxes
    for attr in dir(window):
        val = getattr(window, attr, None)
        if isinstance(val, QCheckBox) and attr not in _hooked_widgets:
            _hooked_widgets.add(attr)
            def _make_cb_hook(name=attr):
                return lambda checked: _on_host_checkbox_toggled(name, checked)
            try:
                val.toggled.connect(_make_cb_hook())
            except Exception:
                pass

        elif isinstance(val, QComboBox) and attr not in _hooked_widgets:
            _hooked_widgets.add(attr)
            def _make_cmb_hook(name=attr):
                return lambda text: _on_host_combobox_changed(name, text)
            try:
                val.currentTextChanged.connect(_make_cmb_hook())
            except Exception:
                pass

        elif isinstance(val, QSpinBox) and attr not in _hooked_widgets:
            _hooked_widgets.add(attr)
            def _make_sb_hook(name=attr):
                return lambda num: _on_host_spinbox_changed(name, num)
            try:
                val.valueChanged.connect(_make_sb_hook())
            except Exception:
                pass

    # Auto-configure and select detected emulator (e.g. MuMu Player) on Host MainWindow
    try:
        from network.emulator_worker import get_emulator_worker
        emu_w = get_emulator_worker()
        preferred, target_port = emu_w.auto_configure_installed_emulator()
        if hasattr(window, "emulator_select") and window.emulator_select:
            for i in range(window.emulator_select.count()):
                txt = window.emulator_select.itemText(i).lower()
                if preferred in txt or txt in preferred:
                    window.emulator_select.setCurrentIndex(i)
                    break
        if hasattr(window, "emulator_install_path_input") and window.emulator_install_path_input:
            discovered = emu_w.discover_installed_emulators()
            if preferred in discovered:
                p = discovered[preferred].get("path", "")
                if p and not window.emulator_install_path_input.text():
                    window.emulator_install_path_input.setText(p)
    except Exception as e:
        print(f"[ui2client] Notice: emulator auto-configuration on window: {e}")

    # Broadcast host_ready and updated full state to any currently connected clients
    broadcast({"type": "host_ready", "ready": True})
    broadcast(get_full_state_snapshot())



def execute_remote_action_on_gui_thread(action: Dict[str, Any]) -> None:
    """
    Executes a remote action safely on the Qt GUI main thread.
    Simulates clicks and updates widgets with visible visual feedback.
    """
    global _is_updating_from_remote
    w = get_host_window()
    if not w:
        # If Host window is still loading (splash screen active), retry shortly
        retries = action.get("_retry_count", 0)
        if retries < 25:
            action["_retry_count"] = retries + 1
            QTimer.singleShot(250, lambda: execute_remote_action_on_gui_thread(action))
            return
        print("[ui2client] Cannot execute action: Host MainWindow not bound yet.")
        return

    cmd = action.get("action")
    target = action.get("target")
    value = action.get("value")

    _is_updating_from_remote = True
    try:
        # 1. Switch page / Nav button click
        if cmd == "switch_page":
            page_name = target or value
            print(f"[ui2client] Remote command: switch_page -> {page_name}")
            if hasattr(w, "switch_page"):
                w.switch_page(page_name)
            # Animate the nav button if found
            if hasattr(w, "nav") and w.nav:
                for btn in w.nav.findChildren(QPushButton):
                    if btn.text().strip().lower() == str(page_name).strip().lower():
                        btn.animateClick()
                        break
            broadcast({
                "type": "page_switched",
                "page_name": page_name
            })

        # 2. Click button
        elif cmd == "click_button":
            btn_name = (target or "").lower()
            print(f"[ui2client] Remote command: click_button -> {btn_name}")

            if btn_name in ("start", "start_bot", "miniquickstart"):
                if hasattr(w, "start_bot"):
                    w.start_bot()
                if hasattr(w, "start_btn") and w.start_btn:
                    w.start_btn.animateClick()
                # Also find Start button in central widget
                for btn in w.findChildren(QPushButton):
                    if btn.text().strip().lower() == "start":
                        btn.animateClick()

            elif btn_name in ("stop", "stop_bot", "miniquickstop"):
                if hasattr(w, "stop_bot"):
                    w.stop_bot()
                if hasattr(w, "stop_btn") and w.stop_btn:
                    w.stop_btn.animateClick()
                for btn in w.findChildren(QPushButton):
                    if btn.text().strip().lower() == "stop":
                        btn.animateClick()

            elif btn_name in ("pause", "pause_bot", "miniquickpause"):
                if hasattr(w, "pause_bot"):
                    w.pause_bot()
                if hasattr(w, "pause_btn") and w.pause_btn:
                    w.pause_btn.animateClick()

            elif btn_name in ("settings", "settings_toggle", "settingstogglebtn"):
                if hasattr(w, "settings_toggle_btn") and w.settings_toggle_btn:
                    w.settings_toggle_btn.animateClick()
                elif hasattr(w, "_toggle_settings_drawer"):
                    w._toggle_settings_drawer()

            elif btn_name in ("restart_adb", "restartadbbtn"):
                if hasattr(w, "restart_adb_btn") and w.restart_adb_btn:
                    w.restart_adb_btn.animateClick()
                elif hasattr(w, "_restart_adb_server"):
                    w._restart_adb_server()
                try:
                    from network.adb_worker import get_adb_worker
                    get_adb_worker().connect()
                except Exception:
                    pass

            elif btn_name in ("launch_emulator", "start_emulator"):
                try:
                    from network.emulator_worker import get_emulator_worker
                    emu_type = str(value or "mumu").lower()
                    get_emulator_worker().launch_emulator(emu_type, wait_ready=True)
                except Exception as e:
                    print(f"[ui2client] Error launching emulator: {e}")

            elif btn_name in ("close_emulator", "stop_emulator"):
                try:
                    from network.emulator_worker import get_emulator_worker
                    emu_type = str(value or "mumu").lower()
                    get_emulator_worker().close_emulator(emu_type)
                except Exception as e:
                    print(f"[ui2client] Error closing emulator: {e}")

            elif btn_name in ("connect_adb", "adb_connect"):
                try:
                    from network.adb_worker import get_adb_worker
                    get_adb_worker().connect()
                except Exception as e:
                    print(f"[ui2client] Error connecting ADB: {e}")


            elif btn_name in ("apply_all_profiles", "apply_all_profiles_btn"):
                if hasattr(w, "apply_all_profiles_btn") and w.apply_all_profiles_btn:
                    w.apply_all_profiles_btn.animateClick()

            elif btn_name in ("backup_all_shared_prefs", "backup_all_shared_prefs_btn"):
                if hasattr(w, "backup_all_shared_prefs_btn") and w.backup_all_shared_prefs_btn:
                    w.backup_all_shared_prefs_btn.animateClick()

            elif btn_name in ("bb_clear_slots", "bb_clear_slots_btn"):
                if hasattr(w, "bb_clear_slots_btn") and w.bb_clear_slots_btn:
                    w.bb_clear_slots_btn.animateClick()

            elif btn_name in ("home_clear_slots", "home_clear_slots_btn"):
                if hasattr(w, "home_clear_slots_btn") and w.home_clear_slots_btn:
                    w.home_clear_slots_btn.animateClick()

            elif btn_name in ("account_creation_start", "account_creation_start_btn"):
                if hasattr(w, "account_creation_start_btn") and w.account_creation_start_btn:
                    w.account_creation_start_btn.animateClick()

            elif btn_name in ("account_creation_stop", "account_creation_stop_btn"):
                if hasattr(w, "account_creation_stop_btn") and w.account_creation_stop_btn:
                    w.account_creation_stop_btn.animateClick()

            else:
                # Generic button lookup by text or objectName
                found = False
                for btn in w.findChildren((QPushButton, QToolButton)):
                    if btn.objectName() == target or btn.text().strip().lower() == str(target).strip().lower():
                        btn.animateClick()
                        found = True
                        break
                if not found:
                    print(f"[ui2client] Warning: Button '{target}' not found on Host MainWindow.")

        # 3. Toggle/Set Checkbox
        elif cmd in ("toggle_checkbox", "set_checkbox"):
            cb_name = target
            checked = bool(value)
            print(f"[ui2client] Remote command: set_checkbox -> {cb_name} = {checked}")
            target_widget = getattr(w, cb_name, None)
            if isinstance(target_widget, QCheckBox):
                target_widget.setChecked(checked)
                # Also visually animate
                target_widget.animateClick() if target_widget.isChecked() != checked else None
            else:
                # Search through all checkboxes by text or name
                for cb in w.findChildren(QCheckBox):
                    if cb.objectName() == cb_name or cb.text().strip().lower() == str(cb_name).strip().lower():
                        cb.setChecked(checked)
                        break

        # 4. Set Combobox
        elif cmd == "set_combobox":
            cmb_name = target
            val_text = str(value)
            print(f"[ui2client] Remote command: set_combobox -> {cmb_name} = {val_text}")
            cmb = getattr(w, cmb_name, None)
            if isinstance(cmb, QComboBox):
                cmb.setCurrentText(val_text)
            else:
                for c in w.findChildren(QComboBox):
                    if c.objectName() == cmb_name:
                        c.setCurrentText(val_text)
                        break

        # 5. Set Spinbox
        elif cmd == "set_spinbox":
            sb_name = target
            val_int = int(value)
            print(f"[ui2client] Remote command: set_spinbox -> {sb_name} = {val_int}")
            sb = getattr(w, sb_name, None)
            if isinstance(sb, QSpinBox):
                sb.setValue(val_int)
            else:
                for s in w.findChildren(QSpinBox):
                    if s.objectName() == sb_name:
                        s.setValue(val_int)
                        break

        # 6. Bring Host window to front
        elif cmd == "focus_host":
            w.showNormal()
            w.raise_()
            w.activateWindow()

        # Broadcast confirmation back to all clients
        broadcast({
            "type": "action_executed",
            "action": cmd,
            "target": target,
            "value": value,
            "success": True
        })

    except Exception as e:
        print(f"[ui2client] Error executing action {action}: {e}")
        traceback.print_exc()
        broadcast({
            "type": "action_executed",
            "action": cmd,
            "target": target,
            "success": False,
            "error": str(e)
        })
    finally:
        _is_updating_from_remote = False


# Connect Qt signal for thread-safe cross-thread GUI dispatch
_dispatcher.dispatch_action.connect(_dispatcher.on_dispatch, Qt.QueuedConnection)

def _dispatch_to_gui(action_data: Dict[str, Any]) -> None:
    """Schedule action execution on the Qt main GUI thread via queued signal."""
    _dispatcher.dispatch_action.emit(action_data)



async def ws_handler(websocket):
    """Asynchronous worker handling a connected Remote Client via WebSockets."""
    addr = websocket.remote_address
    print(f"[ui2client] Remote Client connected from {addr}")
    with _clients_lock:
        _connected_clients.add(websocket)

    try:
        snap = get_full_state_snapshot()
        await websocket.send(_json_serialize(snap).decode('utf-8'))
        await websocket.send(json.dumps({"type": "start_stream", "fps": 4.0, "quality": 75}))

        async for message in websocket:
            try:
                msg = json.loads(message)
                msg_type = msg.get("type", "action")
                if msg_type == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))
                elif msg_type == "get_state":
                    await websocket.send(_json_serialize(get_full_state_snapshot()).decode('utf-8'))
                elif msg_type == "device_frame":
                    global _latest_client_frame
                    data_b64 = msg.get("data", "")
                    if data_b64:
                        try:
                            _latest_client_frame = base64.b64decode(data_b64)
                        except Exception:
                            pass
                else:
                    _dispatch_to_gui(msg)
            except json.JSONDecodeError:
                pass
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"[ui2client] Client connection exception: {e}")
    finally:
        with _clients_lock:
            if websocket in _connected_clients:
                _connected_clients.remove(websocket)
        print(f"[ui2client] Remote Client disconnected: {addr}")


def _server_loop_async(port: int) -> None:
    """Background listener loop accepting incoming Remote Client connections."""
    global _ws_loop
    _ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_ws_loop)
    start_server = websockets.serve(ws_handler, HOST_IP, port, max_size=2**24)
    _ws_loop.run_until_complete(start_server)
    _ws_loop.run_forever()

def start_ui2client_server(port: int = HOST_PORT) -> bool:
    """Start the background ui2client bridge server."""
    global _server_thread, _server_running

    if _server_running:
        return True

    try:
        _server_running = True
        _server_thread = threading.Thread(
            target=_server_loop_async,
            args=(port,),
            daemon=True,
            name="ui2client-server-loop"
        )
        _server_thread.start()
        print(f"[+] [ui2client] Bridge Server (WebSockets) listening on ws://{HOST_IP}:{port}")
        return True
    except Exception as e:
        print(f"[!] [ui2client] Failed to start WebSocket server on port {port}: {e}")
        return False


def stop_ui2client_server() -> None:
    """Stop the background ui2client bridge server."""
    global _server_running, _ws_loop
    _server_running = False
    if _ws_loop and _ws_loop.is_running():
        _ws_loop.call_soon_threadsafe(_ws_loop.stop)
    with _clients_lock:
        _connected_clients.clear()
# Export alias so "ui2cliant" can also be imported if needed
ui2cliant = sys.modules[__name__]
