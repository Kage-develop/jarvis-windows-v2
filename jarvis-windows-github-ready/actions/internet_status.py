"""
Instant internet report: adapter/IP, DNS, ping latency and packet loss.
"""

from __future__ import annotations

import re
import socket
import subprocess
import time


def _run(args: list[str], timeout: int = 10) -> tuple[int, str]:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode, (result.stdout + "\n" + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "Zaman asimi."
    except Exception as e:
        return 1, str(e)


def _wifi_summary() -> str:
    code, out = _run(["netsh", "wlan", "show", "interfaces"], timeout=6)
    if code != 0 or not out:
        return "WiFi: bilgi alinamadi"

    data = {}
    for line in out.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip().lower()] = value.strip()

    ssid = data.get("ssid")
    signal = data.get("signal")
    state = data.get("state") or data.get("durum")
    radio = data.get("radio type") or data.get("radyo turu")
    parts = []
    if ssid:
        parts.append(f"SSID {ssid}")
    if signal:
        parts.append(f"sinyal {signal}")
    if radio:
        parts.append(radio)
    if state and not parts:
        parts.append(state)
    return "WiFi: " + (", ".join(parts) if parts else "bagli bilgi yok")


def _ip_summary() -> str:
    code, out = _run(["ipconfig"], timeout=6)
    if code != 0:
        return "IP: alinamadi"
    ips = []
    gateways = []
    for line in out.splitlines():
        low = line.lower()
        if "ipv4" in low and ":" in line:
            ip = line.split(":", 1)[1].strip()
            if ip and not ip.startswith("169."):
                ips.append(ip)
        if ("default gateway" in low or "varsay" in low) and ":" in line:
            gw = line.split(":", 1)[1].strip()
            if gw:
                gateways.append(gw)
    text = "IP: " + (", ".join(ips[:3]) if ips else "yok")
    if gateways:
        text += f" | Gateway: {gateways[0]}"
    return text


def _dns_check(host: str) -> str:
    started = time.perf_counter()
    try:
        ip = socket.gethostbyname(host)
        ms = (time.perf_counter() - started) * 1000
        return f"DNS: {host} -> {ip} ({ms:.0f} ms)"
    except Exception as e:
        return f"DNS: cozumlenemedi ({e})"


def _ping(host: str, count: int = 4) -> dict:
    count = max(1, min(8, int(count or 4)))
    code, out = _run(["ping", "-n", str(count), host], timeout=14)
    text = out.lower()
    loss = None
    avg = None

    loss_match = re.search(r"(\d+)%\s*(?:loss|kay)", text)
    if loss_match:
        loss = int(loss_match.group(1))

    avg_match = re.search(r"(?:average|ortalama)[^=\d]*[=<]\s*(\d+)\s*ms", text)
    if avg_match:
        avg = int(avg_match.group(1))
    else:
        times = [int(x) for x in re.findall(r"(?:time|zaman|sure|süre)[=<]\s*(\d+)\s*ms", text)]
        if not times:
            times = [int(x) for x in re.findall(r"(\d+)\s*ms", text)]
        if times:
            avg = round(sum(times) / len(times))

    return {
        "host": host,
        "ok": code == 0,
        "loss": loss,
        "avg": avg,
    }


def internet_report(target: str = "1.1.1.1", dns_host: str = "google.com", count: int = 4) -> str:
    target = (target or "1.1.1.1").strip()
    dns_host = (dns_host or "google.com").strip()
    count = max(1, min(8, int(count or 4)))

    pings = [_ping(target, count)]
    if target != "google.com":
        pings.append(_ping("google.com", min(3, count)))

    lines = ["INTERNET RAPORU"]
    lines.append(_wifi_summary())
    lines.append(_ip_summary())
    lines.append(_dns_check(dns_host))

    for item in pings:
        if item["ok"]:
            loss = f", kayip %{item['loss']}" if item["loss"] is not None else ""
            avg = f", ort {item['avg']} ms" if item["avg"] is not None else ""
            lines.append(f"Ping {item['host']}: OK{avg}{loss}")
        else:
            lines.append(f"Ping {item['host']}: basarisiz")

    primary = pings[0]
    if not primary["ok"]:
        verdict = "baglanti sorunlu"
    elif primary["loss"] and primary["loss"] > 0:
        verdict = "paket kaybi var"
    elif primary["avg"] is not None and primary["avg"] > 120:
        verdict = "gecikme yuksek"
    elif primary["avg"] is not None and primary["avg"] > 60:
        verdict = "orta seviye gecikme"
    else:
        verdict = "iyi"
    lines.append(f"Durum: {verdict}")
    return "\n".join(lines)
