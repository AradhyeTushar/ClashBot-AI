# -*- coding: utf-8 -*-
"""
ClashBot AI - UI Branding & Titlebar Patch
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar. All rights reserved.

This module patches Qt widgets and UI windows to ensure 100% consistent
ClashBot AI branding across all window titles, custom title bars, labels, and dialogs.
"""

import sys
import os
import re
import builtins

_BASE_PATCHED = False
_HOOK_INSTALLED = False
_PATCHED_CLASSES = set()

def clean_branding_text(text):
    """Clean any remaining AutoClash legacy strings to ClashBot AI."""
    if not isinstance(text, str):
        return text
    
    # Specific compound names & path replacements
    text = re.sub(r'AutoClash\s*Pro', 'ClashBot AI Pro', text, flags=re.IGNORECASE)
    text = re.sub(r'AutoClash\s*Mini', 'ClashBot AI Mini', text, flags=re.IGNORECASE)
    text = re.sub(r'Auto\s*Clash\s*Pro', 'ClashBot AI Pro', text, flags=re.IGNORECASE)
    text = re.sub(r'Auto\s*Clash\s*Mini', 'ClashBot AI Mini', text, flags=re.IGNORECASE)
    text = re.sub(r'\\AutoClash\\', r'\\ClashBot-AI\\', text, flags=re.IGNORECASE)
    text = re.sub(r'/AutoClash/', r'/ClashBot-AI/', text, flags=re.IGNORECASE)
    text = re.sub(r'Auto\s*Clash', 'ClashBot AI', text, flags=re.IGNORECASE)
    text = re.sub(r'AutoClash', 'ClashBot AI', text, flags=re.IGNORECASE)
    text = re.sub(r'autoclash', 'ClashBot AI', text, flags=re.IGNORECASE)
    return text


def _patch_main_window_class(cls):
    """Patch MainWindow methods."""
    if cls in _PATCHED_CLASSES:
        return
    _PATCHED_CLASSES.add(cls)

    _orig_update_window_title = cls._update_window_title
    def _patched_update_window_title(self, *args, **kwargs):
        try:
            _orig_update_window_title(self, *args, **kwargs)
        except Exception:
            pass
        cleaned = clean_branding_text(self.windowTitle())
        self.setWindowTitle(cleaned)
        if hasattr(self, "titlebar_title") and self.titlebar_title:
            try:
                self.titlebar_title.setText(cleaned)
            except Exception:
                pass
    cls._update_window_title = _patched_update_window_title

    _orig_init = cls.__init__
    def _patched_init(self, *args, **kwargs):
        _orig_init(self, *args, **kwargs)
        try:
            self._update_window_title()
        except Exception:
            pass
        try:
            from PySide6.QtWidgets import QLabel
            for lbl in self.findChildren(QLabel):
                t = lbl.text()
                if t and ('auto' in t.lower() or 'clash' in t.lower()):
                    c = clean_branding_text(t)
                    if c != t:
                        lbl.setText(c)
        except Exception:
            pass
    cls.__init__ = _patched_init

    if hasattr(cls, "append_log"):
        _orig_append_log = cls.append_log
        def _patched_append_log(self, text, *args, **kwargs):
            if isinstance(text, str):
                text = clean_branding_text(text)
            return _orig_append_log(self, text, *args, **kwargs)
        cls.append_log = _patched_append_log


def _patch_mini_window_class(cls):
    """Patch MiniWindow methods."""
    if cls in _PATCHED_CLASSES:
        return
    _PATCHED_CLASSES.add(cls)

    _orig_update_window_title = cls._update_window_title
    def _patched_update_window_title(self, *args, **kwargs):
        try:
            _orig_update_window_title(self, *args, **kwargs)
        except Exception:
            pass
        cleaned = clean_branding_text(self.windowTitle())
        self.setWindowTitle(cleaned)
        if hasattr(self, "title_label") and self.title_label:
            try:
                self.title_label.setText(cleaned)
            except Exception:
                pass
    cls._update_window_title = _patched_update_window_title

    _orig_init = cls.__init__
    def _patched_init(self, *args, **kwargs):
        _orig_init(self, *args, **kwargs)
        try:
            self._update_window_title()
        except Exception:
            pass
        try:
            from PySide6.QtWidgets import QLabel
            for lbl in self.findChildren(QLabel):
                t = lbl.text()
                if t and ('auto' in t.lower() or 'clash' in t.lower()):
                    c = clean_branding_text(t)
                    if c != t:
                        lbl.setText(c)
        except Exception:
            pass
    cls.__init__ = _patched_init

    if hasattr(cls, "append_log"):
        _orig_mini_append_log = cls.append_log
        def _patched_mini_append_log(self, text, *args, **kwargs):
            if isinstance(text, str):
                text = clean_branding_text(text)
            return _orig_mini_append_log(self, text, *args, **kwargs)
        cls.append_log = _patched_mini_append_log


def _patch_bot_worker(mod):
    """Patch TeeStream in bot_worker to ensure session log file and streams use ClashBot AI."""
    if hasattr(mod, "TeeStream"):
        cls = mod.TeeStream
        if cls not in _PATCHED_CLASSES:
            _PATCHED_CLASSES.add(cls)
            _orig_write = cls.write
            def _patched_write(self, data):
                if isinstance(data, str):
                    data = clean_branding_text(data)
                return _orig_write(self, data)
            cls.write = _patched_write


def _install_import_hook():
    """Install import hook to auto-patch window classes whenever modules are loaded."""
    global _HOOK_INSTALLED
    if _HOOK_INSTALLED:
        return
    _HOOK_INSTALLED = True

    _orig_import = builtins.__import__
    def _branding_import(name, globals=None, locals=None, fromlist=(), level=0):
        mod = _orig_import(name, globals, locals, fromlist, level)
        try:
            for mod_name in ("ui.main_window", "main_window"):
                if mod_name in sys.modules:
                    m = sys.modules[mod_name]
                    if hasattr(m, "MainWindow"):
                        _patch_main_window_class(m.MainWindow)
            for mod_name in ("ui.mini_window", "mini_window"):
                if mod_name in sys.modules:
                    m = sys.modules[mod_name]
                    if hasattr(m, "MiniWindow"):
                        _patch_mini_window_class(m.MiniWindow)
            for mod_name in ("ui.bot_worker", "bot_worker"):
                if mod_name in sys.modules:
                    _patch_bot_worker(sys.modules[mod_name])
        except Exception:
            pass
        return mod
    builtins.__import__ = _branding_import


def apply_branding_patches():
    """Apply branding monkey-patches to Qt widgets and window classes."""
    global _BASE_PATCHED
    
    _install_import_hook()

    if not _BASE_PATCHED:
        _BASE_PATCHED = True
        try:
            from PySide6.QtWidgets import (
                QWidget, QLabel, QAbstractButton, QGroupBox
            )
            from PySide6.QtCore import QCoreApplication

            # 1. Patch QWidget.setWindowTitle
            _orig_setWindowTitle = QWidget.setWindowTitle
            def _patched_setWindowTitle(self, *args, **kwargs):
                if args and isinstance(args[0], str):
                    args = (clean_branding_text(args[0]),) + args[1:]
                return _orig_setWindowTitle(self, *args, **kwargs)
            QWidget.setWindowTitle = _patched_setWindowTitle

            # 2. Patch QLabel.setText and QLabel.__init__
            _orig_lbl_setText = QLabel.setText
            def _patched_lbl_setText(self, *args, **kwargs):
                if args and isinstance(args[0], str):
                    args = (clean_branding_text(args[0]),) + args[1:]
                return _orig_lbl_setText(self, *args, **kwargs)
            QLabel.setText = _patched_lbl_setText

            _orig_lbl_init = QLabel.__init__
            def _patched_lbl_init(self, *args, **kwargs):
                if args and isinstance(args[0], str):
                    args = (clean_branding_text(args[0]),) + args[1:]
                if 'text' in kwargs and isinstance(kwargs['text'], str):
                    kwargs['text'] = clean_branding_text(kwargs['text'])
                return _orig_lbl_init(self, *args, **kwargs)
            QLabel.__init__ = _patched_lbl_init

            # 3. Patch QAbstractButton.setText and __init__
            _orig_btn_setText = QAbstractButton.setText
            def _patched_btn_setText(self, *args, **kwargs):
                if args and isinstance(args[0], str):
                    args = (clean_branding_text(args[0]),) + args[1:]
                return _orig_btn_setText(self, *args, **kwargs)
            QAbstractButton.setText = _patched_btn_setText

            _orig_btn_init = QAbstractButton.__init__
            def _patched_btn_init(self, *args, **kwargs):
                if args and isinstance(args[0], str):
                    args = (clean_branding_text(args[0]),) + args[1:]
                if 'text' in kwargs and isinstance(kwargs['text'], str):
                    kwargs['text'] = clean_branding_text(kwargs['text'])
                return _orig_btn_init(self, *args, **kwargs)
            QAbstractButton.__init__ = _patched_btn_init

            # 4. Patch QGroupBox.setTitle and __init__
            _orig_gb_setTitle = QGroupBox.setTitle
            def _patched_gb_setTitle(self, *args, **kwargs):
                if args and isinstance(args[0], str):
                    args = (clean_branding_text(args[0]),) + args[1:]
                return _orig_gb_setTitle(self, *args, **kwargs)
            QGroupBox.setTitle = _patched_gb_setTitle

            # 5. Patch QCoreApplication.setApplicationName & QApplication.setApplicationName
            _orig_setAppName = QCoreApplication.setApplicationName
            def _patched_setAppName(*args, **kwargs):
                str_arg = args[-1] if args else "ClashBot AI"
                cleaned = clean_branding_text(str_arg) if isinstance(str_arg, str) else str_arg
                return _orig_setAppName(cleaned)
            QCoreApplication.setApplicationName = staticmethod(_patched_setAppName)
            QApplication.setApplicationName = staticmethod(_patched_setAppName)

        except Exception as e:
            pass

    # Eagerly patch MainWindow and MiniWindow
    try:
        from ui import main_window
        _patch_main_window_class(main_window.MainWindow)
    except Exception:
        pass

    try:
        from ui import mini_window
        _patch_mini_window_class(mini_window.MiniWindow)
    except Exception:
        pass

    try:
        from ui import bot_worker
        _patch_bot_worker(bot_worker)
    except Exception:
        pass

    # Patch gui.set_windows_app_user_model_id if available
    try:
        from ui import gui
        def _patched_app_id():
            if sys.platform == "win32":
                try:
                    import ctypes
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ClashBotAI.App.2.1.5")
                except Exception:
                    pass
        gui.set_windows_app_user_model_id = _patched_app_id
    except Exception:
        pass
