"""
Higher-level app control: open/close/status/list and simple productivity modes.
"""

from __future__ import annotations

import psutil

from actions.close_app import close_app
from actions.open_app import APP_ALIASES, open_app
from actions.system_quick import system_quick_action


APP_PROCESSES = {
    "chrome": ["chrome.exe"],
    "edge": ["msedge.exe"],
    "firefox": ["firefox.exe"],
    "spotify": ["spotify.exe"],
    "discord": ["discord.exe"],
    "vscode": ["code.exe"],
    "vs code": ["code.exe"],
    "whatsapp": ["whatsapp.exe"],
    "telegram": ["telegram.exe"],
    "notion": ["notion.exe"],
    "steam": ["steam.exe"],
    "valorant": ["valorant.exe", "riotclientservices.exe"],
}

MODES = {
    "work": ["vscode", "chrome", "spotify"],
    "calisma": ["vscode", "chrome", "spotify"],
    "study": ["chrome", "notion", "spotify"],
    "ders": ["chrome", "notion", "spotify"],
    "gaming": ["discord", "spotify", "riot"],
    "oyun": ["discord", "spotify", "riot"],
    "chat": ["discord", "whatsapp", "telegram"],
    "sohbet": ["discord", "whatsapp", "telegram"],
}


def _normalize(name: str) -> str:
    return (name or "").strip().lower()


def _process_names_for(app_name: str) -> list[str]:
    key = _normalize(app_name)
    resolved = APP_ALIASES.get(key, key)
    names = APP_PROCESSES.get(key) or APP_PROCESSES.get(resolved) or []
    if names:
        return [name.lower() for name in names]
    return [resolved.lower(), f"{resolved.lower()}.exe"]


def _matching_processes(app_name: str) -> list[str]:
    wanted = set(_process_names_for(app_name))
    found = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = (proc.info.get("name") or "").lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if name in wanted or name.replace(".exe", "") in wanted:
            found.append(f"{proc.info.get('name')} (pid {proc.info.get('pid')})")
    return found


def _list_running(limit: int = 18) -> str:
    names = []
    skip = {"system idle process", "system", "registry"}
    for proc in psutil.process_iter(["name"]):
        try:
            name = proc.info.get("name") or ""
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        low = name.lower()
        if not name or low in skip or low.startswith("svchost"):
            continue
        if name not in names:
            names.append(name)
        if len(names) >= limit:
            break
    return "Acik uygulamalar:\n" + "\n".join(f"- {name}" for name in names)


def app_control(action: str, app_name: str = "", mode: str = "") -> str:
    action = _normalize(action).replace(" ", "_")
    app_name = (app_name or "").strip()
    mode = _normalize(mode)

    if action in {"open", "ac", "start", "baslat"}:
        return open_app(app_name)

    if action in {"close", "kapat", "stop"}:
        return close_app(app_name)

    if action in {"status", "durum", "is_running", "acik_mi"}:
        if not app_name:
            return "Durum icin uygulama adi gerekli."
        matches = _matching_processes(app_name)
        if matches:
            return f"{app_name} acik:\n" + "\n".join(f"- {item}" for item in matches[:8])
        return f"{app_name} acik gorunmuyor."

    if action in {"list", "liste", "running", "aciklar"}:
        return _list_running()

    if action in {"mode", "mod", "preset"}:
        apps = MODES.get(mode)
        if not apps:
            available = ", ".join(sorted(MODES))
            return f"Mod bulunamadi. Secenekler: {available}"
        results = [f"{app}: {open_app(app)}" for app in apps]
        if mode in {"work", "calisma", "study", "ders"}:
            system_quick_action("hotkey", hotkey="desktop")
        return f"{mode.upper()} modu baslatildi.\n" + "\n".join(results)

    return "app_control action: open | close | status | list | mode"
