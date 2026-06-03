"""
Instagram mesaj gönderme — Chrome'da direkt DM açar, mesajı yapıştırır.
Kişiler ID ile kaydedilir.
"""

from __future__ import annotations

import json
import re
import subprocess
import unicodedata
import webbrowser
import time
from pathlib import Path

import pyautogui

from memory.memory_manager import load_memory, update_memory

BASE_DIR = Path(__file__).resolve().parent.parent
INSTAGRAM_CONTACTS_FILE = BASE_DIR / "memory" / "instagram_contacts.json"


# ---------------------------------------------------------------------------
# Kişi yönetimi
# ---------------------------------------------------------------------------

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
    try:
        if INSTAGRAM_CONTACTS_FILE.exists():
            return json.loads(INSTAGRAM_CONTACTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_contacts(contacts: dict):
    INSTAGRAM_CONTACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    INSTAGRAM_CONTACTS_FILE.write_text(
        json.dumps(contacts, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _match_score(needle: str, candidate: str) -> int:
    c = _normalize_lookup(candidate)
    if not c:
        return 0
    if c == needle:                                   return 300
    if c.startswith(needle) or needle.startswith(c): return 220
    if needle in c:                                   return 160
    parts = needle.split()
    if parts and all(p in c for p in parts):          return 120
    return 0


def _find_contact(name: str) -> dict | None:
    needle = _normalize_lookup(name)
    if not needle:
        return None
    contacts = _load_contacts()
    best, best_score = None, 0
    for key, entry in contacts.items():
        if not isinstance(entry, dict):
            continue
        names = [entry.get("display_name", ""), key]
        aliases = entry.get("aliases", [])
        names += [str(a) for a in aliases] if isinstance(aliases, list) else [str(aliases)]
        for n in names:
            score = _match_score(needle, n)
            if score > best_score:
                best_score = score
                best = entry
    return best


def save_instagram_contact(display_name: str, user_id: str, aliases: str = "") -> str:
    if not display_name or not display_name.strip():
        return "Kişi adı boş olamaz."

    user_id = re.sub(r"\D+", "", user_id or "")
    if not user_id:
        return "Geçersiz Instagram kullanıcı ID'si."

    alias_list = [p.strip() for p in aliases.split(",") if p.strip()] if aliases.strip() else []
    key = _contact_key(display_name)

    contacts = _load_contacts()
    contacts[key] = {
        "display_name": display_name.strip(),
        "user_id": user_id,
        "aliases": alias_list,
    }
    _save_contacts(contacts)

    suffix = f" Takma adlar: {', '.join(alias_list)}" if alias_list else ""
    return f"{display_name.strip()} Instagram kişilerine kaydedildi (ID: {user_id}).{suffix}"


# ---------------------------------------------------------------------------
# Mesaj gönderme
# ---------------------------------------------------------------------------

def _copy_to_clipboard(text: str) -> bool:
    try:
        safe = text.replace("'", "`'")
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Value '{safe}'"],
            timeout=5,
        )
        return True
    except Exception:
        return False


def send_instagram_message(
    message: str,
    recipient_name: str = "",
    user_id: str = "",
) -> str:
    if not message or not message.strip():
        return "Mesaj boş olamaz."

    resolved_name = (recipient_name or "").strip()
    resolved_id = re.sub(r"\D+", "", user_id or "")

    if resolved_name and not resolved_id:
        contact = _find_contact(resolved_name)
        if contact:
            resolved_id = str(contact.get("user_id", "")).strip()
            resolved_name = str(contact.get("display_name", resolved_name)).strip()

    if not resolved_id:
        if resolved_name:
            return (
                f"'{resolved_name}' için kayıtlı Instagram ID bulunamadı. "
                "Önce kişiyi ID'siyle kaydet."
            )
        return "Instagram mesajı için kişi adı veya kullanıcı ID'si gerekli."

    url = f"https://www.instagram.com/direct/t/{resolved_id}/"
    clipboard_ok = _copy_to_clipboard(message)

    try:
        subprocess.Popen([
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            url
        ])
    except Exception:
        try:
            webbrowser.open(url)
        except Exception as exc:
            return f"Instagram açılamadı: {exc}"

    label = resolved_name or f"ID:{resolved_id}"

    # Sayfa yüklensin
    time.sleep(4)

    # Mesaj kutusuna focus al ve yapıştır
    if clipboard_ok:
        pyautogui.click(1024, 967)
        time.sleep(0.4)
        pyautogui.hotkey('ctrl', 'v')

    return f"Instagram'da {label} için mesaj hazırlandı. Göndereyim mi?"


def confirm_instagram_send() -> str:
    """Kullanıcı onay verdikten sonra Enter'a basar ve mesajı gönderir."""
    time.sleep(0.2)
    pyautogui.press('enter')
    return "Mesaj gönderildi."