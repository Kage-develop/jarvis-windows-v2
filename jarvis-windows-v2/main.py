#!/usr/bin/env python3
"""
JARVIS Windows â€” Gercek zamanli sesli yardimci cekirdegi
Alp ÃœnlÃ¼ tarafÄ±ndan yapÄ±lmÄ±ÅŸtÄ±r â€” @alppunlu
Windows ortamina uyarlanmis calisma akisi
"""

import asyncio
import datetime
import threading
import traceback
import os
import re
from pathlib import Path

try:
    import audioop
except Exception:
    audioop = None

import pyaudio  # type: ignore[reportMissingModuleSource]

from app_config import get_app_config_value, is_whatsapp_enabled
from ui import JarvisUI
from memory.memory_manager import load_memory, update_memory, delete_memory, format_memory_for_prompt

# â”€â”€ Paths â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
BASE_DIR        = Path(__file__).resolve().parent
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"

CONTROL_TOKEN_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)
WAKE_PANEL_RE = re.compile(
    r"\bhey\s+(?:jarvis|cervis)\b(?:\s+(?:burda\s*m[Ä±i]s[Ä±i]n|burada\s*m[Ä±i]s[Ä±i]n|burdam[Ä±i]s[Ä±i]n))?",
    re.IGNORECASE,
)
WAKE_UP_PANEL_RE = re.compile(r"\bwake\s+up\s+(?:jarvis|cervis)\b", re.IGNORECASE)
STOP_PHRASE_RE = re.compile(r"\b(?:sus|dur|stop|kes|cevabi durdur|cevabi kes)\b", re.IGNORECASE)
PAUSE_SELF_RE = re.compile(r"\b(?:kendini durdur|kendini pause et|pause ol|duraklat)\b", re.IGNORECASE)
_GENAI = None
_GENAI_TYPES = None


def _genai_modules():
    global _GENAI, _GENAI_TYPES
    if _GENAI is None or _GENAI_TYPES is None:
        from google import genai  # type: ignore[reportMissingImports]
        from google.genai import types  # type: ignore[reportMissingImports]
        _GENAI = genai
        _GENAI_TYPES = types
    return _GENAI, _GENAI_TYPES

# â”€â”€ Model â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
LIVE_MODEL = "models/gemini-2.5-flash-native-audio-latest"

# â”€â”€ Audio â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
FORMAT           = pyaudio.paInt16
CHANNELS         = 1
SEND_SAMPLE_RATE = 16000
RECV_SAMPLE_RATE = 24000
PLAYBACK_SAMPLE_RATE = 48000
CHUNK_SIZE       = 1024
OUTPUT_CHUNK_SIZE = 2048
OUTPUT_QUEUE_SIZE = 0
OUTPUT_WRITE_BYTES = 4096
OUTPUT_COALESCE_TIMEOUT = 0.015
INPUT_DRAIN_CHUNKS = 8

# â”€â”€ Tool tanÄ±mlarÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_RAW_TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": "Windows'ta herhangi bir uygulamayÄ± aÃ§ar. Spotify, Chrome, Terminal, Dosya Gezgini, VS Code vb.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Uygulama adÄ± (Ã¶rn. 'Spotify', 'Chrome', 'Terminal')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "close_app",
        "description": "Windows'ta aÃ§Ä±k olan uygulamayÄ± kapatÄ±r. Spotify, Chrome, Discord, VS Code vb.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "KapatÄ±lacak uygulama adÄ± (Ã¶rn. 'Spotify', 'Chrome', 'Discord')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "sys_info",
        "description": "Sistem bilgisi alÄ±r: pil durumu, CPU, RAM, disk, saat, tarih, aÄŸ baÄŸlantÄ±sÄ±.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "battery | cpu | ram | disk | time | date | network | all"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "pc_health_check",
        "description": (
            "Bilgisayar saglik kontrolu yapar: CPU, RAM, disk, pil, uptime, en yogun islemler, "
            "Temp/Downloads tahmini ve baslangic uygulamalari. Kullanici 'PC saglik', "
            "'bilgisayar nasil', 'neden kasiyor', 'temizlik raporu' dediginde kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "detail": {
                    "type": "STRING",
                    "description": "summary | full | startup"
                },
                "limit": {
                    "type": "NUMBER",
                    "description": "Liste uzunlugu. Varsayilan 5."
                }
            }
        }
    },
    {
        "name": "internet_report",
        "description": (
            "Anlik internet raporu verir: Wi-Fi/SSID/sinyal, IP/gateway, DNS cozumleme, "
            "ping ortalamasi ve paket kaybi. Kullanici internet, ping, lag, paket kaybi, "
            "baglanti nasil diye sordugunda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target": {
                    "type": "STRING",
                    "description": "Ping hedefi. Varsayilan 1.1.1.1"
                },
                "dns_host": {
                    "type": "STRING",
                    "description": "DNS test hostu. Varsayilan google.com"
                },
                "count": {
                    "type": "NUMBER",
                    "description": "Ping sayisi 1-8"
                }
            }
        }
    },
    {
        "name": "app_control",
        "description": (
            "Akilli uygulama kontrolu: uygulama ac/kapat, acik mi kontrol et, acik uygulamalari listele, "
            "ve work/study/gaming/chat modlarini baslat. Kullanici 'Chrome acik mi', "
            "'calisma modunu baslat', 'acik uygulamalari goster' dediginde kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "open | close | status | list | mode"
                },
                "app_name": {
                    "type": "STRING",
                    "description": "Uygulama adi. Ornek: Chrome, Discord, VS Code"
                },
                "mode": {
                    "type": "STRING",
                    "description": "mode action icin: work | study | gaming | chat veya calisma | ders | oyun | sohbet"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "get_app_context",
        "description": (
            "Aktif pencere/uygulama baglamini verir: uygulama adi, pencere basligi, process ve uygulama tipi. "
            "Kullanici 'bunu', 'sunu', 'buradaki', 'aktif pencere', 'su sekme', 'bu uygulama' gibi baglamli "
            "ifadeler kullandiginda once bunu kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "detail": {
                    "type": "STRING",
                    "description": "summary | full"
                }
            }
        }
    },
    {
        "name": "get_weather",
        "description": (
            "Anlik hava durumunu ozetler. Varsayilan konum Istanbul'dur. "
            "Kullanici hava durumunu, sicakligi veya yagmur durumunu sordugunda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "location": {
                    "type": "STRING",
                    "description": "Sehir veya konum. Bos birakilirsa Istanbul kullanilir."
                }
            }
        }
    },
    {
        "name": "get_calendar_events",
        "description": (
            "Takvim (Google Calendar) etkinliklerini okur. "
            "Bugun, yarin, siradaki etkinlik veya yaklasan ajandayi ozetler. "
            "Kullanici toplanti, takvim, ajanda, etkinlik veya gunluk programini sordugunda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": (
                        "today | tomorrow | next | agenda | week veya dogal dilde "
                        "'onumuzdeki 30 gun', '2 hafta', 'bu ay', 'gelecek ay'"
                    )
                },
                "limit": {
                    "type": "NUMBER",
                    "description": "Maksimum etkinlik sayisi"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "add_calendar_event",
        "description": (
            "Takvim (Google Calendar) servisine yeni etkinlik ekler. "
            "Kullanici toplanti, randevu, takvime ekleme veya etkinlik olusturma isterse kullan. "
            "Baslangic tarihini gercek tarih/saat olarak ver; bitis verilmezse varsayilan sure kullanilir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Etkinlik basligi. Ornek: 'Disci Randevusu'"
                },
                "start_iso": {
                    "type": "STRING",
                    "description": "Baslangic tarih/saat. ISO veya yyyy-MM-dd HH:mm formatinda."
                },
                "end_iso": {
                    "type": "STRING",
                    "description": "Bitis tarih/saat. Opsiyonel."
                },
                "location": {
                    "type": "STRING",
                    "description": "Etkinlik konumu. Opsiyonel."
                },
                "notes": {
                    "type": "STRING",
                    "description": "Etkinlik notlari. Opsiyonel."
                },
                "calendar_name": {
                    "type": "STRING",
                    "description": "Eklenecek takvim adi. Opsiyonel."
                },
                "all_day": {
                    "type": "BOOLEAN",
                    "description": "true ise tum gun etkinligi olusturur."
                }
            },
            "required": ["title", "start_iso"]
        }
    },
    {
        "name": "delete_calendar_event",
        "description": (
            "Takvim (Google Calendar) servisinden etkinlik siler. "
            "Kullanici bir toplantiyi, randevuyu veya takvim kaydini silmek istediginde kullan. "
            "Ayni ada birden fazla etkinlik varsa dogru kaydi bulmak icin baslangic tarihini gercek tarih/saat olarak ver."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Silinecek etkinlik basligi. Ornek: 'Disci Randevusu'"
                },
                "start_iso": {
                    "type": "STRING",
                    "description": "Opsiyonel tarih/saat. Ayni isimli birden fazla etkinligi ayirt etmek icin kullan."
                },
                "calendar_name": {
                    "type": "STRING",
                    "description": "Opsiyonel takvim adi"
                },
                "delete_all_matches": {
                    "type": "BOOLEAN",
                    "description": "true ise eslesen tum etkinlikleri siler"
                }
            },
            "required": ["title"]
        }
    },
    {
        "name": "get_reminders",
        "description": (
            "HatÄ±rlatÄ±cÄ±lar (Microsoft To-Do) listesini okur. "
            "Bugunku, yaklasan, geciken veya tum acik animsaticilari ozetler. "
            "Kullanici hatirlatma, animsatici, reminder veya yapilacaklar listesini sordugunda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "today | upcoming | overdue | all | next"
                },
                "limit": {
                    "type": "NUMBER",
                    "description": "Maksimum animsatici sayisi"
                },
                "list_name": {
                    "type": "STRING",
                    "description": "Istenirse belirli bir animsatici listesi adi"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "add_reminder",
        "description": (
            "HatÄ±rlatÄ±cÄ±lar (Microsoft To-Do) uygulamasina yeni bir animsatici ekler. "
            "Kullanici 'hatirlat', 'animsatici ekle', 'reminder kur' dediginde kullan. "
            "Goreli zaman ifadelerini bugunku tarih baglamina gore due_iso alanina ISO formatinda cevir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Animsatici basligi"
                },
                "due_iso": {
                    "type": "STRING",
                    "description": "Opsiyonel tarih/saat. Ornek: 2026-04-13T09:00 veya tum gun icin 2026-04-13"
                },
                "notes": {
                    "type": "STRING",
                    "description": "Opsiyonel not"
                },
                "list_name": {
                    "type": "STRING",
                    "description": "Opsiyonel animsatici listesi"
                },
                "priority": {
                    "type": "STRING",
                    "description": "low | medium | high"
                },
                "all_day": {
                    "type": "BOOLEAN",
                    "description": "Tum gun animsatici ise true"
                }
            },
            "required": ["title"]
        }
    },
    {
        "name": "browser_control",
        "description": "TarayÄ±cÄ±da URL aÃ§ar, Google'da arama yapar veya YouTube'da ilk sonucu doÄŸrudan oynatÄ±r.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "open_url | search | play_youtube"},
                "url":    {"type": "STRING", "description": "AÃ§Ä±lacak URL (open_url iÃ§in)"},
                "query":  {"type": "STRING", "description": "Arama sorgusu (search veya play_youtube iÃ§in)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "shell_run",
        "description": (
            "Guvenli Windows cmd komutu. Izinli: dir, type, ipconfig, ping, tasklist, whoami, "
            "systeminfo, findstr, where, tree; Masaustu/Belgeler/Indirilenler/OneDrive altinda "
            "mkdir, del, copy, move. PowerShell, taskkill, format, shutdown, zincirleme (; & |) YASAK. "
            "Tek komut, tek satir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {
                    "type": "STRING",
                    "description": "Tek bir cmd komutu. Ornek: dir, ipconfig, ping -n 4 google.com"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "play_media",
        "description": (
            "YouTube, Spotify veya Spotify/YouTube'da ÅŸarkÄ±, mÃ¼zik veya video aÃ§ar. "
            "KullanÄ±cÄ± belirli bir platform sÃ¶ylerse onu kullan. "
            "Belirtmezse uygun olanÄ± dene. "
            "KullanÄ±cÄ± 'Ã§al', 'oynat', 'aÃ§' diyorsa autoplay=true kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "ÅžarkÄ±, sanatÃ§Ä±, albÃ¼m veya video arama ifadesi"
                },
                "provider": {
                    "type": "STRING",
                    "description": "auto | youtube | spotify | apple_music"
                },
                "autoplay": {
                    "type": "BOOLEAN",
                    "description": "true ise mÃ¼mkÃ¼nse doÄŸrudan oynatÄ±r"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_youtube_channel_report",
        "description": (
            "YouTube kanalinin public istatistiklerini ve son videolarin performansini raporlar. "
            "Kullanici kanal istatistiklerini, abone sayisini, son videolarini, buyume hizini "
            "veya YouTube analizini sordugunda kullan. Bu arac Studio yerine public YouTube Data API verisini kullanir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": (
                        "Dogal dilde analiz istegi. Ornek: "
                        "'YouTube istatistiklerim nasil', 'son videolarimi analiz et', "
                        "'kanal buyumemi ozetle'"
                    )
                },
                "handle": {
                    "type": "STRING",
                    "description": (
                        "Opsiyonel kanal handle'i, kanal linki veya kanal ID'si. "
                        "Bos birakilirsa ayarlardaki youtube_channel_handle kullanilir."
                    )
                },
                "video_limit": {
                    "type": "NUMBER",
                    "description": "Analize dahil edilecek son video sayisi. Varsayilan 6."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "analyze_screen",
        "description": (
            "Aktif pencerenin ekran goruntusunu alip Gemini vision ile analiz eder. "
            "Kullanici ekranda ne oldugunu, bir hatayi, gorunen metni, butonlari veya pencere icerigini sordugunda kullan. "
            "Bu surum yalnizca aktif pencereyi destekler."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Kullanicinin ekranla ilgili sorusu. Ornek: 'Bu hatayi oku', 'Ekranda ne var?'"
                },
                "target": {
                    "type": "STRING",
                    "description": "Su an sadece active_window desteklenir."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "jarvis_control",
        "description": (
            "Jarvis'in kendi davranisini kontrol eder. Kullanici sessiz cevap modu, sesli cevap modu, "
            "mevcut yaniti kesme, kendini pause etme veya resume istediginde kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "silent_on | silent_off | stop_speaking | pause | resume"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "save_memory",
        "description": "KullanÄ±cÄ± hakkÄ±nda Ã¶nemli bilgiyi kalÄ±cÄ± belleÄŸe kaydeder. Ä°sim, tercihler, projeler vb. duyunca sessizce Ã§aÄŸÄ±r.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": "identity | preferences | projects | notes"
                },
                "key":   {"type": "STRING", "description": "KÄ±sa anahtar (Ã¶rn. 'name')"},
                "value": {"type": "STRING", "description": "DeÄŸer (Ä°ngilizce)"}
            },
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "delete_memory",
        "description": (
            "Kalici hafizadaki bir kaydi siler. "
            "Kullanici 'bunu hafizandan kaldir', 'unut', 'sil' gibi bir sey derse kullan. "
            "Mumkunse category ve key ile sil; emin degilsen match_text ile ilgili kaydi bulup kaldir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": "Kaydin kategorisi. Ornek: notes | identity | preferences | projects"
                },
                "key": {
                    "type": "STRING",
                    "description": "Silinecek anahtar. Ornek: claude_limit_refresh"
                },
                "match_text": {
                    "type": "STRING",
                    "description": "Kaydi bulmak icin kullanilacak dogal dil parcasi. Ornek: 'claude ai limit yenilenmesi'"
                }
            }
        }
    },
    {
        "name": "send_whatsapp_message",
        "description": (
            "WhatsApp Desktop veya WhatsApp Web Ã¼zerinden mesaj taslaÄŸÄ± aÃ§ar veya mesajÄ± gÃ¶nderir. "
            "KiÅŸi adÄ± veya telefon numarasÄ±yla Ã§alÄ±ÅŸabilir. "
            "Telefon numarasÄ± verilmemiÅŸse kiÅŸi adÄ±nÄ± Ã¶nce kayÄ±tlÄ± WhatsApp kiÅŸileri ve iÃ§e aktarÄ±lan telefon rehberinde ara. "
            "KullanÄ±cÄ± 'gÃ¶nder', 'yolla', 'ile', 'hemen gÃ¶nder' gibi aÃ§Ä±k bir gÃ¶nderme niyeti sÃ¶ylÃ¼yorsa "
            "ekstra onay istemeden send_now=true kullan. "
            "YalnÄ±zca 'hazÄ±rla', 'taslak aÃ§', 'yaz ama gÃ¶nderme' diyorsa send_now=false kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "recipient_name": {
                    "type": "STRING",
                    "description": "KiÅŸi adÄ±. Ã–rn: 'Anne', 'Ahmet', 'Ece'"
                },
                "phone_number": {
                    "type": "STRING",
                    "description": "UluslararasÄ± telefon numarasÄ±. Ã–rn: +905551112233"
                },
                "message": {
                    "type": "STRING",
                    "description": "GÃ¶nderilecek mesaj iÃ§eriÄŸi"
                },
                "app_target": {
                    "type": "STRING",
                    "description": "desktop | web | auto. VarsayÄ±lan auto, tercihen desktop."
                },
                "send_now": {
                    "type": "BOOLEAN",
                    "description": "true ise sohbet aÃ§Ä±ldÄ±ktan sonra mesajÄ± otomatik gÃ¶nderir"
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "activate_mode",
        "description": (
            "Otomasyon modlarÄ±nÄ± aktif eder: oyun, araÅŸtÄ±rma veya sinema. "
            "Kullanici sadece 'oyun moduna gec' derse game bos birak; arac once internet ve PC raporu verip oyun sorar. "
            "Kullanici oyunu soylediginde game parametresiyle tekrar cagir (valorant veya minecraft). "
            "Oyun modunda ping kontrolu yapar ve oyun/Discord/Spotify ses profilini uygular. "
            "Calisma modu: Chrome/Google, Spotify ve VS Code acar. "
            "AraÅŸtÄ±rma modu: Chrome, Notion ve YouTube aÃ§ar. "
            "Sinema modu: Film sitelerini (Animecix, fullhdfilmizlesene, hdfilmcehennemi) aÃ§ar."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "mode_name": {
                    "type": "STRING",
                    "description": "Aktivasyon modu: oyun | calisma | arastirma | sinema"
                },
                "game": {
                    "type": "STRING",
                    "description": "Oyun modu iÃ§in oyun adÄ±: valorant | minecraft. KullanÄ±cÄ± belirtmezse boÅŸ bÄ±rak."
                }
            },
            "required": ["mode_name"]
        }
    },
    {
        "name": "save_whatsapp_contact",
        "description": (
            "SÄ±k kullanÄ±lan bir WhatsApp kiÅŸisini adÄ± ve telefon numarasÄ±yla kalÄ±cÄ± belleÄŸe kaydeder. "
            "KullanÄ±cÄ± bir kiÅŸiyi 'annem', 'Ahmet', 'iÅŸ ortaÄŸÄ±m' gibi tekrar kullanÄ±lacak ÅŸekilde tanÄ±mladÄ±ÄŸÄ±nda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "display_name": {
                    "type": "STRING",
                    "description": "Kaydedilecek kiÅŸi adÄ±. Ã–rn: 'Annem', 'Ahmet'"
                },
                "phone_number": {
                    "type": "STRING",
                    "description": "UluslararasÄ± telefon numarasÄ±. Ã–rn: +905551112233"
                },
                "aliases": {
                    "type": "STRING",
                    "description": "VirgÃ¼lle ayrÄ±lmÄ±ÅŸ alternatif hitaplar. Ã–rn: 'anne, annem, mom'"
                }
            },
            "required": ["display_name", "phone_number"]
        }
    },
    {
        "name": "send_instagram_message",
        "description": (
            "Instagram'da bir kiÅŸiye DM aÃ§ar ve mesajÄ± metin kutusuna yapÄ±ÅŸtÄ±rÄ±r. "
            "KullanÄ±cÄ± 'Instagram'dan yaz', 'DM at', 'Instagram mesajÄ± gÃ¶nder' dediÄŸinde kullan. "
            "KullanÄ±cÄ± aÃ§Ä±k bir gÃ¶nderme niyeti sÃ¶ylÃ¼yorsa direkt Ã§aÄŸÄ±r."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "message": {
                    "type": "STRING",
                    "description": "GÃ¶nderilecek mesaj iÃ§eriÄŸi"
                },
                "recipient_name": {
                    "type": "STRING",
                    "description": "KiÅŸi adÄ±. KayÄ±tlÄ± Instagram kiÅŸilerinde aranÄ±r."
                },
                "user_id": {
                    "type": "STRING",
                    "description": "Instagram kullanÄ±cÄ± ID'si (sayÄ±sal). Ã–rn: '17842138500134669'"
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "save_instagram_contact",
        "description": (
            "Bir Instagram kiÅŸisini adÄ± ve kullanÄ±cÄ± adÄ±yla kalÄ±cÄ± belleÄŸe kaydeder. "
            "KullanÄ±cÄ± bir kiÅŸiyi Instagram'da tekrar kullanÄ±lacak ÅŸekilde tanÄ±mladÄ±ÄŸÄ±nda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "display_name": {
                    "type": "STRING",
                    "description": "KiÅŸi adÄ±. Ã–rn: 'Ahmet', 'Annem'"
                },
                "user_id": {
                    "type": "STRING",
                    "description": "Instagram kullanÄ±cÄ± ID'si (sayÄ±sal)"
                },
                "aliases": {
                    "type": "STRING",
                    "description": "VirgÃ¼lle ayrÄ±lmÄ±ÅŸ alternatif hitaplar. Opsiyonel."
                }
            },
            "required": ["display_name", "user_id"]
        }
    },
    {
        "name": "send_discord_message",
        "description": (
            "Discord'da bir kiÅŸiye DM aÃ§ar ve mesajÄ± metin kutusuna yapÄ±ÅŸtÄ±rÄ±r. "
            "KullanÄ±cÄ± 'Discord'dan yaz', 'Discord DM at', 'Discord mesajÄ± gÃ¶nder' dediÄŸinde kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "message": {
                    "type": "STRING",
                    "description": "GÃ¶nderilecek mesaj iÃ§eriÄŸi"
                },
                "recipient_name": {
                    "type": "STRING",
                    "description": "KiÅŸi adÄ±. KayÄ±tlÄ± Discord kiÅŸilerinde aranÄ±r."
                },
                "user_id": {
                    "type": "STRING",
                    "description": "Discord kullanÄ±cÄ± ID'si (sayÄ±sal)"
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "save_discord_contact",
        "description": (
            "Bir Discord kiÅŸisini adÄ± ve kullanÄ±cÄ± ID'siyle kalÄ±cÄ± belleÄŸe kaydeder. "
            "KullanÄ±cÄ± bir kiÅŸiyi Discord'da tekrar kullanÄ±lacak ÅŸekilde tanÄ±mladÄ±ÄŸÄ±nda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "display_name": {
                    "type": "STRING",
                    "description": "KiÅŸi adÄ±. Ã–rn: 'Ahmet', 'ArkadaÅŸÄ±m'"
                },
                "user_id": {
                    "type": "STRING",
                    "description": "Discord kullanÄ±cÄ± ID'si (sayÄ±sal)"
                },
                "aliases": {
                    "type": "STRING",
                    "description": "VirgÃ¼lle ayrÄ±lmÄ±ÅŸ alternatif hitaplar. Opsiyonel."
                }
            },
            "required": ["display_name", "user_id"]
        }
    },
    {
        "name": "confirm_instagram_send",
        "description": (
            "Kullanici Instagram mesajini onayladiktan sonra Enter'a basarak gonderir. "
            "Kullanici evet, gonder, tamam, yap, evt, olur gibi onay verdikten sonra cagir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "confirm_discord_send",
        "description": (
            "Kullanici Discord mesajini onayladiktan sonra Enter'a basarak gonderir. "
            "Kullanici evet, gonder, tamam, yap, evt, olur gibi onay verdikten sonra cagir. "
            "Oyun modu duo davetinde close_tab=true kullan, diger mesajlarda false."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "close_tab": {
                    "type": "BOOLEAN",
                    "description": "true ise mesaj gondirildikten 3-4 saniye sonra Chrome tabini kapatir. Sadece oyun modu duo davetinde true kullan."
                }
            }
        }
    },
    {
        "name": "create_text_file",
        "description": "Yeni bir TXT dosyasÄ± oluÅŸturur. GÃ¶receli yol verilirse Desktop'a kaydeder.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path":    {"type": "STRING", "description": "Dosya yolu. Ã–rn: 'odev.txt' veya 'C:/Users/sulta/Desktop/odev.txt'"},
                "content": {"type": "STRING", "description": "Dosyaya yazÄ±lacak iÃ§erik. Opsiyonel."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_text_file",
        "description": "TXT dosyasÄ±na yazar. mode='w' Ã¼zerine yazar, mode='a' mevcut iÃ§eriÄŸe ekler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path":    {"type": "STRING", "description": "Dosya yolu"},
                "content": {"type": "STRING", "description": "YazÄ±lacak iÃ§erik"},
                "mode":    {"type": "STRING", "description": "'w' = Ã¼zerine yaz (varsayÄ±lan), 'a' = ekle"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "read_text_file",
        "description": "TXT dosyasÄ±nÄ± okur ve iÃ§eriÄŸini dÃ¶ndÃ¼rÃ¼r.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path": {"type": "STRING", "description": "Dosya yolu"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "create_docx_file",
        "description": "Yeni bir Word belgesi (.docx) oluÅŸturur. BaÅŸlÄ±k ve iÃ§erik eklenebilir.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path":    {"type": "STRING", "description": "Dosya yolu. Ã–rn: 'rapor.docx'"},
                "title":   {"type": "STRING", "description": "Belge baÅŸlÄ±ÄŸÄ±. Opsiyonel."},
                "content": {"type": "STRING", "description": "Belge iÃ§eriÄŸi. SatÄ±r satÄ±r paragraf olarak eklenir. Opsiyonel."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "append_to_docx",
        "description": "Mevcut Word belgesine iÃ§erik ekler. Dosya yoksa oluÅŸturur.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path":    {"type": "STRING", "description": "Dosya yolu"},
                "content": {"type": "STRING", "description": "Eklenecek metin"},
                "heading": {"type": "STRING", "description": "Ä°steÄŸe baÄŸlÄ± bÃ¶lÃ¼m baÅŸlÄ±ÄŸÄ±"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "delete_file",
        "description": "Dosya veya boÅŸ klasÃ¶rÃ¼ siler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path": {"type": "STRING", "description": "Silinecek dosya/klasÃ¶r yolu"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "move_file",
        "description": "DosyayÄ±/klasÃ¶rÃ¼ taÅŸÄ±r veya yeniden adlandÄ±rÄ±r.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "src": {"type": "STRING", "description": "Kaynak yol"},
                "dst": {"type": "STRING", "description": "Hedef yol"},
            },
            "required": ["src", "dst"],
        },
    },
    {
        "name": "copy_file",
        "description": "DosyayÄ± kopyalar.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "src": {"type": "STRING", "description": "Kaynak yol"},
                "dst": {"type": "STRING", "description": "Hedef yol"},
            },
            "required": ["src", "dst"],
        },
    },
    {
        "name": "list_files",
        "description": "KlasÃ¶rdeki dosyalarÄ± listeler. VarsayÄ±lan: Desktop.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path": {"type": "STRING", "description": "KlasÃ¶r yolu. Opsiyonel, varsayÄ±lan Desktop."},
            },
        },
    },
    {
        "name": "file_assistant",
        "description": (
            "Dosya asistani: dosya ara, son dosyalari listele, buyuk dosyalari bul, Downloads ozeti ver, "
            "Downloads klasorunu tiplerine gore duzenleme plani cikar veya uygula. "
            "Kullanici 'son indirilen dosya', 'buyuk dosyalari bul', 'pdf ara', "
            "'indirilenleri duzenle' dediginde kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "search | recent | largest | downloads_summary | organize_downloads",
                },
                "path": {
                    "type": "STRING",
                    "description": "Aranacak klasor. Varsayilan Desktop veya Downloads.",
                },
                "query": {
                    "type": "STRING",
                    "description": "Dosya adinda aranacak ifade.",
                },
                "extension": {
                    "type": "STRING",
                    "description": "Opsiyonel uzanti: pdf, png, docx gibi.",
                },
                "limit": {
                    "type": "NUMBER",
                    "description": "Sonuc sayisi.",
                },
                "min_mb": {
                    "type": "NUMBER",
                    "description": "largest action icin minimum MB.",
                },
                "dry_run": {
                    "type": "BOOLEAN",
                    "description": "organize_downloads icin true sadece plan, false dosyalari tasir.",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "system_quick_action",
        "description": (
            "Hizli Windows kontrolleri. action: volume_up/down/mute/set (level 0-100), "
            "app_volume_set/status/mute/unmute/list (app_name + level), "
            "discord_control veya discord_mic/deafen/screen_share toggle, "
            "brightness_up/down/set (level 5-100), active_window (window_action: close/minimize/maximize/"
            "snap_left/snap_right/fullscreen/title), hotkey (desktop|lock|screenshot|media_next|"
            "media_prev|media_play_pause|project|cast|action_center), clipboard_read/write/clear/paste, "
            "quick_note, set_timer (minutes + message), wifi_on/off, bluetooth_on/off/toggle/status/settings, "
            "night_light_on/off/toggle, display_internal/duplicate/extend/external, stop_casting, "
            "media_stop, media_play."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Ornek: volume_down, brightness_set, discord_control, active_window, hotkey, bluetooth_on, night_light_toggle, stop_casting",
                },
                "level": {
                    "type": "NUMBER",
                    "description": "volume_set, brightness_set veya app_volume_set icin 0-100",
                },
                "app_name": {
                    "type": "STRING",
                    "description": "app_volume_* icin uygulama adi: spotify, chrome/google, discord, edge, firefox vb.",
                },
                "hotkey": {
                    "type": "STRING",
                    "description": "hotkey action icin: desktop, lock, screenshot, media_next, project, cast. discord_control icin: mic_toggle, deafen_toggle, screen_share_toggle",
                },
                "window_action": {
                    "type": "STRING",
                    "description": "active_window icin: close, minimize, maximize, restore, snap_left, snap_right, fullscreen, move_monitor_left, move_monitor_right, screenshot, switch, title",
                },
                "text": {
                    "type": "STRING",
                    "description": "quick_note veya clipboard_write metni",
                },
                "minutes": {
                    "type": "NUMBER",
                    "description": "set_timer icin dakika (0.5 = 30 sn)",
                },
                "message": {
                    "type": "STRING",
                    "description": "set_timer hatirlatma metni",
                },
                "display_mode": {
                    "type": "STRING",
                    "description": "Alternatif: internal, duplicate, extend, external",
                },
            },
            "required": ["action"],
        },
    },
]

_CAST_TOOL_DECLARATIONS = [
    {
        "name": "prepare_screen_cast",
        "description": (
            "Ekran baglanti panelini acar (Win+K). Jarvis otomatik cihaz secmez; "
            "kullanici panelden TV/monitoru kendisi secer."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "device_name": {
                    "type": "STRING",
                    "description": "Ornek: LG OLED TV, Samsung TV",
                },
            },
            "required": ["device_name"],
        },
    },
    {
        "name": "confirm_screen_cast",
        "description": (
            "Uyumluluk icin vardir; otomatik baglanmaz, sadece Win+K panelini tekrar acar."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "device_name": {
                    "type": "STRING",
                    "description": "Opsiyonel. Ornek: [LG] webOS TV OLED55B26LA",
                },
            },
        },
    },
    {
        "name": "cancel_screen_cast",
        "description": "Bekleyen ekran yansitma onayini iptal eder.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "list_cast_devices",
        "description": "Yansitilabilir cihaz adlarini listeler (TV, kablosuz ekran vb.).",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
]

_WHATSAPP_TOOL_NAMES = frozenset({"send_whatsapp_message", "save_whatsapp_contact"})


def _build_tool_declarations() -> list:
    tools = list(_RAW_TOOL_DECLARATIONS)
    if not is_whatsapp_enabled():
        tools = [t for t in tools if t["name"] not in _WHATSAPP_TOOL_NAMES]
    tools.extend(_CAST_TOOL_DECLARATIONS)
    return tools


TOOL_DECLARATIONS = _build_tool_declarations()


def get_api_key() -> str:
    return str(get_app_config_value("gemini_api_key", "") or "")


def load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "Sen JARVIS'sin â€” Windows'ta Ã§alÄ±ÅŸan kiÅŸisel AI asistanÄ±. "
            "TÃ¼rkÃ§e konuÅŸ. KÄ±sa ve net yanÄ±tlar ver. "
            "AraÃ§larÄ± kullanarak gÃ¶revleri tamamla, asla taklit etme."
        )


class JarvisLive:
    def __init__(self, ui: JarvisUI):
        self.ui             = ui
        self.session        = None
        self.audio_in_queue = None
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self._stop_flag     = False
        self._pyaudio        = None

        self.ui.on_text_command  = self._on_text_command
        self.ui.on_pause_toggle  = self._on_pause_toggle
        self.ui.on_stop_command  = self._on_stop_command
        self.ui.on_voice_change  = self._on_voice_change
        self.ui.on_effects_state_change = self._on_effects_state_change
        self._paused             = False
        self._silent_responses   = False

    def _on_pause_toggle(self, paused: bool):
        self._paused = paused

    def _on_stop_command(self):
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._interrupt_audio(), self._loop)

    def _on_voice_change(self, voice: str):
        self.ui.write_debug(f"Voice set to {voice}. It will apply on the next live connection.", level="VOICE")

    def _on_effects_state_change(self, enabled: bool):
        pass

    def _audio(self):
        if self._pyaudio is None:
            self._pyaudio = pyaudio.PyAudio()
        return self._pyaudio

    def _focus_ui_section_for_tool(self, tool_name: str, args: dict):
        if tool_name in {"sys_info", "pc_health_check"}:
            query = str(args.get("query", "")).strip().lower()
            if query in {"time", "saat", "zaman", "date", "tarih"}:
                self.ui.focus_panel("time", duration_ms=5200)
            else:
                self.ui.focus_panel("system", duration_ms=5200)
        elif tool_name == "get_weather":
            self.ui.focus_panel("weather", duration_ms=5600)

    def _on_text_command(self, text: str):
        if self._paused:
            return
        self.ui.write_log(f"Siz: {text}")
        if not self._loop or not self.session:
            self.ui.write_log("ERR: JARVIS baÄŸlantÄ±sÄ± henÃ¼z hazÄ±r deÄŸil.")
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    async def _interrupt_audio(self):
        try:
            if self.audio_in_queue:
                while not self.audio_in_queue.empty():
                    try:
                        self.audio_in_queue.get_nowait()
                    except Exception:
                        break
            if self.session:
                await self.session.send_realtime_input(audio_stream_end=True)
            self.set_speaking(False)
        except Exception:
            pass

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        else:
            self.ui.set_state("LISTENING")

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} â€” {short}")
        self.ui.write_debug(f"{tool_name}: {short}", level="ERROR")
        self.ui.set_state("ERROR")

    @staticmethod
    def _result_looks_like_error(result) -> bool:
        text = str(result or "").strip().lower()
        if not text:
            return False
        error_markers = (
            "hata",
            "error",
            "alinamadi",
            "alÄ±namadÄ±",
            "bulunamadi",
            "bulunamadÄ±",
            "acilamadi",
            "aÃ§Ä±lamadÄ±",
            "tamamlanamadi",
            "tamamlanamadÄ±",
            "gecersiz",
            "geÃ§ersiz",
            "izin gerekiyor",
            "izin gerekli",
            "baglanti",
            "baÄŸlantÄ±",
            "gerekli.",
        )
        return any(marker in text for marker in error_markers)

    @staticmethod
    def _should_play_success_sfx(tool_name: str, args: dict, result) -> bool:
        action_tools = {
            "open_app",
            "add_calendar_event",
            "add_reminder",
            "delete_calendar_event",
            "remove_calendar_event",
            "activate_mode",
            "app_control",
        }
        if tool_name in action_tools:
            return True

        if tool_name == "send_whatsapp_message":
            text = str(result or "").lower()
            if bool(args.get("send_now", False)):
                return "gÃ¶nderildi" in text or "gonderildi" in text
            return False

        return False

    @staticmethod
    def _clean_transcript_text(text: str) -> tuple[str, bool]:
        raw = str(text or "")
        had_noise = False
        if CONTROL_TOKEN_RE.search(raw):
            had_noise = True
            raw = CONTROL_TOKEN_RE.sub(" ", raw)
        cleaned = []
        for ch in raw:
            if ch in "\n\r\t" or ord(ch) >= 32:
                cleaned.append(ch)
            else:
                had_noise = True
        normalized = " ".join("".join(cleaned).split())
        return normalized.strip(), had_noise

    @staticmethod
    def _is_panel_wake_phrase(text: str) -> bool:
        normalized = str(text or "").lower().replace("Ä±", "i")
        return bool(WAKE_PANEL_RE.search(normalized) or WAKE_UP_PANEL_RE.search(normalized))

    @staticmethod
    def _is_stop_phrase(text: str) -> bool:
        normalized = str(text or "").lower().replace("Ã„Â±", "i")
        return bool(STOP_PHRASE_RE.search(normalized))

    @staticmethod
    def _is_pause_self_phrase(text: str) -> bool:
        normalized = str(text or "").lower().replace("Ã„Â±", "i")
        return bool(PAUSE_SELF_RE.search(normalized))

    def _is_hidden_to_tray(self) -> bool:
        is_hidden = getattr(self.ui, "is_hidden_to_tray", lambda: False)
        return bool(is_hidden())

    def _wake_panel_if_needed(self, text: str):
        if not self._is_panel_wake_phrase(text):
            return
        if self._is_hidden_to_tray():
            self.ui.wake_up()

    async def _jarvis_control(self, action: str) -> str:
        act = (action or "").strip().lower().replace(" ", "_").replace("-", "_")
        if act in {"silent_on", "sessiz", "sessiz_mod", "silent"}:
            self._silent_responses = True
            self.ui.write_log("SYS: Sessiz cevap modu acildi.")
            return "Sessiz cevap modu acildi. Yanitlar panelde yazili gosterilecek."
        if act in {"silent_off", "sesli", "sesli_mod", "voice_on"}:
            self._silent_responses = False
            self.ui.write_log("SYS: Sesli cevap modu acildi.")
            return "Sesli cevap modu acildi."
        if act in {"stop_speaking", "stop", "dur", "sus"}:
            await self._interrupt_audio()
            self.ui.write_log("SYS: Mevcut yanit durduruldu.")
            return "Mevcut yanit durduruldu."
        if act in {"pause", "duraklat", "kendini_durdur"}:
            self._paused = True
            set_paused = getattr(self.ui, "set_paused_state", None)
            if set_paused:
                set_paused(True)
            else:
                self.ui.paused = True
                self.ui.set_state("PAUSED")
            return "Jarvis duraklatildi."
        if act in {"resume", "devam"}:
            self._paused = False
            set_paused = getattr(self.ui, "set_paused_state", None)
            if set_paused:
                set_paused(False)
            else:
                self.ui.paused = False
                self.ui.set_state("LISTENING")
            return "Jarvis devam ediyor."
        return "jarvis_control action: silent_on | silent_off | stop_speaking | pause | resume"

    def _build_config(self):
        _, types = _genai_modules()
        memory  = load_memory()
        mem_str = format_memory_for_prompt(memory)
        sys_p   = load_system_prompt()
        now     = datetime.datetime.now()
        time_ctx = f"[ÅžU ANKÄ° ZAMAN]\n{now.strftime('%A, %d %B %Y â€” %H:%M')}\n\n"

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str + "\n\n")
        parts.append(sys_p)

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=str(get_app_config_value("voice", "Charon") or "Charon")
                    )
                )
            ),
        )

    async def _execute_tool(self, fc):
        name = fc.name
        args = dict(fc.args or {})
        print(f"[JARVIS] ðŸ”§ {name} {args}")
        self.ui.set_state("THINKING")

        loop   = asyncio.get_event_loop()
        result = "Tamam."
        had_exception = False

        try:
            if name == "save_memory":
                cat = args.get("category", "notes")
                key = args.get("key", "")
                val = args.get("value", "")
                if key and val:
                    update_memory({cat: {key: {"value": val}}})
                    print(f"[Memory] ðŸ’¾ {cat}/{key} = {val}")
                result = "ok"

            elif name == "delete_memory":
                result = delete_memory(
                    args.get("category", ""),
                    args.get("key", ""),
                    args.get("match_text", ""),
                )

            elif name == "open_app":
                from actions.open_app import open_app
                r = await loop.run_in_executor(
                    None, lambda: open_app(args.get("app_name", "")))
                result = r or f"{args.get('app_name')} aÃ§Ä±ldÄ±."

            elif name == "close_app":
                from actions.close_app import close_app
                r = await loop.run_in_executor(
                    None, lambda: close_app(args.get("app_name", "")))
                result = r or f"{args.get('app_name')} kapatÄ±ldÄ±."

            elif name == "activate_mode":
                from actions.activate_mode import activate_mode
                r = await loop.run_in_executor(
                    None, lambda: activate_mode(
                        args.get("mode_name", ""),
                        args.get("game", ""),
                    ))
                result = r or "Mod aktivasÄ± tamamlandÄ±."

            elif name == "sys_info":
                from actions.sys_info import sys_info
                self._focus_ui_section_for_tool(name, args)
                r = await loop.run_in_executor(
                    None, lambda: sys_info(args.get("query", "all")))
                result = r or "Bilgi alÄ±ndÄ±."

            elif name == "pc_health_check":
                from actions.pc_health import pc_health_check
                self._focus_ui_section_for_tool(name, args)
                r = await loop.run_in_executor(
                    None,
                    lambda: pc_health_check(
                        args.get("detail", "summary"),
                        int(args.get("limit", 5) or 5),
                    ),
                )
                result = r or "PC saglik raporu alindi."

            elif name == "internet_report":
                from actions.internet_status import internet_report
                self._focus_ui_section_for_tool("sys_info", {"query": "network"})
                r = await loop.run_in_executor(
                    None,
                    lambda: internet_report(
                        args.get("target", "1.1.1.1"),
                        args.get("dns_host", "google.com"),
                        int(args.get("count", 4) or 4),
                    ),
                )
                result = r or "Internet raporu alindi."

            elif name == "app_control":
                from actions.app_control import app_control
                r = await loop.run_in_executor(
                    None,
                    lambda: app_control(
                        args.get("action", ""),
                        args.get("app_name", ""),
                        args.get("mode", ""),
                    ),
                )
                result = r or "Uygulama kontrolu tamamlandi."

            elif name == "get_app_context":
                from actions.app_context import get_app_context
                r = await loop.run_in_executor(
                    None,
                    lambda: get_app_context(args.get("detail", "summary")),
                )
                result = r or "Aktif uygulama baglami alinamadi."

            elif name == "get_weather":
                from actions.weather import get_weather_summary
                self._focus_ui_section_for_tool(name, args)
                r = await loop.run_in_executor(
                    None, lambda: get_weather_summary(args.get("location") or None))
                result = r or "Hava durumu bilgisi alindi."

            elif name == "get_calendar_events":
                from actions.calendar import get_calendar_events
                r = await loop.run_in_executor(
                    None,
                    lambda: get_calendar_events(
                        args.get("query", "today"),
                        int(args.get("limit", 6) or 6),
                    ),
                )
                result = r or "Takvim bilgisi alindi."

            elif name == "add_calendar_event":
                from actions.calendar import add_calendar_event
                r = await loop.run_in_executor(
                    None,
                    lambda: add_calendar_event(
                        args.get("title", ""),
                        args.get("start_iso", ""),
                        args.get("end_iso", ""),
                        args.get("notes", ""),
                        args.get("location", ""),
                        args.get("calendar_name", ""),
                        bool(args.get("all_day", False)),
                    ),
                )
                result = r or "Takvim etkinligi eklendi."

            elif name == "delete_calendar_event":
                from actions.calendar import delete_calendar_event
                r = await loop.run_in_executor(
                    None,
                    lambda: delete_calendar_event(
                        args.get("title", ""),
                        args.get("start_iso", ""),
                        args.get("calendar_name", ""),
                        bool(args.get("delete_all_matches", False)),
                    ),
                )
                result = r or "Takvim etkinligi silindi."

            elif name == "get_reminders":
                from actions.reminders import get_reminders
                r = await loop.run_in_executor(
                    None,
                    lambda: get_reminders(
                        args.get("query", "upcoming"),
                        int(args.get("limit", 8) or 8),
                        args.get("list_name", ""),
                    ),
                )
                result = r or "Animsatici bilgisi alindi."

            elif name == "add_reminder":
                from actions.reminders import add_reminder
                r = await loop.run_in_executor(
                    None,
                    lambda: add_reminder(
                        args.get("title", ""),
                        args.get("due_iso", ""),
                        args.get("notes", ""),
                        args.get("list_name", ""),
                        args.get("priority", ""),
                        bool(args.get("all_day", False)),
                    ),
                )
                result = r or "Animsatici eklendi."

            elif name == "browser_control":
                from actions.browser import browser_control
                r = await loop.run_in_executor(
                    None, lambda: browser_control(
                        args.get("action"),
                        args.get("url"),
                        args.get("query")
                    ))
                result = r or "Tamam."

            elif name == "shell_run":
                from actions.shell import shell_run
                r = await loop.run_in_executor(
                    None, lambda: shell_run(args.get("command", "")))
                result = r or "Komut Ã§alÄ±ÅŸtÄ±rÄ±ldÄ±."

            elif name == "play_media":
                from actions.media import play_media
                r = await loop.run_in_executor(
                    None,
                    lambda: play_media(
                        args.get("query", ""),
                        args.get("provider", "auto"),
                        bool(args.get("autoplay", True)),
                    ),
                )
                result = r or "Medya oynatma baÅŸlatÄ±ldÄ±."

            elif name == "get_youtube_channel_report":
                from actions.youtube_stats import get_youtube_channel_report
                r = await loop.run_in_executor(
                    None,
                    lambda: get_youtube_channel_report(
                        args.get("query", "overview"),
                        args.get("handle", ""),
                        int(args.get("video_limit", 6) or 6),
                    ),
                )
                result = r or "YouTube kanal raporu alindi."

            elif name == "analyze_screen":
                from actions.screen_vision import analyze_screen
                r = await loop.run_in_executor(
                    None,
                    lambda: analyze_screen(
                        args.get("query", "Ekranda ne var?"),
                        args.get("target", "active_window"),
                    ),
                )
                result = r or "Ekran analizi tamamlandi."

            elif name == "jarvis_control":
                result = await self._jarvis_control(args.get("action", ""))

            elif name == "send_whatsapp_message":
                if not is_whatsapp_enabled():
                    result = "WhatsApp araclari kapali (config: enable_whatsapp=true yap)."
                else:
                    from actions.whatsapp import send_whatsapp_message
                    r = await loop.run_in_executor(
                        None,
                        lambda: send_whatsapp_message(
                            args.get("message", ""),
                            args.get("phone_number", ""),
                            args.get("recipient_name", ""),
                            bool(args.get("send_now", False)),
                            args.get("app_target", "auto"),
                        ),
                    )
                    result = r or "WhatsApp iÅŸlemi tamamlandÄ±."

            elif name == "save_whatsapp_contact":
                if not is_whatsapp_enabled():
                    result = "WhatsApp araclari kapali."
                else:
                    from actions.whatsapp import save_whatsapp_contact
                    r = await loop.run_in_executor(
                        None,
                        lambda: save_whatsapp_contact(
                            args.get("display_name", ""),
                            args.get("phone_number", ""),
                            args.get("aliases", ""),
                        ),
                    )
                    result = r or "WhatsApp kiÅŸisi kaydedildi."

            elif name == "send_instagram_message":
                from actions.Instagram import send_instagram_message
                r = await loop.run_in_executor(
                    None,
                    lambda: send_instagram_message(
                        args.get("message", ""),
                        args.get("recipient_name", ""),
                        args.get("user_id", ""),
                    ),
                )
                result = r or "Instagram iÅŸlemi tamamlandÄ±."

            elif name == "save_instagram_contact":
                from actions.Instagram import save_instagram_contact
                r = await loop.run_in_executor(
                    None,
                    lambda: save_instagram_contact(
                        args.get("display_name", ""),
                        args.get("user_id", ""),
                        args.get("aliases", ""),
                    ),
                )
                result = r or "Instagram kiÅŸisi kaydedildi."

            elif name == "send_discord_message":
                from actions.discord import send_discord_message
                r = await loop.run_in_executor(
                    None,
                    lambda: send_discord_message(
                        args.get("message", ""),
                        args.get("recipient_name", ""),
                        args.get("user_id", ""),
                    ),
                )
                result = r or "Discord iÅŸlemi tamamlandÄ±."

            elif name == "save_discord_contact":
                from actions.discord import save_discord_contact
                r = await loop.run_in_executor(
                    None,
                    lambda: save_discord_contact(
                        args.get("display_name", ""),
                        args.get("user_id", ""),
                        args.get("aliases", ""),
                    ),
                )
                result = r or "Discord kiÅŸisi kaydedildi."

            elif name == "confirm_instagram_send":
                from actions.Instagram import confirm_instagram_send
                r = await loop.run_in_executor(None, confirm_instagram_send)
                result = r or "Instagram mesajÄ± gÃ¶nderildi."

            elif name == "confirm_discord_send":
                from actions.discord import confirm_discord_send
                close_tab = bool(args.get("close_tab", False))
                r = await loop.run_in_executor(
                    None, lambda: confirm_discord_send(close_tab=close_tab))
                result = r or "Discord mesajÄ± gÃ¶nderildi."

            elif name == "create_text_file":
                from actions.file_manager import create_text_file
                r = await loop.run_in_executor(
                    None, lambda: create_text_file(
                        args.get("path", ""),
                        args.get("content", ""),
                    ))
                result = r or "Dosya oluÅŸturuldu."

            elif name == "write_text_file":
                from actions.file_manager import write_text_file
                r = await loop.run_in_executor(
                    None, lambda: write_text_file(
                        args.get("path", ""),
                        args.get("content", ""),
                        args.get("mode", "w"),
                    ))
                result = r or "Dosyaya yazÄ±ldÄ±."

            elif name == "read_text_file":
                from actions.file_manager import read_text_file
                r = await loop.run_in_executor(
                    None, lambda: read_text_file(args.get("path", "")))
                result = r or "(Dosya boÅŸ)"

            elif name == "create_docx_file":
                from actions.file_manager import create_docx_file
                r = await loop.run_in_executor(
                    None, lambda: create_docx_file(
                        args.get("path", ""),
                        args.get("title", ""),
                        args.get("content", ""),
                    ))
                result = r or "Word belgesi oluÅŸturuldu."

            elif name == "append_to_docx":
                from actions.file_manager import append_to_docx
                r = await loop.run_in_executor(
                    None, lambda: append_to_docx(
                        args.get("path", ""),
                        args.get("content", ""),
                        args.get("heading", ""),
                    ))
                result = r or "Word belgesine eklendi."

            elif name == "delete_file":
                from actions.file_manager import delete_file
                r = await loop.run_in_executor(
                    None, lambda: delete_file(args.get("path", "")))
                result = r or "Silindi."

            elif name == "move_file":
                from actions.file_manager import move_file
                r = await loop.run_in_executor(
                    None, lambda: move_file(
                        args.get("src", ""),
                        args.get("dst", ""),
                    ))
                result = r or "TaÅŸÄ±ndÄ±."

            elif name == "copy_file":
                from actions.file_manager import copy_file
                r = await loop.run_in_executor(
                    None, lambda: copy_file(
                        args.get("src", ""),
                        args.get("dst", ""),
                    ))
                result = r or "KopyalandÄ±."

            elif name == "list_files":
                from actions.file_manager import list_files
                r = await loop.run_in_executor(
                    None, lambda: list_files(args.get("path", "~/Desktop")))
                result = r or "KlasÃ¶r boÅŸ."

            elif name == "file_assistant":
                from actions.file_manager import file_assistant
                r = await loop.run_in_executor(
                    None,
                    lambda: file_assistant(
                        args.get("action", ""),
                        args.get("path", "~/Desktop"),
                        args.get("query", ""),
                        args.get("extension", ""),
                        int(args.get("limit", 20) or 20),
                        int(args.get("min_mb", 10) or 10),
                        bool(args.get("dry_run", True)),
                    ),
                )
                result = r or "Dosya asistani tamamlandi."

            elif name == "prepare_screen_cast":
                from actions.display_cast import prepare_screen_cast
                r = await loop.run_in_executor(
                    None,
                    lambda: prepare_screen_cast(args.get("device_name", "")),
                )
                result = r or "Yansitma hazir."

            elif name == "confirm_screen_cast":
                from actions.display_cast import confirm_screen_cast
                r = await loop.run_in_executor(
                    None,
                    lambda: confirm_screen_cast(args.get("device_name", "")),
                )
                result = r or "Yansitma onaylandi."

            elif name == "cancel_screen_cast":
                from actions.display_cast import cancel_screen_cast
                r = await loop.run_in_executor(None, cancel_screen_cast)
                result = r or "Yansitma iptal."

            elif name == "list_cast_devices":
                from actions.display_cast import list_cast_devices
                r = await loop.run_in_executor(
                    None,
                    lambda: ", ".join(list_cast_devices()) or "Yansitilabilir cihaz bulunamadi.",
                )
                result = r

            elif name == "system_quick_action":
                from actions.system_quick import system_quick_action
                r = await loop.run_in_executor(
                    None,
                    lambda: system_quick_action(
                        args.get("action", ""),
                        int(args["level"]) if args.get("level") is not None else None,
                        args.get("hotkey", ""),
                        args.get("text", ""),
                        float(args["minutes"]) if args.get("minutes") is not None else None,
                        args.get("message", ""),
                        args.get("display_mode", ""),
                        args.get("window_action", ""),
                        args.get("app_name", ""),
                    ),
                )
                result = r or "Tamam."

            else:
                result = f"Bilinmeyen araÃ§: {name}"

        except Exception as e:
            result = f"Hata: {e}"
            had_exception = True
            traceback.print_exc()
            self.speak_error(name, e)

        tool_failed = self._result_looks_like_error(result)
        if tool_failed:
            if not had_exception:
                self.ui.set_state("ERROR")
        elif self._should_play_success_sfx(name, args, result):
            self.ui.play_success_sfx()

        if not tool_failed and not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[JARVIS] ðŸ“¤ {name} â†’ {str(result)[:80]}")
        _, types = _genai_modules()
        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        try:
            while True:
                if self._stop_flag:
                    return
                msg = await self.out_queue.get()
                await self.session.send_realtime_input(media=msg)
        except asyncio.CancelledError:
            return

    def _queue_audio_chunk(self, data):
        if not self.audio_in_queue:
            return
        try:
            self.audio_in_queue.put_nowait(data)
            return
        except asyncio.QueueFull:
            pass
        try:
            self.audio_in_queue.get_nowait()
        except Exception:
            pass
        try:
            self.audio_in_queue.put_nowait(data)
        except asyncio.QueueFull:
            pass

    async def _listen_audio(self):
        print("[JARVIS] ðŸŽ¤ Mikrofon baÅŸladÄ±")
        stream = await asyncio.to_thread(
            self._audio().open,
            format=FORMAT, channels=CHANNELS,
            rate=SEND_SAMPLE_RATE, input=True,
            frames_per_buffer=CHUNK_SIZE,
        )
        was_speaking = False
        try:
            print("[JARVIS] ðŸ”„ Ses buffer temizleniyor...")
            for _ in range(10):
                if self._stop_flag:
                    return
                await asyncio.to_thread(
                    stream.read, CHUNK_SIZE, exception_on_overflow=False)

            while True:
                if self._stop_flag:
                    return

                with self._speaking_lock:
                    jarvis_speaking = self._is_speaking

                if jarvis_speaking:
                    was_speaking = True
                    await asyncio.sleep(0.1)
                    continue

                if was_speaking:
                    was_speaking = False
                    try:
                        await asyncio.to_thread(stream.stop_stream)
                        await asyncio.to_thread(stream.start_stream)
                    except Exception:
                        for _ in range(INPUT_DRAIN_CHUNKS):
                            await asyncio.to_thread(
                                stream.read, CHUNK_SIZE, exception_on_overflow=False)

                data = await asyncio.to_thread(
                    stream.read, CHUNK_SIZE, exception_on_overflow=False)

                if not self.ui.muted and not self._paused:
                    await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
        except asyncio.CancelledError:
            print("[JARVIS] ðŸŽ¤ Mikrofon iptal edildi")
            return
        except Exception as e:
            print(f"[JARVIS] âŒ Mikrofon: {e}")
            raise
        finally:
            await asyncio.to_thread(stream.close)

    async def _receive_audio(self):
        print("[JARVIS] ðŸ‘‚ AlÄ±m baÅŸladÄ±")
        out_buf, in_buf = [], []
        output_noise = False
        output_noise_samples = []
        hidden_turn = False
        woke_turn = False
        try:
            while True:
                async for response in self.session.receive():
                    if response.data:
                        if not self._silent_responses and not self._is_hidden_to_tray():
                            self._queue_audio_chunk(response.data)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            if not self._silent_responses and not self._is_hidden_to_tray():
                                self.set_speaking(True)
                            raw_txt = sc.output_transcription.text.strip()
                            if raw_txt:
                                txt, had_noise = self._clean_transcript_text(raw_txt)
                                if had_noise:
                                    output_noise = True
                                    if len(output_noise_samples) < 4:
                                        output_noise_samples.append(raw_txt)
                                if txt:
                                    out_buf.append(txt)
                                    if len(out_buf) > 80:
                                        out_buf = out_buf[-80:]

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = sc.input_transcription.text.strip()
                            if txt:
                                if not in_buf:
                                    hidden_turn = self._is_hidden_to_tray()
                                    woke_turn = False
                                if self._is_panel_wake_phrase(txt):
                                    woke_turn = True
                                    self._wake_panel_if_needed(txt)
                                if self._is_stop_phrase(txt):
                                    await self._interrupt_audio()
                                if self._is_pause_self_phrase(txt):
                                    await self._jarvis_control("pause")
                                in_buf.append(txt)
                                if len(in_buf) > 80:
                                    in_buf = in_buf[-80:]
                                self.ui.mark_user_activity(True)

                        if sc.turn_complete:
                            self._queue_audio_chunk(None)

                            full_in = " ".join(in_buf).strip()
                            suppress_turn = hidden_turn and not woke_turn
                            if full_in and not suppress_turn:
                                self.ui.write_log(f"Siz: {full_in}")
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            if full_out and not suppress_turn:
                                self.ui.write_log(f"JARVIS: {full_out}")
                                if output_noise_samples:
                                    self.ui.write_debug(
                                        "KÄ±smen filtrelenen ses transcripti: " + " | ".join(output_noise_samples),
                                        level="WARN",
                                    )
                            elif output_noise and not suppress_turn:
                                self.ui.write_log("ERR: JARVIS sesli yanÄ±tÄ±nÄ± Ã§Ã¶zÃ¼mlerken bir hata oluÅŸtu.")
                                if output_noise_samples:
                                    self.ui.write_debug(
                                        "Filtrelenen ham transcript: " + " | ".join(output_noise_samples),
                                        level="WARN",
                                    )
                                self.ui.set_state("ERROR")
                            out_buf = []
                            output_noise = False
                            output_noise_samples = []
                            hidden_turn = False
                            woke_turn = False

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[JARVIS] ðŸ“ž {fc.name}")
                            if (hidden_turn or self._is_hidden_to_tray()) and not woke_turn:
                                _, types = _genai_modules()
                                fr = types.FunctionResponse(
                                    id=fc.id,
                                    name=fc.name,
                                    response={"result": "Jarvis tray modunda. Once 'hey jarvis' veya 'wake up jarvis' ile paneli ac."},
                                )
                            else:
                                fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        await self.session.send_tool_response(
                            function_responses=fn_responses)

        except asyncio.CancelledError:
            print("[JARVIS] ðŸ‘‚ AlÄ±m iptal edildi")
            return
        except Exception as e:
            print(f"[JARVIS] âŒ AlÄ±m: {e}")
            error_str = str(e).lower()
            if any(x in error_str for x in ["1008", "policy", "closed", "connection", "socket"]):
                print("[JARVIS] âš ï¸ WebSocket baÄŸlantÄ±sÄ± kesildi. Yeniden baÄŸlanÄ±yor...")
                self.ui.write_log("ERR: BaÄŸlantÄ± kesildi, yeniden baÄŸlanÄ±lÄ±yor...")
                self.ui.set_state("ERROR")
            else:
                traceback.print_exc()
            raise

    async def _play_audio(self):
        print("[JARVIS] ðŸ”Š Ses Ã§alma baÅŸladÄ±")
        stream = await asyncio.to_thread(
            self._audio().open,
            format=FORMAT, channels=CHANNELS,
            rate=PLAYBACK_SAMPLE_RATE if audioop else RECV_SAMPLE_RATE,
            output=True,
            frames_per_buffer=OUTPUT_CHUNK_SIZE,
        )
        buffer = bytearray()
        rate_state = None

        async def write_buffer():
            nonlocal buffer, rate_state
            if not buffer:
                return
            if len(buffer) % 2:
                buffer = buffer[:-1]
            if not buffer:
                return
            data = bytes(buffer)
            buffer.clear()
            if audioop:
                data, rate_state = audioop.ratecv(
                    data,
                    2,
                    CHANNELS,
                    RECV_SAMPLE_RATE,
                    PLAYBACK_SAMPLE_RATE,
                    rate_state,
                )
            await asyncio.to_thread(stream.write, data, exception_on_underflow=False)

        try:
            while True:
                if self._stop_flag:
                    return
                chunk = await self.audio_in_queue.get()
                if chunk is None:
                    await write_buffer()
                    self.set_speaking(False)
                    continue
                self.set_speaking(True)
                buffer.extend(chunk)

                end_turn = False
                while len(buffer) < OUTPUT_WRITE_BYTES:
                    try:
                        next_chunk = await asyncio.wait_for(
                            self.audio_in_queue.get(),
                            timeout=OUTPUT_COALESCE_TIMEOUT,
                        )
                    except asyncio.TimeoutError:
                        break

                    if next_chunk is None:
                        end_turn = True
                        break
                    buffer.extend(next_chunk)

                await write_buffer()
                if end_turn:
                    self.set_speaking(False)
        except asyncio.CancelledError:
            print("[JARVIS] ðŸ”Š Ses Ã§alma iptal edildi")
            return
        except Exception as e:
            print(f"[JARVIS] âŒ Ses: {e}")
            raise
        finally:
            self.set_speaking(False)
            await asyncio.to_thread(stream.close)

    async def run(self):
        api_key = get_api_key()
        if not api_key:
            self.ui.write_log("ERR: Gemini API key bulunamadÄ±. AyarlarÄ± kontrol edin.")
            return

        genai, _ = _genai_modules()
        client = genai.Client(
            api_key=api_key,
            http_options={"api_version": "v1alpha"}
        )

        while True:
            if self._stop_flag:
                print("[JARVIS] ðŸ›‘ KapatÄ±lÄ±yor...")
                break

            if self._paused:
                await asyncio.sleep(1)
                continue

            try:
                print("[JARVIS] ðŸ”Œ BaÄŸlanÄ±yor...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session        = session
                    self._loop          = asyncio.get_event_loop()
                    self.audio_in_queue = asyncio.Queue(maxsize=OUTPUT_QUEUE_SIZE)
                    self.out_queue      = asyncio.Queue(maxsize=10)

                    print("[JARVIS] âœ… BaÄŸlandÄ±.")
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: Sistemler Ã§evrimiÃ§i. Komutunuzu bekliyorum, Efendim.")

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())

            except Exception as e:
                print(f"[JARVIS] âš ï¸ {e}")
                traceback.print_exc()
                self.set_speaking(False)
                self.ui.write_log(f"ERR: JARVIS baglantisi kesildi veya internete ulasilamiyor â€” {e}")

                await asyncio.sleep(2)
                self.ui.set_state("ERROR")
                print("[JARVIS] ðŸ”„ 3 saniyede yeniden baÄŸlanÄ±yor...")
                await asyncio.sleep(3)


def main():
    if os.environ.get("TERM_PROGRAM") == "vscode":
        print("[JARVIS] VS Code icinden baslatildi.")

    print("[JARVIS] UI baslatiliyor...")
    ui = JarvisUI()
    print("[JARVIS] UI hazir.")

    print("[JARVIS] Wake listener kaldirildi; tray modunda ana mikrofon dinliyor.")

    jarvis_instance = None

    def runner():
        nonlocal jarvis_instance
        print("[JARVIS] Runner baslatildi.")
        ui.wait_for_api_key()
        print("[JARVIS] API key hazir.")
        jarvis_instance = JarvisLive(ui)
        try:
            asyncio.run(jarvis_instance.run())
        except KeyboardInterrupt:
            print("\n Kapatiliyor...")
        except Exception as e:
            print(f"[JARVIS] Runner hatasi: {e}")
            traceback.print_exc()

    runner_thread = threading.Thread(target=runner, daemon=True)
    runner_thread.start()

    print("[JARVIS] mainloop basliyor...")
    try:
        ui.run()
    finally:
        print("[JARVIS] mainloop bitti.")
        if jarvis_instance:
            jarvis_instance._stop_flag = True


if __name__ == "__main__":
    main()
