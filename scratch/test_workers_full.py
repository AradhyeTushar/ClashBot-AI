import sys
import os

# Add Host/src to sys.path
host_src = r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)\Host\src"
remote_dir = r"c:\Users\aradh\Desktop\ClashBot-AI -DEV)\Remote Cliant"
if host_src not in sys.path:
    sys.path.insert(0, host_src)
if remote_dir not in sys.path:
    sys.path.insert(0, remote_dir)

os.chdir(host_src)

print("=" * 60)
print("TESTING ADB WORKER & EMULATOR WORKER SUBSYSTEM")
print("=" * 60)

# 1. Test EmulatorWorker
from network.emulator_worker import get_emulator_worker, EmulatorWorkerThread
emu_w = get_emulator_worker()
installed = emu_w.discover_installed_emulators()
print("[1] Installed Emulators:", list(installed.keys()))
for k, v in installed.items():
    print(f"    - {k}: {v.get('name')} at {v.get('path')} (port {v.get('base_port')})")

assert "mumu" in installed, "MuMu Player should be detected on this machine!"
mumu_info = installed["mumu"]
assert mumu_info["base_port"] == 16384, f"Expected 16384, got {mumu_info['base_port']}"

# Test instance port resolution
p0 = emu_w.resolve_instance_port("mumu", "0")
p1 = emu_w.resolve_instance_port("mumu", "1")
p2 = emu_w.resolve_instance_port("mumu", "2")
print(f"[2] MuMu instance ports: Inst 0 -> {p0}, Inst 1 -> {p1}, Inst 2 -> {p2}")
assert p0 == 16384 and p1 == 16416 and p2 == 16448, "Port resolution math incorrect!"

# Test auto-configuration
preferred, port = emu_w.auto_configure_installed_emulator()
print(f"[3] Auto-configured emulator: {preferred} on port {port}")
assert preferred == "mumu" and port == 16384

# Test EmulatorWorkerThread
emu_thread = EmulatorWorkerThread(action="launch", emulator_type="mumu", timeout_sec=2.0)
assert hasattr(emu_thread, "status_changed")
assert hasattr(emu_thread, "emulator_ready")
print("[4] EmulatorWorkerThread initialized successfully with Qt signals")

# 2. Test AdbWorker
from network.adb_worker import get_adb_worker, AdbWorkerThread
adb_w = get_adb_worker()
print(f"[5] AdbWorker binary: {adb_w.adb_bin}")
assert os.path.isfile(adb_w.adb_bin), f"ADB binary missing: {adb_w.adb_bin}"

print(f"[6] Target device: {adb_w.target_device}")
assert adb_w.port == 16384 or "16384" in adb_w.target_device, f"Expected port 16384, got {adb_w.target_device}"

# Test methods exist
assert hasattr(adb_w, "tap")
assert hasattr(adb_w, "swipe")
assert hasattr(adb_w, "zoom_out")
assert hasattr(adb_w, "screencap")
assert hasattr(adb_w, "screencap_compressed")
assert hasattr(adb_w, "screencap_cv2")
assert hasattr(adb_w, "restart_adb_server")
print("[7] All device automation methods present on AdbWorker")

# Test AdbWorkerThread
adb_thread = AdbWorkerThread(mode="connect")
assert hasattr(adb_thread, "connected")
assert hasattr(adb_thread, "disconnected")
assert hasattr(adb_thread, "frame_ready")
print("[8] AdbWorkerThread initialized successfully with Qt signals")

# 3. Test ui2client state snapshot
from ui import ui2client
snapshot = ui2client.get_full_state_snapshot()
print(f"[9] ui2client snapshot: configured_emulator={snapshot.get('configured_emulator')}, port={snapshot.get('configured_port')}, detected={snapshot.get('detected_emulators')}")
assert snapshot.get("configured_emulator") == "mumu"
assert snapshot.get("configured_port") == 16384
assert "mumu" in snapshot.get("detected_emulators", [])

# 4. Test ClientBridge helper methods
from client_bridge import ClientBridge
bridge = ClientBridge()
assert hasattr(bridge, "launch_emulator")
assert hasattr(bridge, "close_emulator")
assert hasattr(bridge, "connect_adb")
print("[10] ClientBridge has all emulator and ADB helper methods")

print("=" * 60)
print("ALL TESTS PASSED WITH 100% SUCCESS!")
print("=" * 60)
