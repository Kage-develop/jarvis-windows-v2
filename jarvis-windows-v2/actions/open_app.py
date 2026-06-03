"""
Uygulama açma — Windows için os.startfile / start komutu ile çalışır.
"""

import os
import shutil
import subprocess


APP_ALIASES = {
    "edge":              "msedge",
    "microsoft edge":    "msedge",
    "chrome":            "chrome",
    "google chrome":     "chrome",
    "firefox":           "firefox",
    "terminal":          "cmd",
    "cmd":               "cmd",
    "powershell":        "powershell",
    "explorer":          "explorer",
    "dosya gezgini":     "explorer",
    "file explorer":     "explorer",
    "spotify":           "spotify",
    "vscode":            "code",
    "vs code":           "code",
    "code":              "code",
    "discord":           "discord",
    "slack":             "slack",
    "whatsapp":          "whatsapp",
    "telegram":          "telegram",
    "zoom":              "zoom",
    "notepad":           "notepad",
    "notlar":            "notepad",
    "not defteri":       "notepad",
    "word":              "winword",
    "excel":             "excel",
    "powerpoint":        "powerpnt",
    "calculator":        "calc",
    "hesap makinesi":    "calc",
    "task manager":      "taskmgr",
    "gorev yoneticisi":  "taskmgr",
    "görev yöneticisi":  "taskmgr",
    "settings":          "ms-settings:",
    "ayarlar":           "ms-settings:",
    "paint":             "mspaint",
    "wordpad":           "wordpad",
    "snipping tool":     "SnippingTool",
    "ekran alintisi":    "SnippingTool",
    "ekran alıntısı":    "SnippingTool",
    "photos":            "ms-photos:",
    "fotograflar":       "ms-photos:",
    "fotoğraflar":       "ms-photos:",
    "maps":              "bingmaps:",
    "haritalar":         "bingmaps:",
    "mail":              "outlookmail:",
    "calendar":          "outlookcal:",
    "takvim":            "outlookcal:",
    "store":             "ms-windows-store:",
    "magaza":            "ms-windows-store:",
    "mağaza":            "ms-windows-store:",
    "music":             "mswindowsmusic:",
    "muzik":             "mswindowsmusic:",
    "müzik":             "mswindowsmusic:",
    "notion":            "notion",
    "steam":             "steam",
    "obs":               "obs64",
    "vlc":               "vlc",
    "riot":              "riotclient",
    "riot client":       "riotclient",
    "riot games":        "riotclient",
    "modrinth":          "modrinth:",
    "epic":              "epicgames",
    "epic games":        "epicgames",
    "epic games launcher": "epicgames",
}

URI_SCHEMES = {
    "ms-settings:", "ms-photos:", "bingmaps:", "outlookmail:",
    "outlookcal:", "ms-windows-store:", "mswindowsmusic:", "modrinth:",
}

_APPDATA_PATHS = {
    "discord":   [
        r"%LOCALAPPDATA%\Discord\Update.exe",
        r"%LOCALAPPDATA%\Discord\app-*\Discord.exe",
    ],
    "spotify":   [
        r"%APPDATA%\Spotify\Spotify.exe",
        r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe",
    ],
    "telegram":  [
        r"%APPDATA%\Telegram Desktop\Telegram.exe",
        r"%LOCALAPPDATA%\Telegram Desktop\Telegram.exe",
    ],
    "whatsapp":  [
        r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe",
        r"%APPDATA%\WhatsApp\WhatsApp.exe",
    ],
    "slack":     [
        r"%LOCALAPPDATA%\slack\slack.exe",
    ],
    "zoom":      [
        r"%APPDATA%\Zoom\bin\Zoom.exe",
        r"%LOCALAPPDATA%\Zoom\bin\Zoom.exe",
    ],
    "notion":    [
        r"%LOCALAPPDATA%\Programs\Notion\Notion.exe",
    ],
    "steam":     [
        r"C:\Program Files (x86)\Steam\steam.exe",
        r"C:\Program Files\Steam\steam.exe",
    ],
    "obs64":     [
        r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
    ],
    "vlc":       [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
    ],
    "riotclient": [
        r"C:\Riot Games\Riot Client\RiotClientServices.exe",
        r"%LOCALAPPDATA%\Riot Games\Riot Client\RiotClientServices.exe",
    ],

    "epicgames": [
        r"%LOCALAPPDATA%\EpicGamesLauncher\Saved\Logs\..\..\..\Portal\Binaries\Win64\EpicGamesLauncher.exe",
        r"C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe",
        r"C:\Program Files\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe",
    ],
}


def _find_appdata_exe(app_key: str) -> str | None:
    import glob
    paths = _APPDATA_PATHS.get(app_key.lower(), [])
    for pattern in paths:
        expanded = os.path.expandvars(pattern)
        if "*" in expanded:
            matches = glob.glob(expanded)
            if matches:
                return sorted(matches)[-1]
        elif os.path.exists(expanded):
            return expanded
    return None


def open_app(app_name: str) -> str:
    if not app_name:
        return "Uygulama adı belirtilmedi."

    # Dosya veya klasör yolu ise direkt os.startfile ile aç (.docx, .pdf, vb.)
    if os.path.exists(app_name):
        try:
            os.startfile(app_name)
            return f"{app_name} açıldı."
        except Exception as e:
            return f"'{app_name}' açılamadı: {e}"

    normalized = app_name.lower().strip()
    resolved = APP_ALIASES.get(normalized, normalized)

    # URI scheme
    if any(resolved.startswith(scheme) for scheme in URI_SCHEMES):
        try:
            os.startfile(resolved)
            return f"{app_name} açıldı."
        except Exception as e:
            return f"'{app_name}' açılamadı: {e}"

    # AppData yollarını dene
    exe_path = _find_appdata_exe(resolved)
    if exe_path:
        try:
            if "Discord" in exe_path and "Update.exe" in exe_path:
                subprocess.Popen([exe_path, "--processStart", "Discord.exe"], creationflags=0x08000000)
            else:
                subprocess.Popen([exe_path], creationflags=0x08000000)
            return f"{app_name} açıldı."
        except Exception as e:
            return f"'{app_name}' açılamadı: {e}"

    # PATH'teki executable
    exe_path = shutil.which(resolved)
    if exe_path:
        try:
            subprocess.Popen([exe_path], creationflags=0x08000000)
            return f"{app_name} açıldı."
        except Exception as e:
            return f"'{app_name}' açılamadı: {e}"

    # start komutu
    try:
        result = subprocess.run(
            f'start "" "{resolved}"',
            shell=True, capture_output=True,
            text=True, timeout=10,
        )
        if result.returncode == 0:
            return f"{app_name} açıldı."
    except Exception:
        pass

    # os.startfile son çare
    try:
        os.startfile(resolved)
        return f"{app_name} açıldı."
    except Exception as e:
        return f"'{app_name}' bulunamadı veya açılamadı. Yüklü olduğundan emin ol."
     