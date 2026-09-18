# -*- coding: utf-8 -*-
"""
ClashBot AI - Remote Client Stylesheet System
Matches the exact stylesheet, colors, fonts, and assets of ClashBot AI Host UI.
"""

import os

def get_assets_dir() -> str:
    """Get absolute path to assets directory with forward slashes for Qt CSS."""
    client_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(client_dir, "assets")
    return assets_dir.replace("\\", "/")



def get_base_stylesheet() -> str:
    """Generate exact ClashBot AI stylesheet with resolved asset paths."""
    a = get_assets_dir()
    
    css = f"""
QMainWindow {{
    background-color: #14161A;
}}
                
QFrame {{
    background-color: rgba(28, 31, 38, 235);
}}

#NavPanel {{
    background-color: #1D212A;
    border-right: 1px solid #2A2F3B;
}}

#PageStack {{
    background: qlineargradient(
        x1: 0, y1: 0,
        x2: 1, y2: 1,
        stop: 0 #181C25,
        stop: 0.55 #1A1E29,
        stop: 1 #212233
    );
}}

#PageStack > QWidget {{
    background: transparent;
}}

#BottomBar {{
    background-color: #171A21;
    border-top: 1px solid #2A2F3B;
    border-bottom-left-radius: 10px;
    border-bottom-right-radius: 10px;
}}

#TitleBar {{
    background-color: #171A21;
    border-bottom: 1px solid #2A2F3B;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}}

#TitleBarTitle {{
    color: #ECEFF4;
    font-family: "Segoe UI Variable", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    font-weight: 600;
}}

#TitleMinBtn,
#TitleCloseBtn {{
    min-width: 38px;
    max-width: 38px;
    min-height: 32px;
    max-height: 32px;
    margin: 0px;
    padding: 0px;
    text-align: center;
    border-radius: 6px;
    font-size: 16px;
    font-weight: bold;
    color: #C9CCD6;
    background: transparent;
    border: none;
}}

#TitleMinBtn:hover {{
    background-color: #2D3240;
    color: #FFFFFF;
}}
#TitleMinBtn:pressed {{
    background-color: #1F2330;
}}

#TitleCloseBtn:hover {{
    background-color: #DC2626;
    color: #FFFFFF;
    border: 1px solid #B91C1C;
}}
#TitleCloseBtn:pressed {{
    background-color: #991B1B;
    border: 1px solid #7F1D1D;
}}

/* ---------------- Buttons ---------------- */

QPushButton {{
    background-color: #242834;
    color: #E6E6E6;
    border: 1px solid #181B24;
    border-radius: 8px;
    padding: 8px 12px;
    margin: 2px 4px;
    text-align: center;
    font-family: "Segoe UI Variable", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: #2D3240;
    border: 1px solid #222737;
}}

QPushButton:pressed {{
    background-color: #1F2330;
    border: 1px solid #141824;
}}

/* Sidebar navigation buttons */
QPushButton[nav_button="true"] {{
    background: transparent;
    border: none;
    border-left: 3px solid transparent;
    color: #C9CCD6;
    text-align: left;
    padding: 7px 14px 7px 14px;
    margin: 2px 6px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton[nav_button="true"]:hover {{
    background-color: rgba(148, 163, 184, 0.14);
    color: #E6EAF2;
}}

QPushButton[nav_button="true"]:checked {{
    background-color: rgba(139, 85, 246, 0.18);
    border: 1px solid rgba(139, 85, 246, 0.45);
    border-left: 3px solid #8B55F6;
    color: #F4F7FB;
    font-weight: bold;
}}

QPushButton[nav_button="true"]:pressed {{
    background-color: rgba(148, 163, 184, 0.24);
}}

/* ---------------- Text & Labels ---------------- */

QLabel {{
    color: #C9CCD6;
    background: transparent;
    font-weight: 400;
}}

/* ---------------- CheckBoxes (Exact Refined Host Style) ---------------- */

QCheckBox {{
    color: #C9CCD6;
    font-weight: 400;
    min-height: 26px;
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #3A4253;
    background-color: #1B1F2A;
    image: none;
}}

QCheckBox::indicator:hover {{
    border: 1px solid #8B55F6;
    background-color: #202432;
}}

QCheckBox::indicator:unchecked {{
    border: 1px solid #3A4253;
    background-color: #1B1F2A;
    image: none;
}}

QCheckBox::indicator:unchecked:hover {{
    border: 1px solid #8B55F6;
    background-color: #202432;
}}

QCheckBox::indicator:checked {{
    border: 1px solid #8B55F6;
    background-color: #1B1F2A;
    image: url("{a}/checkbox_check_purple.svg");
}}

QCheckBox::indicator:checked:hover {{
    border: 1px solid #9B6CFA;
    background-color: #232736;
    image: url("{a}/checkbox_check_purple.svg");
}}

QCheckBox:disabled,
QCheckBox:disabled:hover {{
    color: rgba(150, 158, 174, 0.92);
}}

QCheckBox::indicator:disabled,
QCheckBox::indicator:unchecked:disabled {{
    border: 1px solid rgba(39, 45, 57, 0.9);
    background-color: rgba(23, 27, 34, 0.88);
    image: none;
}}

QCheckBox::indicator:checked:disabled {{
    border: 1px solid rgba(78, 86, 100, 0.9);
    background-color: rgba(23, 27, 34, 0.88);
    image: url("{a}/checkbox_check_gray.svg");
}}

/* ---------------- Inputs & Combos ---------------- */

QTextEdit {{
    color: #C9CCD6;
    background-color: #13161F;
    border: 1px solid #2A2F3B;
    border-radius: 6px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}}

QLineEdit,
QComboBox,
QSpinBox {{
    color: #E6E6E6;
    font-family: "Segoe UI Variable", "Segoe UI", Arial, sans-serif;
    font-weight: 500;
    font-size: 13px;
    background-color: #1B1F2A;
    border: 1px solid #2A2F3B;
    border-radius: 6px;
    min-height: 26px;
}}

QLineEdit:hover,
QComboBox:hover,
QSpinBox:hover {{
    border: 1px solid #3A4253;
}}

QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus {{
    border: 1px solid #A78BFA;
}}

QComboBox {{
    padding-left: 8px;
    padding-right: 26px;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 18px;
    margin-right: 2px;
    border: none;
    background: transparent;
}}

QComboBox::down-arrow {{
    image: url("{a}/arrow_down.svg");
    width: 12px;
    height: 8px;
}}

QComboBox QAbstractItemView {{
    color: #E6E6E6;
    background-color: #1B1F2A;
    border: 1px solid #2A2F3B;
    outline: none;
    selection-background-color: #8B55F6;
    selection-color: #FFFFFF;
}}

QComboBox QAbstractItemView::item {{
    min-height: 24px;
    padding: 3px 8px;
}}

QComboBox QAbstractItemView::item:hover,
QComboBox QAbstractItemView::item:selected {{
    background-color: #8B55F6;
    color: #FFFFFF;
}}

QSpinBox {{
    padding-left: 8px;
    padding-right: 24px;
}}

QSpinBox::up-button,
QSpinBox::down-button {{
    subcontrol-origin: padding;
    width: 14px;
    margin-right: 2px;
    background: transparent;
    border: none;
}}

QSpinBox::up-button:hover,
QSpinBox::down-button:hover {{
    background: rgba(96, 165, 250, 0.16);
}}

QSpinBox::up-button:pressed,
QSpinBox::down-button:pressed {{
    background: rgba(96, 165, 250, 0.28);
}}

QSpinBox::up-button {{
    subcontrol-position: top right;
}}

QSpinBox::down-button {{
    subcontrol-position: bottom right;
}}

QSpinBox::up-arrow {{
    image: url("{a}/arrow_up.svg");
    width: 12px;
    height: 8px;
}}

QSpinBox::down-arrow {{
    image: url("{a}/arrow_down.svg");
    width: 12px;
    height: 8px;
}}

/* ---------------- Scrollbars ---------------- */

QScrollBar:vertical {{
    background: #171A21;
    width: 10px;
    margin: 2px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background: rgba(142, 150, 166, 0.5);
    min-height: 24px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical:hover {{
    background: rgba(165, 174, 190, 0.68);
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: transparent;
    height: 0px;
}}

QScrollBar:horizontal {{
    background: #171A21;
    height: 10px;
    margin: 2px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background: rgba(142, 150, 166, 0.5);
    min-width: 24px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal:hover {{
    background: rgba(165, 174, 190, 0.68);
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {{
    background: transparent;
    width: 0px;
}}

/* ---------------- Group Boxes (Exact Golden Titles) ---------------- */

QGroupBox {{
    color: #F4D37A;
    font-family: "Segoe UI Variable", "Segoe UI", Arial, sans-serif;
    font-weight: 500;
    font-size: 15px;
    border: 1px solid #232734;
    border-radius: 8px;
    background-color: rgba(27, 31, 42, 140);
    margin-top: 12px;
    padding-top: 14px;
    padding-bottom: 8px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
}}

/* ---------------- Control Buttons (Start / Pause / Stop) ---------------- */

#StartBtn {{
    background-color: #22C55E;
    color: white;
    text-align: center;
    font-size: 22px;
    font-weight: bold;
    border-radius: 10px;
    border: 1px solid rgba(0, 0, 0, 0.35);
    min-height: 42px;
    min-width: 90px;
}}

#StartBtn:hover {{ background-color: #16A34A; }}
#StartBtn:pressed {{ background-color: #15803D; }}

#PauseBtn {{
    background-color: #FACC15;
    color: #1A202C;
    text-align: center;
    font-size: 20px;
    font-weight: bold;
    border-radius: 10px;
    border: 1px solid rgba(0, 0, 0, 0.35);
    min-height: 42px;
    min-width: 80px;
}}

#PauseBtn:hover {{ background-color: #EAB308; }}
#PauseBtn:pressed {{ background-color: #CA8A04; }}

#StopBtn {{
    background-color: #EF4444;
    color: white;
    text-align: center;
    font-size: 22px;
    font-weight: bold;
    border-radius: 10px;
    border: 1px solid rgba(0, 0, 0, 0.35);
    min-height: 42px;
    min-width: 90px;
}}

#StopBtn:hover {{ background-color: #DC2626; }}
#StopBtn:pressed  {{ background-color: #B91C1C; }}

/* ---------------- Settings Drawer ---------------- */

#SettingsDrawer {{
    background-color: #1D212A;
    border: 2px solid #2F3546;
    border-radius: 8px;
    padding: 12px;
    margin: 0px;
    min-width: 250px;
    max-width: 250px;
}}

/* ---------------- Focus Host Button ---------------- */

#FocusHostBtn {{
    background-color: #4C1D95;
    color: #EDE9FE;
    border: 1px solid #6D28D9;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 12px;
}}

#FocusHostBtn:hover {{
    background-color: #5B21B6;
    border-color: #8B5CF6;
    color: #FFFFFF;
}}

/* Tooltips */
QToolTip {{
    background-color: #2E3440;
    color: #ECEFF4;
    border: 1px solid #4C566A;
    padding: 4px;
    border-radius: 4px;
}}
"""
    return css
