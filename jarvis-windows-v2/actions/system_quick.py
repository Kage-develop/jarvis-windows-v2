"""
Hizli sistem kontrolleri — ses, parlaklik, kisayol, pano, wifi/bt, gece isigi, ekran yansitma, zamanlayici, not
"""

from __future__ import annotations

import ctypes
import datetime
import os
import subprocess
import threading
import time
from pathlib import Path

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

user32 = ctypes.windll.user32
KEYEVENTF_KEYUP = 0x0002

VK_LWIN = 0x5B
VK_SHIFT = 0x10
VK_MENU = 0x12  # Alt
VK_ESCAPE = 0x1B
VK_RETURN = 0x0D
VK_F4 = 0x73
VK_F11 = 0x7A
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_CONTROL = 0x11
VK_V = 0x56
VK_TAB = 0x09

NOTES_FILE = Path.home() / "Desktop" / "Jarvis-Notlar.txt"
_DISPLAY_SWITCH = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "DisplaySwitch.exe"

_ACTIVE_TIMERS: dict[str, threading.Timer] = {}
_MAX_TIMERS = 8

APP_VOLUME_ALIASES = {
    "spotify": {"spotify.exe"},
    "spotfay": {"spotify.exe"},
    "spotfayi": {"spotify.exe"},
    "chrome": {"chrome.exe"},
    "google": {"chrome.exe"},
    "google chrome": {"chrome.exe"},
    "edge": {"msedge.exe"},
    "firefox": {"firefox.exe"},
    "discord": {"discord.exe"},
    "whatsapp": {"whatsapp.exe"},
    "telegram": {"telegram.exe"},
    "vlc": {"vlc.exe"},
    "obs": {"obs64.exe", "obs.exe"},
    "zoom": {"zoom.exe", "zoomintl.exe"},
    "valorant": {"valorant.exe", "valorant-win64-shipping.exe", "riotclientservices.exe"},
    "riot": {"riotclientservices.exe", "riotclientux.exe"},
    "minecraft": {"minecraft.exe", "javaw.exe", "java.exe", "minecraftlauncher.exe", "modrinth app.exe"},
    "modrinth": {"modrinth app.exe", "modrinth.exe"},
}

HOTKEY_ALIASES = {
    "desktop": "desktop",
    "masaustu": "desktop",
    "lock": "lock",
    "kilitle": "lock",
    "ekran kilidi": "lock",
    "screenshot": "screenshot",
    "ekran goruntusu": "screenshot",
    "snip": "screenshot",
    "media_next": "media_next",
    "sonraki": "media_next",
    "next_track": "media_next",
    "media_prev": "media_prev",
    "onceki": "media_prev",
    "prev_track": "media_prev",
    "media_play_pause": "media_play_pause",
    "oynat_duraklat": "media_play_pause",
    "play_pause": "media_play_pause",
    "project": "project",
    "win_p": "project",
    "yansitma": "project",
    "ekran yansitma": "project",
    "cast": "cast",
    "baglan": "cast",
    "win_k": "cast",
    "ekran paylasimi": "cast",
    "action_center": "action_center",
    "bildirim": "action_center",
    "win_a": "action_center",
}


def _run_ps(script: str, timeout: int = 20) -> tuple[bool, str]:
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        out = (r.stdout + r.stderr).strip()
        failed = (
            r.returncode != 0
            or "Exception calling" in out
            or "FullyQualifiedErrorId" in out
            or "ERROR:" in out.upper()
        )
        if not failed:
            return True, out or "Tamam."
        return False, out or f"PowerShell cikis kodu: {r.returncode}"
    except subprocess.TimeoutExpired:
        return False, f"Zaman asimi ({timeout}s)."
    except Exception as e:
        return False, f"Hata: {e}"


def _key_down(vk: int) -> None:
    user32.keybd_event(vk, 0, 0, 0)


def _key_up(vk: int) -> None:
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def _tap(vk: int) -> None:
    _key_down(vk)
    _key_up(vk)


def _combo(modifiers: list[int], key: int) -> None:
    for m in modifiers:
        _key_down(m)
    _key_down(key)
    _key_up(key)
    for m in reversed(modifiers):
        _key_up(m)


def _active_window_title() -> str:
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value.strip()
    except Exception:
        return ""


def _press_hotkey(name: str) -> str:
    key = HOTKEY_ALIASES.get((name or "").strip().lower().replace("-", "_"))
    if not key:
        allowed = ", ".join(sorted(set(HOTKEY_ALIASES.values())))
        return f"Bilinmeyen kisayol. Ornekler: {allowed}"

    if key == "desktop":
        _combo([VK_LWIN], ord("D"))
        return "Masaustu gosterildi (Win+D)."
    if key == "lock":
        _combo([VK_LWIN], ord("L"))
        return "Bilgisayar kilitlendi (Win+L)."
    if key == "screenshot":
        _combo([VK_LWIN, VK_SHIFT], ord("S"))
        return "Ekran alintisi araci acildi (Win+Shift+S)."
    if key == "media_next":
        _tap(VK_MEDIA_NEXT_TRACK)
        return "Sonraki parca / ileri."
    if key == "media_prev":
        _tap(VK_MEDIA_PREV_TRACK)
        return "Onceki parca."
    if key == "media_play_pause":
        _tap(VK_MEDIA_PLAY_PAUSE)
        return "Oynat / duraklat."
    if key == "project":
        _combo([VK_LWIN], ord("P"))
        return "Ekran yansitma menusu acildi (Win+P). Mod sec."
    if key == "cast":
        _combo([VK_LWIN], ord("K"))
        return "Ekran baglanti / paylasim paneli acildi (Win+K)."
    if key == "action_center":
        _combo([VK_LWIN], ord("A"))
        return "Hizli ayarlar / bildirim merkezi acildi (Win+A). Gece isigi burada da olabilir."

    return "Kisayol uygulanamadi."


def _focus_discord() -> None:
    try:
        from actions.open_app import open_app

        open_app("discord")
        time.sleep(0.8)
    except Exception:
        pass


def _discord_control(action: str) -> str:
    act = (action or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "mic_toggle": "mic_toggle",
        "mute_toggle": "mic_toggle",
        "microphone_toggle": "mic_toggle",
        "sesimi_ac_kapat": "mic_toggle",
        "mikrofon": "mic_toggle",
        "mute": "mic_toggle",
        "sustur": "mic_toggle",
        "deafen_toggle": "deafen_toggle",
        "deafen": "deafen_toggle",
        "sagirlastir": "deafen_toggle",
        "kulaklik_sustur": "deafen_toggle",
        "screen_share_toggle": "screen_share_toggle",
        "screen_share_stop": "screen_share_toggle",
        "stop_screen_share": "screen_share_toggle",
        "ekran_paylasimini_durdur": "screen_share_toggle",
        "stream_stop": "screen_share_toggle",
    }
    key = aliases.get(act)
    if not key:
        return "discord_control action: mic_toggle | deafen_toggle | screen_share_toggle"

    _focus_discord()

    if key == "mic_toggle":
        _combo([VK_CONTROL, VK_SHIFT], ord("M"))
        return "Discord mikrofon mute/unmute komutu gonderildi (Ctrl+Shift+M)."
    if key == "deafen_toggle":
        _combo([VK_CONTROL, VK_SHIFT], ord("D"))
        return "Discord deafen/undeafen komutu gonderildi (Ctrl+Shift+D)."
    if key == "screen_share_toggle":
        _combo([VK_CONTROL, VK_SHIFT], ord("S"))
        return (
            "Discord ekran paylasimi kısayolu gonderildi (Ctrl+Shift+S). "
            "Paylasim aciksa durur; acik degilse Discord kısayol ayarina gore paylasim menusu acilabilir."
        )

    return "Discord komutu uygulanamadi."


def _active_window_action(action: str) -> str:
    act = (action or "").strip().lower().replace(" ", "_").replace("-", "_")
    title = _active_window_title()
    label = f"aktif pencere ({title})" if title else "aktif pencere"

    aliases = {
        "close": "close",
        "kapat": "close",
        "exit": "close",
        "minimize": "minimize",
        "simge_durumuna_kucult": "minimize",
        "kucult": "minimize",
        "maximize": "maximize",
        "buyut": "maximize",
        "restore": "restore",
        "geri_al": "restore",
        "left": "snap_left",
        "snap_left": "snap_left",
        "sola_yasla": "snap_left",
        "right": "snap_right",
        "snap_right": "snap_right",
        "saga_yasla": "snap_right",
        "top": "maximize",
        "up": "maximize",
        "down": "minimize",
        "fullscreen": "fullscreen",
        "tam_ekran": "fullscreen",
        "move_monitor_left": "move_monitor_left",
        "monitor_left": "move_monitor_left",
        "sol_monitore_tasi": "move_monitor_left",
        "move_monitor_right": "move_monitor_right",
        "monitor_right": "move_monitor_right",
        "sag_monitore_tasi": "move_monitor_right",
        "screenshot": "screenshot",
        "ekran_goruntusu": "screenshot",
        "switch": "switch",
        "pencere_degistir": "switch",
        "title": "title",
        "baslik": "title",
    }
    key = aliases.get(act)
    if not key:
        return (
            "active_window icin action: close, minimize, maximize, restore, "
            "snap_left, snap_right, fullscreen, move_monitor_left/right, screenshot, switch, title"
        )

    if key == "title":
        return f"Aktif pencere: {title or 'baslik alinamadi'}"
    if key == "close":
        _combo([VK_MENU], VK_F4)
        return f"{label} kapatma komutu gonderildi (Alt+F4)."
    if key == "minimize":
        _combo([VK_LWIN], VK_DOWN)
        return f"{label} kucultuldu / asagi alindi (Win+Down)."
    if key == "maximize":
        _combo([VK_LWIN], VK_UP)
        return f"{label} buyutuldu (Win+Up)."
    if key == "restore":
        _combo([VK_LWIN], VK_DOWN)
        time.sleep(0.08)
        _combo([VK_LWIN], VK_DOWN)
        return f"{label} geri alindi veya simge durumuna kucultuldu."
    if key == "snap_left":
        _combo([VK_LWIN], VK_LEFT)
        return f"{label} sola yaslandi (Win+Left)."
    if key == "snap_right":
        _combo([VK_LWIN], VK_RIGHT)
        return f"{label} saga yaslandi (Win+Right)."
    if key == "fullscreen":
        _tap(VK_F11)
        return f"{label} icin tam ekran degistirildi (F11)."
    if key == "move_monitor_left":
        _combo([VK_LWIN, VK_SHIFT], VK_LEFT)
        return f"{label} sol monitore tasinmaya calisildi."
    if key == "move_monitor_right":
        _combo([VK_LWIN, VK_SHIFT], VK_RIGHT)
        return f"{label} sag monitore tasinmaya calisildi."
    if key == "screenshot":
        _combo([VK_LWIN, VK_SHIFT], ord("S"))
        return f"{label} icin ekran alintisi araci acildi."
    if key == "switch":
        _combo([VK_MENU], VK_TAB)
        return "Pencere degistirme komutu gonderildi (Alt+Tab)."

    return "Pencere islemi uygulanamadi."


def _volume_keys(action: str, level: int | None) -> str:
    act = (action or "").strip().lower()
    if act == "mute":
        _tap(VK_VOLUME_MUTE)
        return "Ses susturuldu / acildi (mute)."
    if act in {"up", "volume_up", "artir"}:
        for _ in range(5):
            _tap(VK_VOLUME_UP)
        return "Ses artirildi."
    if act in {"down", "volume_down", "azalt"}:
        for _ in range(5):
            _tap(VK_VOLUME_DOWN)
        return "Ses azaltildi."
    if act in {"set", "volume_set"} and level is not None:
        return _volume_set_level(int(level))
    return "Ses: action=up|down|mute|set ve set icin level=0-100."


def _volume_set_level(pct: int) -> str:
    pct = max(0, min(100, int(pct)))
    try:
        from pycaw.pycaw import AudioUtilities  # type: ignore[import-untyped]

        device = AudioUtilities.GetSpeakers()
        device.EndpointVolume.SetMasterVolumeLevelScalar(pct / 100.0, None)
        return f"Ses %{pct} ayarlandi."
    except Exception:
        pass

    # Klavye fallback: ~2%% adim; once sifira yakin indir, sonra hedefe cik
    for _ in range(50):
        _tap(VK_VOLUME_DOWN)
        time.sleep(0.01)
    steps = max(0, int(round(pct / 2)))
    for _ in range(steps):
        _tap(VK_VOLUME_UP)
        time.sleep(0.01)
    return f"Ses %{pct} ayarlandi."


def _app_volume_names(app_name: str) -> set[str]:
    key = (app_name or "").strip().lower()
    if not key:
        return set()
    if key in APP_VOLUME_ALIASES:
        return APP_VOLUME_ALIASES[key]
    cleaned = key if key.endswith(".exe") else f"{key}.exe"
    return {cleaned}


def _app_volume(action: str, app_name: str = "", level: int | None = None) -> str:
    act = (action or "").strip().lower()
    wanted = _app_volume_names(app_name)

    try:
        import comtypes  # type: ignore[import-untyped]
        from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume  # type: ignore[import-untyped]
    except Exception:
        return "Uygulama sesi icin pycaw/comtypes gerekli."

    try:
        comtypes.CoInitialize()
    except Exception:
        pass

    sessions = AudioUtilities.GetAllSessions()
    found = []
    available = []

    for session in sessions:
        proc = getattr(session, "Process", None)
        if not proc:
            continue
        proc_name = (getattr(proc, "name", lambda: "")() or "").lower()
        if proc_name:
            available.append(proc_name)
        if wanted and proc_name not in wanted:
            continue
        try:
            volume = session._ctl.QueryInterface(ISimpleAudioVolume)
            current = int(round(volume.GetMasterVolume() * 100))
            muted = bool(volume.GetMute())
        except Exception:
            continue
        found.append((proc_name, volume, current, muted))

    if act in {"list", "app_volume_list"}:
        names = sorted(set(available))
        if not names:
            return "Aktif ses oturumu bulunamadi. Uygulamada ses caliyor olmali."
        return "Aktif ses oturumlari:\n" + "\n".join(f"- {name}" for name in names[:30])

    if not wanted:
        return "Uygulama adi gerekli. Ornek: app_name='spotify', level=50."

    if not found:
        known = ", ".join(sorted(set(available))[:12]) or "ses oturumu yok"
        return f"{app_name} icin aktif ses oturumu bulunamadi. Uygulamada ses caliyor olmali. Aktif: {known}"

    if act in {"status", "app_volume_status"}:
        return "\n".join(
            f"{proc}: %{current} {'(mute)' if muted else ''}".strip()
            for proc, _, current, muted in found
        )

    if act in {"set", "app_volume_set"}:
        if level is None:
            return "Ses seviyesi gerekli: 0-100."
        pct = max(0, min(100, int(level)))
        for _, volume, _, _ in found:
            volume.SetMasterVolume(pct / 100.0, None)
            volume.SetMute(0, None)
        names = ", ".join(sorted(set(proc for proc, *_ in found)))
        return f"{names} sesi %{pct} yapildi."

    if act in {"mute", "app_volume_mute"}:
        for _, volume, _, _ in found:
            volume.SetMute(1, None)
        names = ", ".join(sorted(set(proc for proc, *_ in found)))
        return f"{names} sessize alindi."

    if act in {"unmute", "app_volume_unmute"}:
        for _, volume, _, _ in found:
            volume.SetMute(0, None)
        names = ", ".join(sorted(set(proc for proc, *_ in found)))
        return f"{names} sesi acildi."

    return "app_volume action: set | status | mute | unmute | list"


def _brightness(action: str, level: int | None) -> str:
    act = (action or "").strip().lower()
    if act in {"up", "brightness_up", "artir"}:
        ps = """
$cur = (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness -ErrorAction SilentlyContinue | Select-Object -First 1).CurrentBrightness
if (-not $cur) { $cur = 50 }
$new = [Math]::Min(100, $cur + 15)
(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, $new)
Write-Output "Parlaklik %$new"
"""
        ok, msg = _run_ps(ps)
        return msg if ok else "Parlaklik artirilamadi (dizustu ekran / surucu gerekebilir)."
    if act in {"down", "brightness_down", "azalt"}:
        ps = """
$cur = (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness -ErrorAction SilentlyContinue | Select-Object -First 1).CurrentBrightness
if (-not $cur) { $cur = 50 }
$new = [Math]::Max(5, $cur - 15)
(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, $new)
Write-Output "Parlaklik %$new"
"""
        ok, msg = _run_ps(ps)
        return msg if ok else "Parlaklik azaltilamadi."
    if act in {"set", "brightness_set"} and level is not None:
        pct = max(5, min(100, int(level)))
        ps = f"""
(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {pct})
Write-Output "Parlaklik %{pct} ayarlandi."
"""
        ok, msg = _run_ps(ps)
        if ok:
            return msg
        return "Parlaklik ayarlanamadi. Windows Ayarlar > Sistem > Ekrandan deneyin."
    return "Parlaklik: action=up|down|set ve set icin level=5-100."


def _wifi_name() -> str | None:
    try:
        r = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )
        for line in r.stdout.splitlines():
            if line.strip().lower().startswith("name"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return "Wi-Fi"


def _wifi_toggle(enable: bool) -> str:
    iface = _wifi_name() or "Wi-Fi"
    state = "enabled" if enable else "disabled"
    err_text = ""

    try:
        r = subprocess.run(
            ["netsh", "interface", "set", "interface", iface, f"admin={state}"],
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="replace",
        )
        if r.returncode == 0:
            return f"Wi-Fi {'acildi' if enable else 'kapatildi'} ({iface})."
        err_text = (r.stdout + r.stderr).strip()
    except Exception as e:
        err_text = str(e)

    # PowerShell yedek (bazen netsh'ten farkli yetki)
    ps_verb = "Enable" if enable else "Disable"
    ps = f"""
$ErrorActionPreference = 'SilentlyContinue'
$a = Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object {{ $_.Name -eq '{iface}' -or $_.InterfaceDescription -match 'Wi-Fi|Wireless' }} | Select-Object -First 1
if ($a) {{
    {ps_verb}-NetAdapter -Name $a.Name -Confirm:$false
    if ($a.Status -eq '{'Up' if enable else 'Disabled'}' -or $a.AdminStatus -eq '{'Up' if enable else 'Down'}') {{
        Write-Output 'OK'
        exit 0
    }}
}}
Write-Output 'FAIL'
"""
    ok, msg = _run_ps(ps, timeout=12)
    if ok and "OK" in msg:
        return f"Wi-Fi {'acildi' if enable else 'kapatildi'} ({iface})."

    low = (err_text + msg).lower()
    if any(x in low for x in ("admin", "denied", "yetki", "elevated", "access is denied", "yönetici")):
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "ms-settings:network-wifi"],
                close_fds=True,
            )
        except Exception:
            pass
        action = "kapat" if not enable else "ac"
        return (
            f"Wi-Fi adaptoru {action}mak icin yonetici izni gerekiyor. "
            f"Ag ayarlari acildi — Wi-Fi anahtarini oradan veya Win+A Hizli Ayarlar'dan {action}. "
            f"(Jarvis yonetici degil; bu normal.)"
        )

    return err_text or msg or "Wi-Fi durumu degistirilemedi."


def _bluetooth_quick_settings_toggle(enable: bool) -> str:
    _combo([VK_LWIN], ord("A"))
    time.sleep(0.45)
    _tap(VK_RIGHT)
    time.sleep(0.15)
    _tap(VK_RETURN)
    time.sleep(0.65)
    _combo([VK_LWIN], ord("A"))
    action = "acma" if enable else "kapatma"
    return f"Bluetooth {action} kisayolu gonderildi (Win+A, Sag, Enter, Win+A)."


def _bluetooth_toggle(enable: bool) -> str:
    return _bluetooth_quick_settings_toggle(enable)


def _night_light(action: str) -> str:
    _combo([VK_LWIN], ord("A"))
    time.sleep(0.45)
    _tap(VK_DOWN)
    time.sleep(0.12)
    _tap(VK_DOWN)
    time.sleep(0.25)
    _tap(VK_RETURN)
    time.sleep(0.65)
    _combo([VK_LWIN], ord("A"))
    return "Gece isigi kisayolu gonderildi (Win+A, Asagi, Asagi, Enter, Win+A)."


def _night_light_registry(action: str) -> str:
    act = (action or "toggle").strip().lower()
    if act not in {"on", "off", "toggle", "ac", "kapat"}:
        act = "toggle"
    if act == "ac":
        act = "on"
    if act == "kapat":
        act = "off"

    ps = rf"""
$action = '{act}'
$root = Join-Path $env:LOCALAPPDATA 'Packages\Microsoft.Windows.ShellExperienceHost_cw5n1h2txyewy\Settings\settings.dat'
$found = $false
try {{
    $cache = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\CloudStore\Store\Cache\DefaultAccount'
    $dirs = @(
        Get-ChildItem -Path $cache -Directory -ErrorAction SilentlyContinue |
            Where-Object {{ $_.Name -match 'bluelight|BlueLight|nightlight|NightLight' }}
    )
    if (-not $dirs) {{
        $dirs = Get-ChildItem -Path $cache -Directory -Recurse -Depth 3 -ErrorAction SilentlyContinue |
            Where-Object {{ $_.Name -match 'bluelight|BlueLight|nightlight|NightLight' }} |
            Select-Object -First 2
    }}
    foreach ($dir in $dirs) {{
        $dataPath = Join-Path $dir.FullName 'Data'
        if (-not (Test-Path $dataPath)) {{ continue }}
        $item = Get-ItemProperty -Path $dataPath -Name 'Data' -ErrorAction SilentlyContinue
        if (-not $item -or -not $item.Data) {{ continue }}
        $b = [byte[]]$item.Data.Clone()
        if ($b.Length -lt 22) {{ continue }}
        $cur = $b[18] -eq 1
        $want = switch ($action) {{
            'on' {{ $true }}
            'off' {{ $false }}
            default {{ -not $cur }}
        }}
        if ($want -eq $cur) {{
            Write-Output ('Gece isigi zaten ' + ($(if ($want) {{ 'acik' }} else {{ 'kapali' }})))
            $found = $true
            break
        }}
        $b[18] = [byte]($(if ($want) {{ 1 }} else {{ 0 }}))
        Set-ItemProperty -Path $dataPath -Name 'Data' -Value $b -Type Binary
        Write-Output ('Gece isigi ' + ($(if ($want) {{ 'acildi' }} else {{ 'kapatildi' }})))
        $found = $true
        break
    }}
}} catch {{ }}
if (-not $found) {{
    Start-Process 'ms-settings:nightlight'
    Write-Output 'Gece isigi ayarlari acildi; bu Windows surumunde otomatik anahtar bulunamadi.'
}}
"""
    ok, msg = _run_ps(ps, timeout=20)
    return msg if ok else f"Gece isigi: {msg}"


def _display_mode(mode: str) -> str:
    m = (mode or "").strip().lower().replace(" ", "_")
    mapping = {
        "internal": "/internal",
        "pc_only": "/internal",
        "bilgisayar": "/internal",
        "sadece_bilgisayar": "/internal",
        "duplicate": "/clone",
        "clone": "/clone",
        "kopyala": "/clone",
        "extend": "/extend",
        "genislet": "/extend",
        "external": "/external",
        "second_screen": "/external",
        "ikinci_ekran": "/external",
    }
    arg = mapping.get(m)
    if not arg:
        return (
            "display_mode: internal | duplicate | extend | external "
            "(veya bilgisayar, kopyala, genislet, ikinci_ekran)"
        )
    if not _DISPLAY_SWITCH.is_file():
        return "DisplaySwitch.exe bulunamadi."
    try:
        subprocess.run([str(_DISPLAY_SWITCH), arg], timeout=10)
        labels = {
            "/internal": "Yalnizca bilgisayar ekrani",
            "/clone": "Cift ekran (kopyala)",
            "/extend": "Genisletilmis",
            "/external": "Yalnizca ikinci ekran",
        }
        return f"Ekran modu: {labels.get(arg, arg)}."
    except Exception as e:
        return f"Ekran modu hatasi: {e}"


def _stop_casting() -> str:
    results = []
    if _DISPLAY_SWITCH.is_file():
        try:
            subprocess.run([str(_DISPLAY_SWITCH), "/internal"], timeout=10)
            results.append("Yansitma kapatildi (yalnizca bu bilgisayar).")
        except Exception as e:
            results.append(f"DisplaySwitch: {e}")
    _combo([VK_LWIN], ord("K"))
    results.append("Baglanti paneli acildi (Win+K); aktif yansitmayi listeden kes.")
    return " ".join(results)


def _clipboard(action: str, text: str) -> str:
    act = (action or "").strip().lower()
    if act in {"read", "oku", "get"}:
        if HAS_PYPERCLIP:
            try:
                data = pyperclip.paste()
                if not data:
                    return "Pano bos."
                if len(data) > 1500:
                    return data[:1500] + "\n... (kisaltildi)"
                return data
            except Exception as e:
                return f"Pano okunamadi: {e}"
        ok, msg = _run_ps("Get-Clipboard -Raw")
        return msg if ok else f"Pano okunamadi: {msg}"

    if act in {"write", "yaz", "set", "copy"}:
        if not text:
            return "Panoya yazmak icin text gerekli."
        if HAS_PYPERCLIP:
            try:
                pyperclip.copy(text)
                preview = text[:80] + ("..." if len(text) > 80 else "")
                return f"Panoya kopyalandi: {preview}"
            except Exception as e:
                return f"Pano yazilamadi: {e}"
        safe = text.replace("'", "''")
        ok, msg = _run_ps(f"Set-Clipboard -Value '{safe}'")
        return "Panoya kopyalandi." if ok else msg

    if act in {"clear", "temizle"}:
        if HAS_PYPERCLIP:
            try:
                pyperclip.copy("")
                return "Pano temizlendi."
            except Exception:
                pass
        ok, msg = _run_ps("Set-Clipboard -Value $null")
        return "Pano temizlendi." if ok else msg

    if act in {"paste", "yapistir", "yapıştır"}:
        _combo([VK_CONTROL], VK_V)
        return "Panodaki metin yapistirildi (Ctrl+V). Hedef pencere odakta olmali."

    return "clipboard: action=read|write|clear|paste"


def _bluetooth_status() -> str:
    ps = """
$ErrorActionPreference = 'SilentlyContinue'
$devices = @(
    Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue |
        Where-Object { $_.FriendlyName -and $_.FriendlyName -notmatch 'Enumerator|Device \\(RFCOMM' }
)
if ($devices.Count -gt 0) {
    $radio = $devices | Where-Object { $_.FriendlyName -match 'Radio|Adapter|Bluetooth' } | Select-Object -First 1
    if (-not $radio) { $radio = $devices | Select-Object -First 1 }
    Write-Output ("Bluetooth: " + $radio.Status + " (" + $radio.FriendlyName + ")")
    exit 0
}
$svc = Get-Service bthserv -ErrorAction SilentlyContinue
if ($svc) {
    Write-Output ("Bluetooth servisi: " + $svc.Status + ". Radio cihazi listelenemedi; Windows izin/driver nedeniyle olabilir.")
    exit 0
}
Write-Output 'Bluetooth bulunamadi veya bu cihazda Bluetooth destegi yok.'
"""
    ok, msg = _run_ps(ps, timeout=10)
    return msg if ok else f"Bluetooth durumu alinamadi: {msg}"


def _bluetooth_settings(requested_action: str = "") -> str:
    try:
        subprocess.Popen(["cmd", "/c", "start", "ms-settings:bluetooth"], close_fds=True)
    except Exception:
        pass
    suffix = ""
    if requested_action:
        suffix = f" Bluetooth'u {requested_action}mak icin anahtari panelden degistir."
    return "Bluetooth ac/kapat otomatik yapilmiyor; Bluetooth ayarlari acildi." + suffix


def _quick_note(text: str, append: bool = True) -> str:
    if not text or not text.strip():
        return "Not metni bos."
    NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"[{stamp}] {text.strip()}\n"
    mode = "a" if append else "w"
    with open(NOTES_FILE, mode, encoding="utf-8") as f:
        f.write(line)
    return f"Not kaydedildi: {NOTES_FILE.name}"


def _timer_notify(message: str) -> None:
    safe = message.replace("'", "''")[:500]
    ps = f"""
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.MessageBox]::Show(
    '{safe}',
    'JARVIS Hatirlatma',
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Information
) | Out-Null
"""
    _run_ps(ps, timeout=10)
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except Exception:
        pass


def _set_timer(minutes: float, message: str) -> str:
    try:
        mins = float(minutes)
    except (TypeError, ValueError):
        return "Gecerli dakika sayisi gerekli."
    if mins <= 0 or mins > 24 * 60:
        return "Zamanlayici 0-1440 dakika arasi olmali."

    if len(_ACTIVE_TIMERS) >= _MAX_TIMERS:
        return f"En fazla {_MAX_TIMERS} aktif zamanlayici olabilir."

    msg = (message or "Hatirlatma").strip() or "Hatirlatma"
    timer_id = f"t{len(_ACTIVE_TIMERS) + 1}_{int(mins * 60)}"

    def _fire():
        _ACTIVE_TIMERS.pop(timer_id, None)
        _timer_notify(msg)
        try:
            with open(NOTES_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.now():%H:%M}] ZAMANLAYICI: {msg}\n")
        except Exception:
            pass

    t = threading.Timer(mins * 60.0, _fire)
    t.daemon = True
    _ACTIVE_TIMERS[timer_id] = t
    t.start()

    if mins >= 1:
        when = f"{mins:g} dakika"
    else:
        when = f"{int(mins * 60)} saniye"
    return f"Zamanlayici kuruldu: {when} sonra — {msg}"


def system_quick_action(
    action: str,
    level: int | None = None,
    hotkey: str = "",
    text: str = "",
    minutes: float | None = None,
    message: str = "",
    display_mode: str = "",
    window_action: str = "",
    app_name: str = "",
) -> str:
    """
    Tek giris noktasi — tum hizli sistem islemleri.

    action ornekleri:
      volume_up, volume_down, volume_mute, volume_set
      app_volume_set/status/mute/unmute/list
      discord_control (discord_action: mic_toggle/deafen_toggle/screen_share_toggle)
      brightness_up, brightness_down, brightness_set
      hotkey, clipboard_read, clipboard_write, clipboard_clear
      active_window (window_action: close/minimize/maximize/snap_left/snap_right/fullscreen)
      quick_note, set_timer
      wifi_on, wifi_off, bluetooth_on/off/toggle, bluetooth_status, bluetooth_settings
      night_light_on, night_light_off, night_light_toggle
      display_internal, display_duplicate, display_extend, display_external, stop_casting
    """
    act = (action or "").strip().lower().replace(" ", "_")

    if act in {"volume_up", "volume_down", "volume_mute", "volume_set"}:
        sub = act.replace("volume_", "")
        return _volume_keys(sub, level)

    if act in {"app_volume_set", "app_volume_status", "app_volume_mute", "app_volume_unmute", "app_volume_list"}:
        sub = act.replace("app_volume_", "")
        return _app_volume(sub, app_name or text, level)

    if act in {
        "discord_control",
        "discord_mic_toggle",
        "discord_mute_toggle",
        "discord_deafen_toggle",
        "discord_screen_share_toggle",
        "discord_screen_share_stop",
    }:
        sub = act.replace("discord_", "")
        if sub == "control":
            sub = hotkey or text or message
        return _discord_control(sub)

    if act in {"brightness_up", "brightness_down", "brightness_set"}:
        sub = act.replace("brightness_", "")
        return _brightness(sub, level)

    if act == "hotkey":
        return _press_hotkey(hotkey)

    if act == "active_window":
        return _active_window_action(window_action or hotkey)

    if act == "clipboard_read":
        return _clipboard("read", text)
    if act == "clipboard_write":
        return _clipboard("write", text)
    if act == "clipboard_clear":
        return _clipboard("clear", text)
    if act == "clipboard_paste":
        return _clipboard("paste", text)

    if act == "bluetooth_status":
        return _bluetooth_status()
    if act == "bluetooth_settings":
        return _bluetooth_settings()

    if act == "quick_note":
        return _quick_note(text)

    if act == "set_timer":
        if minutes is None:
            return "set_timer icin minutes gerekli."
        return _set_timer(minutes, message or text)

    if act == "wifi_on":
        return _wifi_toggle(True)
    if act == "wifi_off":
        return _wifi_toggle(False)
    if act == "bluetooth_on":
        return _bluetooth_toggle(True)
    if act == "bluetooth_off":
        return _bluetooth_toggle(False)
    if act == "bluetooth_toggle":
        return _bluetooth_quick_settings_toggle(True)

    if act in {"night_light_on", "night_light_off", "night_light_toggle"}:
        sub = act.replace("night_light_", "")
        return _night_light(sub)

    if act.startswith("display_"):
        mode = act.replace("display_", "")
        return _display_mode(mode)

    if act == "stop_casting":
        return _stop_casting()

    if act in {"media_stop", "media_pause", "muzik_durdur", "durdur"}:
        _tap(VK_MEDIA_PLAY_PAUSE)
        return "Muzik duraklatildi / durduruldu."
    if act in {"media_play", "muzik_baslat", "oynat"}:
        _tap(VK_MEDIA_PLAY_PAUSE)
        return "Muzik oynatiliyor."

    if display_mode:
        return _display_mode(display_mode)

    hint = (
        "volume_up/down/mute/set, app_volume_set/status/mute/unmute/list, discord_control, brightness_up/down/set, hotkey, "
        "active_window, "
        "clipboard_read/write/clear/paste, quick_note, set_timer, "
        "wifi_on/off, bluetooth_on/off/toggle/status/settings, night_light_on/off/toggle, "
        "display_internal/duplicate/extend/external, stop_casting, "
        "media_stop, media_play"
    )
    return f"Bilinmeyen action: {act}. Izinli: {hint}"
