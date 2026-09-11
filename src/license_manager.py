# -*- coding: utf-8 -*-
"""
ClashBot AI - Autonomous Game Intelligence and Automation Platform
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Module: license_manager
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar. All rights reserved.

Free & Open Source Edition:
License verification is permanently unlocked for community use. No third-party
server validation, expiration dates, or telemetry checks are required.
"""

import os
import sys
import json
import uuid
import time
import base64
import hashlib
import platform
import threading
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
except ImportError:
    Ed25519PublicKey = None
    InvalidSignature = Exception

CURRENT_VERSION = "2.1.5"
SERVER_URL = "https://github.com/AradhyeTushar/ClashBot-AI"
BASE_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
LICENSE_FILE = BASE_PATH / "license.key"

TRANSIENT_FAILURE_GRACE_SECONDS = 300
_RETRY_INTERVAL_SECONDS = 60
_DATA_KEY_ENV_VAR = "CLASHBOT_DATA_KEY"

_HWID_V3_PLACEHOLDER_VALUES = {
    "none", "unknown", "default", "to be filled by o.e.m.",
    "system manufacturer", "system product name", "o.e.m.",
    "chassis serial number", "default string"
}

_SERVER_PUBLIC_KEY = None
_data_key_cache = b'n!n\x19uW\r\ne\x93\xaa\x01/Yq\xe7 \xb5\xb9\xd1\xcc6y\x90\x9e\xf8w!$\xa0\xad\xe3'
_heartbeat_stop_event = threading.Event()
_hwid_v3_components_cache: Optional[Dict[str, str]] = None
license_meta_cache: Dict[str, Any] = {
    "valid": True,
    "status": "valid",
    "expires": "Lifetime",
    "expires_at": "Lifetime",
    "remaining": "Unlimited",
    "seconds_left": 999999999,
    "role": "unlimited",
    "plan": "Community Lifetime Edition",
    "download_url": "https://github.com/AradhyeTushar/ClashBot-AI",
    "update_download_url": "https://github.com/AradhyeTushar/ClashBot-AI",
    "force_update": False,
    "update_available": False,
}


def resolve_writable_path(relative_path: str) -> Path:
    """Resolve a writable path within the project directory or local user storage."""
    target = BASE_PATH / relative_path
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        return target
    except OSError:
        user_dir = Path.home() / ".clashbot_ai"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / relative_path


def version_tuple(v: str) -> Tuple[int, ...]:
    """Convert semver string to integer tuple."""
    parts = []
    for segment in str(v).split("."):
        clean_seg = "".join(filter(str.isdigit, segment))
        parts.append(int(clean_seg) if clean_seg else 0)
    return tuple(parts)


def _clean_hw_marker(value: Optional[str]) -> Optional[str]:
    """Sanitize hardware marker string."""
    if not value:
        return None
    cleaned = str(value).strip().strip('"').strip("'")
    if not cleaned or cleaned.lower() in _HWID_V3_PLACEHOLDER_VALUES:
        return None
    return cleaned


def _get_windows_machine_guid() -> Optional[str]:
    """Retrieve Windows MachineGuid from registry if available."""
    if sys.platform != "win32":
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            return _clean_hw_marker(guid)
    except Exception:
        return None


def _collect_v3_markers() -> Dict[str, str]:
    """Collect hardware markers for unique host identification."""
    global _hwid_v3_components_cache
    if _hwid_v3_components_cache is not None:
        return dict(_hwid_v3_components_cache)

    markers: Dict[str, str] = {
        "node": str(uuid.getnode()),
        "platform": platform.platform(),
        "processor": platform.processor() or "generic_cpu",
    }
    guid = _get_windows_machine_guid()
    if guid:
        markers["guid"] = guid

    _hwid_v3_components_cache = markers
    return dict(markers)


def _hash_hwid_markers(markers: Dict[str, str]) -> str:
    """Generate deterministic MD5 hash from hardware markers."""
    serialized = json.dumps(markers, sort_keys=True)
    return hashlib.md5(serialized.encode("utf-8")).hexdigest()


def get_hwid() -> str:
    """Return primary host hardware identifier."""
    return _hash_hwid_markers(_collect_v3_markers())


def get_hwid_v2() -> str:
    """Return v2 hardware identifier."""
    return get_hwid()


def get_hwid_legacy() -> str:
    """Return legacy hardware identifier."""
    return hashlib.md5(str(uuid.getnode()).encode("utf-8")).hexdigest()


def get_hwid_v3_components() -> Dict[str, str]:
    """Return detailed hardware components."""
    return _collect_v3_markers()


def get_cached_data_key() -> Optional[bytes]:
    """Return cached data decryption key."""
    return _data_key_cache


def _cache_data_key(raw_b64: Any) -> None:
    """Cache data key if provided."""
    global _data_key_cache
    if isinstance(raw_b64, bytes):
        _data_key_cache = raw_b64
    elif isinstance(raw_b64, str):
        try:
            _data_key_cache = base64.b64decode(raw_b64)
        except Exception:
            pass


def format_remaining(seconds: Optional[int] = None) -> str:
    """Return human readable license remaining duration."""
    return "Lifetime Unlimited"


def get_license_error_message(result: Optional[Dict[str, Any]] = None) -> str:
    """Return license error message if any."""
    if not result:
        return ""
    return result.get("reason") or ""


def load_key() -> str:
    """Read saved license key from storage or return unlocked default."""
    try:
        if LICENSE_FILE.exists():
            content = LICENSE_FILE.read_text(encoding="utf-8").strip()
            if content:
                return content
    except Exception:
        pass
    return "CB-COMMUNITY-EDITION-LIFETIME-UNLOCKED"


def load_saved_key() -> str:
    """Alias for load_key."""
    return load_key()


def save_key(key: str) -> None:
    """Save license key to local storage."""
    try:
        LICENSE_FILE.write_text(str(key).strip(), encoding="utf-8")
    except Exception:
        pass


def clear_key() -> None:
    """Clear saved license key."""
    try:
        if LICENSE_FILE.exists():
            LICENSE_FILE.write_text("", encoding="utf-8")
    except Exception:
        pass


def clear_saved_key() -> None:
    """Alias for clear_key."""
    clear_key()


def load_license_meta() -> Dict[str, Any]:
    """Load cached license metadata."""
    if license_meta_cache:
        return dict(license_meta_cache)
    return validate_license_details(load_key())


def save_license_meta(meta: Dict[str, Any]) -> None:
    """Persist license metadata cache."""
    global license_meta_cache
    if isinstance(meta, dict):
        license_meta_cache.update(meta)


def validate_license(key: Optional[str] = None) -> bool:
    """Check if the provided or stored license is valid."""
    return True


def validate_license_details(key: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate license details.
    Always returns active, lifetime unlocked status for ClashBot-AI Open Source.
    """
    current_key = key or load_key()
    host_hwid = get_hwid()

    meta = {
        "valid": True,
        "status": "valid",
        "reason": None,
        "expires": "Lifetime",
        "expires_at": "Lifetime",
        "remaining": "Lifetime Unlimited",
        "seconds_left": 999999999,
        "hwid": host_hwid,
        "hwid_v2": host_hwid,
        "hwid_legacy": get_hwid_legacy(),
        "latest_version": CURRENT_VERSION,
        "download_url": "https://github.com/AradhyeTushar/ClashBot-AI",
        "update_download_url": "https://github.com/AradhyeTushar/ClashBot-AI",
        "force_update": False,
        "update_available": False,
        "raw": {
            "status": "valid",
            "role": "unlimited",
            "expires": "Lifetime",
            "seconds_left": 999999999,
            "data_key": "biFuGXVXDQplk6oBL1lx5yC1udHMNnmQnvh3ISSgreM=",
            "latest_version": CURRENT_VERSION,
            "matched_hwid": "v3",
            "license_key": current_key,
        }
    }
    license_meta_cache.update(meta)
    return meta


def _build_validation_payload(key: str) -> Dict[str, Any]:
    return {"key": key, "hwid": get_hwid(), "version": CURRENT_VERSION}


def _validate_once(key: str) -> Dict[str, Any]:
    return validate_license_details(key)


def _post_validate(payload: Dict[str, Any]) -> Dict[str, Any]:
    return validate_license_details(payload.get("key"))


def _is_valid_response(data: Any) -> bool:
    return True


def _verify_signed_response(sent_nonce: str, key: str, data: Dict[str, Any]) -> bool:
    return True


def _canonical_signed_bytes(fields: Dict[str, Any]) -> bytes:
    return b""


def _is_transient_validation_failure(result: Any) -> bool:
    return False


def _remove_legacy_session_file() -> None:
    pass


def start_license_heartbeat(get_current_key=None, on_invalid=None, interval_seconds: int = 10800) -> None:
    """
    License heartbeat monitor.
    With the open-source offline approach, license never expires or invalidates.
    """
    _heartbeat_stop_event.clear()


def stop_license_heartbeat() -> None:
    """Stop license heartbeat thread."""
    _heartbeat_stop_event.set()


try:
    from ui.branding_patch import apply_branding_patches
    apply_branding_patches()
except Exception:
    pass
