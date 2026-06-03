from __future__ import annotations

import ctypes

try:
    import psutil
except ImportError:
    psutil = None


user32 = ctypes.windll.user32


APP_HINTS = {
    "chrome.exe": ("Chrome", "browser"),
    "msedge.exe": ("Edge", "browser"),
    "firefox.exe": ("Firefox", "browser"),
    "code.exe": ("VS Code", "editor"),
    "spotify.exe": ("Spotify", "media"),
    "discord.exe": ("Discord", "chat"),
    "whatsapp.exe": ("WhatsApp", "chat"),
    "telegram.exe": ("Telegram", "chat"),
}


def _active_hwnd() -> int:
    try:
        return int(user32.GetForegroundWindow())
    except Exception:
        return 0


def _window_title(hwnd: int) -> str:
    try:
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value.strip()
    except Exception:
        return ""


def _window_pid(hwnd: int) -> int:
    try:
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(pid.value)
    except Exception:
        return 0


def _process_info(pid: int) -> tuple[str, str]:
    if not psutil or not pid:
        return "", ""
    try:
        proc = psutil.Process(pid)
        return (proc.name() or "").strip(), (proc.exe() or "").strip()
    except Exception:
        return "", ""


def _classify(process_name: str, title: str) -> tuple[str, str]:
    key = (process_name or "").lower()
    if key in APP_HINTS:
        return APP_HINTS[key]

    low_title = (title or "").lower()
    for proc, hint in APP_HINTS.items():
        app_name = hint[0].lower()
        if app_name in low_title or proc.replace(".exe", "") in low_title:
            return hint

    return process_name.replace(".exe", "") or "Bilinmeyen uygulama", "unknown"


def get_app_context(detail: str = "summary") -> str:
    hwnd = _active_hwnd()
    if not hwnd:
        return "Aktif pencere bulunamadi."

    title = _window_title(hwnd)
    pid = _window_pid(hwnd)
    process_name, exe_path = _process_info(pid)
    app_name, app_type = _classify(process_name, title)

    lines = [
        f"Aktif uygulama: {app_name}",
        f"Uygulama tipi: {app_type}",
        f"Pencere basligi: {title or 'alinamadi'}",
    ]
    if process_name:
        lines.append(f"Process: {process_name}")
    if str(detail or "").strip().lower() in {"full", "debug"}:
        lines.append(f"PID: {pid or 'alinamadi'}")
        if exe_path:
            lines.append(f"Exe: {exe_path}")

    if app_type == "browser":
        lines.append("Baglam ipucu: Sekme/URL icerigi icin analyze_screen kullan; sekmeyi yenilemek icin system_quick_action hotkey=refresh kullan.")
    elif app_type == "editor":
        lines.append("Baglam ipucu: Kod veya gorunen metin icin analyze_screen kullan; pencere islemleri icin active_window kullan.")
    elif app_type == "media":
        lines.append("Baglam ipucu: Oynatma/durdurma icin system_quick_action media_play veya media_stop kullan.")
    elif app_type == "chat":
        lines.append("Baglam ipucu: Gorunen sohbet/metin icin analyze_screen kullan; uygulama kontrolu icin app_control veya active_window kullan.")

    return "\n".join(lines)
