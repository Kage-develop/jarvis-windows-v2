"""
Screen casting helpers.

Jarvis never auto-selects or clicks a wireless display. It only opens the
Windows Win+K connection panel and lets the user choose the device.
"""

from __future__ import annotations

import unicodedata
from difflib import SequenceMatcher

from actions.system_quick import _press_hotkey

_PENDING_CAST: dict | None = None


def _normalize(name: str) -> str:
    text = (name or "").strip().casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.split())


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def list_cast_devices() -> list[str]:
    """List likely wireless display names when Windows allows PnP access."""
    from actions.system_quick import _run_ps

    ps = """
$names = @()
$patterns = 'TV','OLED','LG','Samsung','Sony','Display','Wireless','Miracast','Cast','Monitor','Projector','Wi-Fi Direct'
Get-PnpDevice -ErrorAction SilentlyContinue | ForEach-Object {
    $n = $_.FriendlyName
    if (-not $n) { return }
    foreach ($p in $patterns) {
        if ($n -like "*$p*") { $names += $n; break }
    }
}
$names | Sort-Object -Unique
"""
    ok, msg = _run_ps(ps, timeout=12)
    if not ok or not msg:
        return []

    devices = []
    for line in msg.splitlines():
        line = line.strip()
        if line.lower() in {"tamam.", "ok", "none"}:
            continue
        if line and line not in devices:
            devices.append(line)
    return devices


def _match_device(requested: str, devices: list[str]) -> tuple[str | None, float]:
    if not requested or not devices:
        return None, 0.0
    req = _normalize(requested)
    best_name = None
    best_score = 0.0
    for dev in devices:
        score = _similarity(requested, dev)
        if req and req in _normalize(dev):
            score = max(score, 0.92)
        if score > best_score:
            best_score = score
            best_name = dev
    if best_score >= 0.45:
        return best_name, best_score
    return None, best_score


def prepare_screen_cast(device_name: str = "") -> str:
    """Open Win+K. The user manually chooses the cast target."""
    global _PENDING_CAST

    requested = (device_name or "").strip()
    devices = list_cast_devices()
    matched, score = _match_device(requested, devices)

    _PENDING_CAST = {
        "requested": requested,
        "matched": matched or "",
        "score": score,
        "devices": devices[:12],
    }

    try:
        _press_hotkey("cast")
    except Exception as e:
        return f"Win+K acilamadi: {e}"

    hint = ", ".join(devices[:6]) if devices else "cihaz listesi bos veya Windows izin vermedi"
    if matched:
        return f"Win+K ekran baglanti paneli acildi. Listeden '{matched}' cihazini sec."
    if requested:
        return f"Win+K ekran baglanti paneli acildi. '{requested}' icin listeden cihaz sec. Gorunen cihazlar: {hint}"
    return f"Win+K ekran baglanti paneli acildi. Gorunen cihazlar: {hint}"


def confirm_screen_cast(device_name: str = "") -> str:
    """Compatibility shim: no auto-clicking, only opens Win+K."""
    return prepare_screen_cast(device_name)


def cancel_screen_cast() -> str:
    global _PENDING_CAST
    _PENDING_CAST = None
    return "Ekran yansitma panel islemi iptal edildi."
