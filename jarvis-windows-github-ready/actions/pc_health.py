"""
PC health assistant: system load, storage, startup apps and cleanup hints.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import psutil


def _gb(value: float) -> str:
    return f"{value / (1024 ** 3):.1f}GB"


def _folder_size(path: Path, limit: int = 1200) -> int:
    total = 0
    seen = 0
    if not path.exists():
        return 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
                seen += 1
                if seen >= limit:
                    return total
            except OSError:
                continue
    return total


def _top_processes(limit: int = 5) -> list[str]:
    samples = []
    skip = {"system idle process", "idle", "system"}
    for proc in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if name in skip:
                continue
            proc.cpu_percent(None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    psutil.cpu_percent(interval=0.35)
    for proc in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if name in skip:
                continue
            mem = proc.info["memory_info"].rss if proc.info.get("memory_info") else 0
            samples.append((proc.cpu_percent(None), mem, proc.info.get("name") or "unknown"))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    samples.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [
        f"{name}: CPU %{cpu:.1f}, RAM {_gb(mem)}"
        for cpu, mem, name in samples[:limit]
    ]


def _startup_apps(limit: int = 12) -> list[str]:
    ps = r"""
$paths = @(
 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run',
 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run',
 'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run'
)
foreach ($p in $paths) {
  if (Test-Path $p) {
    Get-ItemProperty $p | Select-Object -Property * -ExcludeProperty PS* |
      Format-List
  }
}
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=8,
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return []

    apps = []
    for line in result.stdout.splitlines():
        if ":" not in line:
            continue
        name = line.split(":", 1)[0].strip()
        if name and name not in apps:
            apps.append(name)
        if len(apps) >= limit:
            break
    return apps


def pc_health_check(detail: str = "summary", limit: int = 5) -> str:
    detail = (detail or "summary").strip().lower()
    limit = max(3, min(12, int(limit or 5)))

    cpu = psutil.cpu_percent(interval=0.45)
    vm = psutil.virtual_memory()
    disk = shutil.disk_usage("C:\\")
    battery = psutil.sensors_battery()
    boot_time = psutil.boot_time()

    lines = ["PC SAGLIK RAPORU"]
    lines.append(f"CPU: %{cpu:.1f}")
    lines.append(f"RAM: {_gb(vm.used)} / {_gb(vm.total)} (%{vm.percent:.0f})")
    lines.append(f"Disk C: {_gb(disk.used)} kullanildi, {_gb(disk.free)} bos (%{disk.used / disk.total * 100:.0f})")

    if battery:
        state = "sarjda" if battery.power_plugged else "pil"
        lines.append(f"Pil: %{battery.percent:.0f} ({state})")
    else:
        lines.append("Pil: bilgi yok veya masaustu PC")

    uptime_hours = max(0, int((__import__("time").time() - boot_time) // 3600))
    lines.append(f"Calisma suresi: {uptime_hours} saat")

    temp_dir = Path(os.environ.get("TEMP", ""))
    downloads = Path.home() / "Downloads"
    temp_size = _folder_size(temp_dir)
    downloads_size = _folder_size(downloads)

    warnings = []
    if cpu >= 85:
        warnings.append("CPU yuksek")
    if vm.percent >= 85:
        warnings.append("RAM dolu")
    if disk.free / disk.total <= 0.12:
        warnings.append("C diskinde bos alan az")
    if temp_size > 2 * 1024 ** 3:
        warnings.append("Temp klasoru buyuk")
    if downloads_size > 8 * 1024 ** 3:
        warnings.append("Downloads klasoru buyuk")

    lines.append("Durum: " + (", ".join(warnings) if warnings else "iyi gorunuyor"))

    if detail in {"summary", "all", "full", "detay", "detayli"}:
        lines.append("")
        lines.append("En yogun islemler:")
        lines.extend(f"- {line}" for line in _top_processes(limit))
        lines.append("")
        lines.append(f"Temp tahmini: {_gb(temp_size)}")
        lines.append(f"Downloads tahmini: {_gb(downloads_size)}")

    if detail in {"all", "full", "detayli", "startup", "baslangic"}:
        apps = _startup_apps(limit=limit)
        lines.append("")
        lines.append("Baslangic uygulamalari:")
        lines.extend(f"- {app}" for app in apps) if apps else lines.append("- Bulunamadi veya erisim yok")

    return "\n".join(lines)
