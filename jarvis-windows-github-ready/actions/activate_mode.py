"""
Otomasyon Modları — Oyun, Araştırma, Sinema
"""

import re
import subprocess

from actions.open_app import open_app
from actions.browser import browser_control
from actions.internet_status import internet_report
from actions.pc_health import pc_health_check
from actions.system_quick import system_quick_action


MODES = {
    "calisma": {
        "description": "Calisma modu: Chrome, Spotify ve VS Code acilir",
        "apps": ["Chrome", "Spotify", "VS Code"],
        "urls": ["https://www.google.com"]
    },
    "arastirma": {
        "description": "Araştırma modu: Chrome, Notion ve YouTube açılır",
        "apps": ["Chrome", "Notion"],
        "urls": ["https://www.youtube.com"]
    },
    "sinema": {
        "description": "Sinema modu: Film sitelerini açar",
        "apps": ["Chrome"],
        "urls": [
            "https://animecix.tv",
            "https://fullhdfilmizlesene.life",
            "https://www.hdfilmcehennemi.nl/"
        ]
    }
}

GAME_PRESETS = {
    "valorant": {
        "apps": ["riot", "Discord", "Spotify"],
        "volumes": {
            "valorant": 100,
            "discord": 70,
            "spotify": 25,
        },
        "ping_targets": ["1.1.1.1", "google.com"],
    },
    "minecraft": {
        "apps": ["modrinth", "Discord", "Spotify"],
        "volumes": {
            "minecraft": 100,
            "discord": 70,
            "spotify": 50,
        },
        "ping_targets": ["1.1.1.1", "google.com"],
    },
}


def _ping_target(target: str, count: int = 4) -> str:
    try:
        result = subprocess.run(
            ["ping", "-n", str(max(1, min(8, count))), target],
            capture_output=True,
            text=True,
            timeout=12,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as e:
        return f"{target}: ping hatasi ({e})"

    output = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode != 0:
        return f"{target}: ulasilamadi"

    times = [int(x) for x in re.findall(r"(?:time|Time|Zaman|Sure|Süre)[=<]\s*(\d+)\s*ms", output)]
    if not times:
        times = [int(x) for x in re.findall(r"(\d+)\s*ms", output)]
    if times:
        avg = sum(times) / len(times)
        return f"{target}: ortalama {avg:.0f} ms"
    return f"{target}: ping tamam"


def _game_ping_report(targets: list[str]) -> str:
    return "Ping: " + " | ".join(_ping_target(target) for target in targets[:3])


def _apply_game_volumes(volumes: dict[str, int]) -> list[str]:
    results = []
    for app, level in volumes.items():
        result = system_quick_action("app_volume_set", level=int(level), app_name=app)
        if "aktif ses oturumu bulunamadi" in result.lower():
            results.append(f"{app} %{level}: ses oturumu bekleniyor")
        else:
            results.append(result)
    return results


def activate_mode(mode_name: str, game: str = "") -> str:
    """
    Seçili modu aktif eder.
    Mod: oyun | arastirma | sinema
    oyun modu için game parametresi gerekli: valorant | minecraft
    """
    if not mode_name:
        return "Mod adı belirtilmedi. Seçenekler: oyun, arastirma, sinema"

    normalized = mode_name.lower().strip()

    # Oyun modu
    if normalized == "oyun":
        if not game or not game.strip():
            internet = internet_report(target="1.1.1.1", dns_host="google.com", count=4)
            health = pc_health_check(detail="summary", limit=3)
            return (
                "Oyun modu on kontrolu:\n\n"
                f"{internet}\n\n"
                f"{health}\n\n"
                "Hangi oyun icin hazirlayayim? Valorant mi Minecraft mi?"
            )

        game_key = game.lower().strip()
        preset = GAME_PRESETS.get(game_key)

        if not preset:
            available = ", ".join(GAME_PRESETS.keys())
            return f"'{game}' için hazır ayar yok. Seçenekler: {available}"

        results = []
        for app in preset["apps"]:
            try:
                open_app(app)
                results.append(f"✓ {app}")
            except Exception as e:
                results.append(f"✗ {app}: {e}")

        volume_results = _apply_game_volumes(preset.get("volumes", {}))
        if volume_results:
            results.append("Ses: " + " | ".join(volume_results))

        ping_targets = preset.get("ping_targets", [])
        if ping_targets:
            results.append(_game_ping_report(ping_targets))

        summary = " | ".join(results)
        return f"OYUN modu aktif ({game.capitalize()}). {summary}"

    # Diğer modlar
    if normalized not in MODES:
        available = "oyun, " + ", ".join(MODES.keys())
        return f"'{mode_name}' modu bulunamadı. Seçenekler: {available}"

    mode = MODES[normalized]
    results = []

    for app in mode.get("apps", []):
        try:
            open_app(app)
            results.append(f"✓ {app}")
        except Exception as e:
            results.append(f"✗ {app}: {e}")

    for url in mode.get("urls", []):
        try:
            browser_control("open_url", url=url)
            results.append(f"✓ {url}")
        except Exception as e:
            results.append(f"✗ {url}: {e}")

    summary = " | ".join(results)
    return f"{normalized.upper()} modu aktif. {summary}"
