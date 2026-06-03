"""
Uygulama kapatma — Windows için taskkill ve psutil kullanır.
"""

import subprocess
import psutil


APP_ALIASES = {
    "edge":                     ["msedge", "msedge.exe"],
    "microsoft edge":           ["msedge", "msedge.exe"],
    "chrome":                   ["chrome", "chrome.exe"],
    "google chrome":            ["chrome", "chrome.exe"],
    "firefox":                  ["firefox", "firefox.exe"],
    "terminal":                 ["cmd", "cmd.exe", "conhost"],
    "cmd":                      ["cmd", "cmd.exe"],
    "powershell":               ["powershell", "powershell.exe", "pwsh"],
    "explorer":                 ["explorer", "explorer.exe"],
    "dosya gezgini":            ["explorer", "explorer.exe"],
    "file explorer":            ["explorer", "explorer.exe"],
    "spotify":                  ["Spotify", "Spotify.exe"],
    "vscode":                   ["code", "code.exe"],
    "vs code":                  ["code", "code.exe"],
    "code":                     ["code", "code.exe"],
    "discord":                  ["Discord", "Discord.exe"],
    "slack":                    ["slack", "slack.exe"],
    "whatsapp":                 ["WhatsApp", "WhatsApp.exe"],
    "telegram":                 ["Telegram", "Telegram.exe"],
    "zoom":                     ["Zoom", "Zoom.exe", "ZoomIntl"],
    "notepad":                  ["notepad", "notepad.exe"],
    "notlar":                   ["notepad", "notepad.exe"],
    "not defteri":              ["notepad", "notepad.exe"],
    "word":                     ["winword", "winword.exe"],
    "excel":                    ["excel", "excel.exe"],
    "powerpoint":               ["powerpnt", "powerpnt.exe"],
    "calculator":               ["calc", "calc.exe"],
    "hesap makinesi":           ["calc", "calc.exe"],
    "task manager":             ["taskmgr", "taskmgr.exe"],
    "gorev yoneticisi":         ["taskmgr", "taskmgr.exe"],
    "görev yöneticisi":         ["taskmgr", "taskmgr.exe"],
    "settings":                 ["SettingsHost", "SettingsHost.exe"],
    "ayarlar":                  ["SettingsHost", "SettingsHost.exe"],
    "paint":                    ["mspaint", "mspaint.exe"],
    "wordpad":                  ["wordpad", "wordpad.exe"],
    "snipping tool":            ["SnippingTool", "SnippingTool.exe"],
    "ekran alintisi":           ["SnippingTool", "SnippingTool.exe"],
    "ekran alıntısı":           ["SnippingTool", "SnippingTool.exe"],
    "photos":                   ["Photos", "Photos.exe"],
    "fotograflar":              ["Photos", "Photos.exe"],
    "fotoğraflar":              ["Photos", "Photos.exe"],
    "maps":                     ["bingmaps", "bingmaps.exe"],
    "haritalar":                ["bingmaps", "bingmaps.exe"],
    "mail":                     ["outlook", "outlook.exe"],
    "calendar":                 ["outlook", "outlook.exe"],
    "takvim":                   ["outlook", "outlook.exe"],
    "store":                    ["WinStore.App", "WinStore.App.exe"],
    "magaza":                   ["WinStore.App", "WinStore.App.exe"],
    "mağaza":                   ["WinStore.App", "WinStore.App.exe"],
    "music":                    ["msmusic", "msmusic.exe", "WinMusicApp"],
    "muzik":                    ["msmusic", "msmusic.exe", "WinMusicApp"],
    "müzik":                    ["msmusic", "msmusic.exe", "WinMusicApp"],
    "notion":                   ["Notion", "Notion.exe"],
    "steam":                    ["steam", "steam.exe"],
    "obs":                      ["obs64", "obs64.exe", "obs", "obs.exe"],
    "vlc":                      ["vlc", "vlc.exe"],
    "riot":                     ["RiotClientServices", "RiotClientServices.exe"],
    "riot client":              ["RiotClientServices", "RiotClientServices.exe"],
    "riot games":               ["RiotClientServices", "RiotClientServices.exe"],
    "epic":                     ["EpicGamesLauncher", "EpicGamesLauncher.exe"],
    "epic games":               ["EpicGamesLauncher", "EpicGamesLauncher.exe"],
    "epic games launcher":      ["EpicGamesLauncher", "EpicGamesLauncher.exe"],
}


def close_app(app_name: str) -> str:
    """
    Uygulamayı kapat. Açık işlemleri psutil ve taskkill ile sonlandırır.
    """
    if not app_name:
        return "Uygulama adı belirtilmedi."

    normalized = app_name.lower().strip()
    exe_names = APP_ALIASES.get(normalized, [app_name])

    if isinstance(exe_names, str):
        exe_names = [exe_names]

    try:
        found = False

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name'].lower()
                for exe_name in exe_names:
                    if proc_name == exe_name.lower() or \
                       proc_name == exe_name.lower().replace(".exe", "") or \
                       proc_name.replace(".exe", "") == exe_name.lower().replace(".exe", ""):
                        try:
                            proc.kill()
                            found = True
                        except psutil.AccessDenied:
                            pass
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        if found:
            return f"{app_name} kapatıldı."

        for exe_name in exe_names:
            clean_exe = exe_name.replace(".exe", "") + ".exe"
            try:
                result = subprocess.run(
                    f'taskkill /IM {clean_exe} /F',
                    shell=True, capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 or "SUCCESS" in result.stdout:
                    return f"{app_name} kapatıldı."
            except subprocess.TimeoutExpired:
                continue
            except Exception:
                continue

        return f"'{app_name}' zaten kapalı veya bulunamadı."

    except Exception as e:
        return f"'{app_name}' kapatılırken hata oluştu: {type(e).__name__}"