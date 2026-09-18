# ClashBot AI - Remote Client

Welcome to the **ClashBot AI Remote Client**!

This module provides a full-featured, live-synchronized Remote Control Interface for ClashBot AI.

---

## Key Features

1. **Dual UI Execution**:
   - Starting from `Remote Cliant/run.py` (or `run_client.bat`) automatically launches the main Host engine (`Host/run.py`).
   - Both the **Host UI window** and the **Remote Client UI window** open on your desktop side-by-side.

2. **Live Click & Control Synchronization**:
   - Clicking any button (e.g. *Start Bot*, *Stop Bot*, *Pause Bot*, *Restart ADB*) in the Remote UI triggers the exact corresponding click in the Main Host UI.
   - Switching tabs (e.g. *General*, *Attack Army*, *Builder Base*, *Clan Capital*, *Upgrades/Research*, *XP Farming*, *Extra Modes*, *Bot Runtime*, *Statistics*, *Log*) switches the tab in the Host UI in real time.
   - Toggling any checkbox (e.g. *Enable Farming*, *Upgrade Walls*, *Request Donations*, etc.) immediately toggles the setting in the Host UI.
   - Adjusting dropdowns or spinbox numbers in Remote UI instantly updates Host UI.
   - Direct changes in Host UI are also reflected in Remote UI (two-way synchronization).

3. **Live Log Streaming**:
   - Live console logs and AI tactical actions from the Host engine stream directly into the Remote Client's **Log** tab in real-time.

---

## How to Run

### Option 1: Double-Click
Double-click `run_client.bat` in this folder.

### Option 2: Command Line
Open a terminal in this directory and execute:
```bash
python run.py
```

---

## Architecture

- **Host Bridge Server (`Host/src/ui/ui2client.py`)**:
  - High-performance local socket server running on `127.0.0.1:29170`.
  - Dispatches actions safely onto the Qt main GUI thread (`animateClick()`, `click()`, `switch_page()`).
- **Remote Client Bridge (`Remote Cliant/client_bridge.py`)**:
  - Asynchronous socket client with auto-reconnect and Qt signal routing.
- **Remote Client UI (`Remote Cliant/remote_ui.py`)**:
  - Exact aesthetic replica of ClashBot AI's dark gaming UI.
