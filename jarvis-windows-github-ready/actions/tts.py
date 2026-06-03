"""
TTS (Text-to-Speech) — Windows için PowerShell SAPI veya cmd pyttsx3 kullanır.
"""

import subprocess
import threading
import sys


def speak_text(text: str, on_done=None, blocking: bool = False):
    """
    Metni sesli olarak okur (Windows SAPI).
    on_done: okuma bitince çağrılacak fonksiyon (opsiyonel)
    blocking: True ise bitene kadar bekler
    """
    if not text or not text.strip():
        if on_done:
            on_done()
        return

    max_len = 500
    if len(text) > max_len:
        text = text[:max_len] + "..."

    def _run():
        try:
            # PowerShell dene
            safe_text = text.replace("'", "''").replace('"', '`"')
            script = (
                "Add-Type -AssemblyName System.Speech; "
                f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$s.Speak('{safe_text}')"
            )
            subprocess.run(
                ["powershell", "-WindowStyle", "Hidden", "-Command", script],
                check=False,
                timeout=60,
                creationflags=0x08000000,
            )
        except FileNotFoundError:
            # PowerShell yoksa cmd dene
            try:
                safe_text = text.replace('"', '\\"')
                cmd = f'echo {safe_text} | espeak'
                subprocess.run(
                    cmd,
                    shell=True,
                    check=False,
                    timeout=60,
                )
            except Exception:
                pass
        except Exception:
            pass
        
        if on_done:
            on_done()

    if blocking:
        _run()
    else:
        threading.Thread(target=_run, daemon=True).start()


def get_available_voices() -> list[str]:
    """Windows'taki mevcut SAPI seslerini listeler."""
    try:
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }"
        )
        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []
