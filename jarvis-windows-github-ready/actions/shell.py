"""
Terminal komutu çalıştırma — Windows cmd/PowerShell
"""

import os
import re
import subprocess


BLOCKED = [
    "format c:",
    "format d:",
    "del /f /s /q c:\\",
    "rmdir /s /q c:\\",
    "rd /s /q c:\\",
    "shutdown",
    "net user administrator",
    "reg delete hklm",
    "bcdedit",
    "diskpart",
]

# Linux -> Windows komut çevirisi (yaygın komutlar)
CMD_TRANSLATIONS = {
    "ls": "dir",
    "ls -la": "dir /A",
    "ls -l": "dir /B",
    "pwd": "cd",
    "cat": "type",
    "grep": "findstr",
    "find": "where",
    "mkdir": "mkdir",
    "rmdir": "rmdir",
    "rm": "del",
    "cp": "copy",
    "mv": "move",
    "chmod": "icacls",
    "whoami": "whoami",
    "echo": "echo",
    "date": "date /t",
    "time": "time /t",
    "ipconfig": "ipconfig",
    "ping": "ping",
    "tasklist": "tasklist",
    "taskkill": "taskkill",
}

# Bilinen ortam değişkenleri → gerçek yol
ENV_EXPANSIONS = {
    "%USERPROFILE%": os.path.expanduser("~"),
    "%DESKTOP%":     os.path.join(os.path.expanduser("~"), "Desktop"),
    "%TEMP%":        os.environ.get("TEMP", os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp")),
    "%APPDATA%":     os.environ.get("APPDATA", ""),
    "%LOCALAPPDATA%": os.environ.get("LOCALAPPDATA", ""),
}


def _fix_path_escaping(command: str) -> str:
    """
    JSON double-escape sorununu düzelt:
      %USERPROFILE%\\\\Desktop  →  %USERPROFILE%\\Desktop
      C:\\\\Users\\\\           →  C:\\Users\\
    Tek backslash zaten doğruysa dokunma.
    """
    # 4 backslash → 1 backslash (JSON çift escape)
    command = command.replace("\\\\\\\\", "\\")
    # 2 backslash → 1 backslash (tek katlı double-escape)
    command = re.sub(r"(?<!\\)\\\\(?!\\)", r"\\", command)
    return command


def _expand_env(command: str) -> str:
    """Bilinen env değişkenlerini gerçek yollara çevir."""
    for var, path in ENV_EXPANSIONS.items():
        if var in command.upper():
            command = re.sub(re.escape(var), path.replace("\\", "\\\\"), command, flags=re.IGNORECASE)
    # Windows'un kendi %VAR% genişletmesini de uygula
    command = os.path.expandvars(command)
    return command


def _translate_linux_cmd(command: str) -> str:
    """Linux komutlarını Windows komutlarına çevir."""
    cmd_lower = command.lower().strip()

    for linux_cmd, windows_cmd in CMD_TRANSLATIONS.items():
        if cmd_lower == linux_cmd:
            return command.replace(linux_cmd, windows_cmd, 1)
        if cmd_lower.startswith(linux_cmd + " "):
            return command.replace(linux_cmd, windows_cmd, 1)

    return command


def shell_run(command: str, timeout: int = 30) -> str:
    if not command:
        return "Komut belirtilmedi."

    # 1. Escape düzelt
    command = _fix_path_escaping(command)

    # 2. Env değişkenlerini genişlet
    command = _expand_env(command)

    cmd_lower = command.lower().strip()

    # 3. Güvenlik kontrolü
    for blocked in BLOCKED:
        if blocked in cmd_lower:
            return f"Güvenlik: Bu komut engellendi → {blocked}"

    # 4. Linux → Windows çevirisi
    command = _translate_linux_cmd(command)

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        output = (result.stdout + result.stderr).strip()

        if not output:
            return "Komut başarıyla çalıştı (çıktı yok)."

        if len(output) > 800:
            output = output[:800] + "\n... (çıktı kısaltıldı)"

        return output

    except subprocess.TimeoutExpired:
        return f"Komut zaman aşımına uğradı ({timeout}s)."
    except FileNotFoundError:
        return "Komut bulunamadı. Doğru yazıldığından emin ol."
    except Exception as e:
        return f"Hata: {type(e).__name__}: {str(e)[:100]}"