"""
WhatsApp mesaj gönderme — Windows için WhatsApp Desktop URI scheme veya Web.
Önce WhatsApp Desktop uygulaması aranır; bulunamazsa WhatsApp Web kullanılır.

send_now=True → pencere/sekme açıldıktan sonra otomatik Enter gönderir.
  Yöntem önceliği: win32api > pyautogui > PowerShell SendKeys
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import unicodedata
import urllib.parse
import webbrowser
from pathlib import Path

from memory.memory_manager import load_memory, update_memory

try:
    import win32api, win32con, win32gui
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


DESKTOP_OPEN_DELAY = 2.5   # WhatsApp Desktop'ın sohbeti yüklemesi için bekleme (sn)
WEB_OPEN_DELAY     = 4.0   # WhatsApp Web'in yüklenmesi için bekleme (sn)

BASE_DIR      = Path(__file__).resolve().parent.parent
PHONEBOOK_FILE = BASE_DIR / "memory" / "phone_book.json"

WHATSAPP_DESKTOP_PATHS: list[Path] = [
    Path(os.environ.get("LOCALAPPDATA",      "")) / "WhatsApp" / "WhatsApp.exe",
    Path(os.environ.get("PROGRAMFILES",      "")) / "WhatsApp" / "WhatsApp.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", "")) / "WhatsApp" / "WhatsApp.exe",
]

# WhatsApp Desktop pencere sınıfı / başlık parçası
WA_WINDOW_CLASS = "WhatsApp"
WA_WINDOW_TITLE = "WhatsApp"


# ---------------------------------------------------------------------------
# Enter gönderme yardımcıları
# ---------------------------------------------------------------------------

def _send_enter_win32(delay: float) -> tuple[bool, str]:
    """Aktif WhatsApp penceresine win32api ile VK_RETURN gönderir."""
    if not HAS_WIN32:
        return False, "win32api yok"
    try:
        time.sleep(delay)
        hwnd = win32gui.FindWindow(None, None)
        # Ön plandaki pencereye gönder
        win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
        time.sleep(0.05)
        win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def _send_enter_pyautogui(delay: float) -> tuple[bool, str]:
    if not HAS_PYAUTOGUI:
        return False, "pyautogui yok"
    try:
        time.sleep(delay)
        pyautogui.press("enter")
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def _send_enter_powershell(delay: float) -> tuple[bool, str]:
    """PowerShell WScript.Shell SendKeys ile Enter gönderir."""
    try:
        time.sleep(delay)
        script = (
            '$wsh = New-Object -ComObject WScript.Shell; '
            '$wsh.SendKeys("{ENTER}")'
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            timeout=8,
        )
        if result.returncode == 0:
            return True, "ok"
        return False, f"PowerShell çıkış kodu: {result.returncode}"
    except Exception as exc:
        return False, str(exc)


def _send_enter(delay: float) -> tuple[bool, str]:
    """En iyi mevcut yöntemle Enter gönderir."""
    for fn in (_send_enter_win32, _send_enter_pyautogui, _send_enter_powershell):
        ok, detail = fn(delay)
        if ok:
            return True, detail
    return False, "Hiçbir Enter gönderme yöntemi çalışmadı (win32api / pyautogui / PowerShell)"


# ---------------------------------------------------------------------------
# WhatsApp Desktop kurulum tespiti
# ---------------------------------------------------------------------------

def _find_whatsapp_desktop_exe() -> Path | None:
    for path in WHATSAPP_DESKTOP_PATHS:
        if path.exists():
            return path

    windows_apps = Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "WindowsApps"
    try:
        matches = list(windows_apps.glob("5319275A.WhatsAppDesktop*\\WhatsApp.exe"))
        if matches:
            return matches[0]
    except (PermissionError, OSError):
        pass

    try:
        result = subprocess.run(
            ["where", "WhatsApp.exe"],
            capture_output=True, text=True, timeout=5, shell=True,
        )
        if result.returncode == 0:
            p = Path(result.stdout.strip().splitlines()[0])
            if p.exists():
                return p
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["reg", "query", r"HKCU\Software\Classes\whatsapp", "/ve"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return Path("__scheme_only__")
    except Exception:
        pass

    return None


def _whatsapp_desktop_available() -> bool:
    return _find_whatsapp_desktop_exe() is not None


# ---------------------------------------------------------------------------
# Telefon / kişi yardımcıları
# ---------------------------------------------------------------------------

def _normalize_phone(phone_number: str) -> str:
    digits = re.sub(r"\D+", "", phone_number or "")
    if len(digits) == 11 and digits.startswith("0"):
        digits = "90" + digits[1:]
    elif len(digits) == 10:
        digits = "90" + digits
    if len(digits) < 8 or len(digits) > 15:
        raise ValueError("Telefon numarası uluslararası formatta olmalı. Örn: +905551112233")
    return digits


def _normalize_lookup(text: str) -> str:
    text = (text or "").strip().casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("ı", "i")
    text = re.sub(r"\s+", " ", text)
    return text


def _contact_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _normalize_lookup(name)).strip("_") or "contact"


def _load_contacts() -> dict:
    memory = load_memory()
    contacts = memory.get("whatsapp_contacts", {})
    return contacts if isinstance(contacts, dict) else {}


def _load_phone_book() -> dict:
    try:
        if PHONEBOOK_FILE.exists():
            return json.loads(PHONEBOOK_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _contact_candidates() -> list[dict]:
    candidates = []
    for source_name, source in (("whatsapp", _load_contacts()), ("phone_book", _load_phone_book())):
        if not isinstance(source, dict):
            continue
        for key, entry in source.items():
            if not isinstance(entry, dict):
                continue
            item = dict(entry)
            item.setdefault("display_name", key)
            item["_source"] = source_name
            item["_key"] = key
            candidates.append(item)
    return candidates


def _match_score(needle: str, candidate: str) -> int:
    c = _normalize_lookup(candidate)
    if not c:
        return 0
    if c == needle:                                              return 300
    if c.startswith(needle) or needle.startswith(c):            return 220
    if needle in c:                                              return 160
    parts = needle.split()
    if parts and all(p in c for p in parts):                     return 120
    return 0


def _find_contact(recipient_name: str) -> dict | None:
    needle = _normalize_lookup(recipient_name)
    if not needle:
        return None
    best, best_score = None, 0
    for entry in _contact_candidates():
        names = [entry.get("display_name", ""), entry.get("_key", "")]
        aliases = entry.get("aliases", [])
        names += [str(a) for a in aliases] if isinstance(aliases, list) else [str(aliases)]
        for name in names:
            score = _match_score(needle, name)
            if score > best_score:
                best_score = score
                best = entry
    return best


# ---------------------------------------------------------------------------
# Kişi kaydetme
# ---------------------------------------------------------------------------

def save_whatsapp_contact(display_name: str, phone_number: str, aliases: str = "") -> str:
    if not display_name or not display_name.strip():
        return "Kişi adı boş olamaz."
    try:
        normalized_phone = _normalize_phone(phone_number)
    except ValueError as exc:
        return str(exc)
    alias_list = [p.strip() for p in aliases.split(",") if p.strip()] if aliases.strip() else []
    key = _contact_key(display_name)
    update_memory({
        "whatsapp_contacts": {
            key: {
                "value": f"+{normalized_phone}",
                "display_name": display_name.strip(),
                "aliases": alias_list,
            }
        }
    })
    suffix = f" Takma adlar: {', '.join(alias_list)}" if alias_list else ""
    return f"{display_name.strip()} WhatsApp kişilerine kaydedildi.{suffix}"


# ---------------------------------------------------------------------------
# Platform açma yardımcıları
# ---------------------------------------------------------------------------

def _open_whatsapp_desktop(phone: str, message: str) -> tuple[bool, str]:
    url = f"whatsapp://send?phone={phone}&text={urllib.parse.quote(message.strip())}"
    try:
        subprocess.run(["start", "", url], shell=True, timeout=10)
    except Exception as exc:
        return False, str(exc)
    return True, ""


def _open_whatsapp_web(phone: str, message: str) -> tuple[bool, str]:
    url = f"https://web.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(message.strip())}"
    try:
        webbrowser.open(url)
    except Exception as exc:
        return False, str(exc)
    return True, ""


# ---------------------------------------------------------------------------
# Ana fonksiyon
# ---------------------------------------------------------------------------

def send_whatsapp_message(
    message: str,
    phone_number: str = "",
    recipient_name: str = "",
    send_now: bool = False,
    app_target: str = "auto",
) -> str:
    """
    WhatsApp mesajı hazırlar veya gönderir.

    send_now=False  → sohbeti/sekmeyi aç, kullanıcı Enter'a bassın.
    send_now=True   → aç, yüklenmeyi bekle, otomatik Enter gönder.

    app_target: "auto" | "desktop" | "web"
      auto → Desktop kuruluysa Desktop, değilse Web.
    """
    if not message or not message.strip():
        return "Mesaj boş olamaz."

    app_target = (app_target or "auto").strip().lower()
    if app_target not in {"auto", "desktop", "web"}:
        app_target = "auto"

    # Numara çöz
    normalized_phone = ""
    if phone_number and phone_number.strip():
        try:
            normalized_phone = _normalize_phone(phone_number)
        except ValueError as exc:
            return str(exc)

    resolved_name = (recipient_name or "").strip()
    contact_source = ""
    if resolved_name:
        contact = _find_contact(resolved_name)
        if contact and not normalized_phone:
            try:
                normalized_phone = _normalize_phone(str(contact.get("value", "")))
            except ValueError:
                pass
            resolved_name = str(contact.get("display_name", resolved_name)).strip() or resolved_name
            contact_source = contact.get("_source", "")

    if not normalized_phone:
        if resolved_name:
            return (
                f"'{resolved_name}' için kayıtlı telefon numarası bulunamadı. "
                "Önce kişiyi numarasıyla kaydet."
            )
        return "WhatsApp mesajı için kişi adı veya telefon numarası gerekli."

    label       = resolved_name or f"+{normalized_phone}"
    source_note = " (rehberden)" if contact_source == "phone_book" else ""

    # Hangi platform?
    if app_target == "desktop":
        use_desktop = True
    elif app_target == "web":
        use_desktop = False
    else:
        use_desktop = _whatsapp_desktop_available()

    fallback_note = ""

    # ── Desktop ──────────────────────────────────────────────────────────────
    if use_desktop:
        ok, err = _open_whatsapp_desktop(normalized_phone, message)
        if ok:
            if not send_now:
                return f"WhatsApp Desktop'ta {label}{source_note} için taslak açıldı. Göndermek için Enter'a bas."
            ok_s, s_err = _send_enter(DESKTOP_OPEN_DELAY)
            if ok_s:
                return f"WhatsApp Desktop üzerinden {label}{source_note} kişisine mesaj gönderildi."
            return (
                f"WhatsApp Desktop açıldı ama otomatik gönderilemedi: {s_err}. "
                "Enter'a basarak gönderebilirsin."
            )
        if app_target == "desktop":
            return f"WhatsApp Desktop açılamadı: {err}"
        fallback_note = f"WhatsApp Desktop açılamadı ({err}), WhatsApp Web'e geçiliyor...\n"

    # ── Web ──────────────────────────────────────────────────────────────────
    ok, err = _open_whatsapp_web(normalized_phone, message)
    if not ok:
        return fallback_note + f"WhatsApp Web açılamadı: {err}"

    if not send_now:
        return (
            fallback_note
            + f"WhatsApp Web'de {label}{source_note} için taslak açıldı. Göndermek için Enter'a bas."
        )

    ok_s, s_err = _send_enter(WEB_OPEN_DELAY)
    if ok_s:
        return fallback_note + f"WhatsApp Web üzerinden {label}{source_note} kişisine mesaj gönderildi."

    return (
        fallback_note
        + f"WhatsApp Web açıldı ama otomatik gönderilemedi: {s_err}. "
        "Enter'a basarak gönderebilirsin."
    )