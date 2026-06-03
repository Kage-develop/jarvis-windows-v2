"""
Tarayıcı kontrolü — Windows için webbrowser modülü ile çalışır.
"""

import re
import subprocess
import urllib.parse
import webbrowser

import requests

_VIDEO_ID_RE = re.compile(r'"videoId":"([A-Za-z0-9_-]{11})"')


def _validate_url(url: str) -> str:
    """URL'yi valide et ve normalize et."""
    url = url.strip()
    
    # URL'de = veya ? varsa önceki kısımları sil (genellikle komut hatası)
    if "=" in url and not url.startswith("http"):
        url = url.split("=")[-1].strip()
    
    # Protokol ekle
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    return url


def _open(url: str) -> None:
    try:
        subprocess.Popen(
            ["chrome.exe", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        try:
            subprocess.Popen(
                [r"C:\Program Files\Google\Chrome\Application\chrome.exe", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            webbrowser.open(url)

def _find_first_youtube_video(query: str) -> str | None:
    encoded = urllib.parse.quote_plus(query)
    response = requests.get(
        f"https://www.youtube.com/results?search_query={encoded}",
        headers={"User-Agent": "JARVIS/1.0"},
        timeout=10,
    )
    response.raise_for_status()

    seen: set[str] = set()
    for video_id in _VIDEO_ID_RE.findall(response.text):
        if video_id not in seen:
            seen.add(video_id)
            return video_id
    return None


def browser_control(action: str, url: str = None, query: str = None) -> str:
    if action == "open_url":
        if not url:
            return "URL belirtilmedi."
        url = _validate_url(url)
        _open(url)
        return f"Açıldı: {url}"

    elif action == "search":
        if not query:
            return "Arama sorgusu belirtilmedi."
        encoded = urllib.parse.quote(query)
        search_url = f"https://www.google.com/search?q={encoded}"
        _open(search_url)
        return f"'{query}' için arama açıldı."

    elif action in ("play_youtube", "youtube_play", "play_music"):
        if not query:
            return "YouTube için arama sorgusu belirtilmedi."

        try:
            video_id = _find_first_youtube_video(query)
        except Exception as exc:
            encoded = urllib.parse.quote(query)
            fallback_url = f"https://www.youtube.com/results?search_query={encoded}"
            _open(fallback_url)
            return (
                f"YouTube ilk sonucu alınamadı ({type(exc).__name__}). "
                f"Arama sonuçları açıldı: {query}"
            )

        if not video_id:
            encoded = urllib.parse.quote(query)
            fallback_url = f"https://www.youtube.com/results?search_query={encoded}"
            _open(fallback_url)
            return f"YouTube'da doğrudan video bulunamadı. Arama sonuçları açıldı: {query}"

        watch_url = f"https://www.youtube.com/watch?v={video_id}&autoplay=1"
        _open(watch_url)
        return f"YouTube'da oynatılıyor: {query}"

    return f"Bilinmeyen eylem: {action}"
