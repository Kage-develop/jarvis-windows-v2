"""
Discord mesaj gönderme — tarayıcıda DM açar, mesajı panoya kopyalar ve yapıştırır.
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
DISCORD_CONTACTS_FILE = BASE_DIR / "memory" / "discord_contacts.json"


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
        if DISCORD_CONTACTS_FILE.exists():
            return json.loads(DISCORD_CONTACTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_contacts(contacts: dict):
    DISCORD_CONTACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    DISCORD_CONTACTS_FILE.write_text(
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


def save_discord_contact(display_name: str, user_id: str, aliases: str = "") -> str:
    if not display_name or not display_name.strip():
        return "Kişi adı boş olamaz."

    user_id = re.sub(r"\D+", "", user_id or "")
    if not user_id:
        return "Geçersiz Discord kullanıcı ID'si."

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
    return f"{display_name.strip()} Discord kişilerine kaydedildi (ID: {user_id}).{suffix}"


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


def send_discord_message(
    message: str,
    recipient_name: str = "",
    user_id: str = "",
) -> str:
    """
    Discord DM'ini tarayıcıda açar, mesajı panoya kopyalar ve yapıştırır.
    Kullanıcı onaylarsa confirm_discord_send çağrılır.
    """
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
                f"'{resolved_name}' için kayıtlı Discord ID bulunamadı. "
                "Önce kişiyi ID'siyle kaydet."
            )
        return "Discord mesajı için kişi adı veya kullanıcı ID'si gerekli."

    url = f"https://discord.com/channels/@me/{resolved_id}"
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
            return f"Discord DM açılamadı: {exc}"

    label = resolved_name or f"ID:{resolved_id}"

    # Sayfa yüklensin
    time.sleep(3.5)

    # Mesaj kutusuna focus al ve yapıştır
    if clipboard_ok:
        screen_w, screen_h = pyautogui.size()
        # Discord mesaj kutusu ekranın alt ortasında olur
        pyautogui.click(screen_w // 2, screen_h - 80)
        time.sleep(0.4)
        pyautogui.hotkey('ctrl', 'v')

    return f"Discord'da {label} için mesaj hazırlandı. Göndereyim mi?"


def confirm_discord_send(close_tab: bool = False, **kwargs) -> str:
    """
    Kullanıcı onay verdikten sonra Enter'a basar ve mesajı gönderir.

    Args:
        close_tab: Mesaj gönderildikten sonra sekmeyi kapat (Ctrl+W). Varsayılan: False.
        **kwargs:  Gelecekteki parametreler için uyumluluk güvencesi.
    """
    time.sleep(0.2)
    pyautogui.press('enter')

    if close_tab:
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'w')
        return "Mesaj gönderildi ve sekme kapatıldı."

    return "Mesaj gönderildi."