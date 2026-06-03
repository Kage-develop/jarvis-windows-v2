# Setup Guide

This guide explains how to run JARVIS Windows locally.

## Requirements

- Windows 10 or newer
- Python 3.11 or newer
- Microphone and speakers
- Internet connection
- Gemini API key

## Install

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create your private config:

```bash
copy config\api_keys.example.json config\api_keys.json
```

Then edit `config/api_keys.json` and add your Gemini API key.

## Run

```bash
python main.py
```

Or run:

```bash
setup.bat
```

## Optional Settings

`config/api_keys.json` supports:

```json
{
  "gemini_api_key": "",
  "voice": "Charon",
  "youtube_api_key": "",
  "youtube_channel_handle": "",
  "weather_location": "Baku",
  "google_calendar_auth": "",
  "microsoft_todo_auth": "",
  "enable_tts": true,
  "enable_voice_input": true,
  "enable_whatsapp": false,
  "model": "gemini-2.5-flash"
}
```

## Supported Tools

| Tool | Description |
| --- | --- |
| `open_app` | Opens Windows apps |
| `close_app` | Closes Windows apps |
| `sys_info` | Reads CPU, RAM, disk, and battery info |
| `browser_control` | Opens URLs and performs browser searches |
| `play_media` | Opens YouTube or Spotify media |
| `shell_run` | Runs Windows shell commands |
| `get_calendar_events` | Opens or reads calendar-related context |
| `add_reminder` | Adds reminders |
| `send_whatsapp_message` | Sends WhatsApp messages when enabled |
| `send_instagram_message` | Opens Instagram DM flows |
| `send_discord_message` | Opens Discord DM flows |

## Troubleshooting

### Gemini API key is missing

Make sure `config/api_keys.json` exists and `gemini_api_key` is filled.

### PyAudio install fails

Use Python 3.11 or install a compatible PyAudio wheel for Windows.

### No sound

Check Windows sound settings, speakers, and microphone permissions.

### WhatsApp does not work

Install WhatsApp Desktop or open WhatsApp Web in your browser. Then set
`enable_whatsapp` to `true` in `config/api_keys.json`.

### Do not share private files

Before publishing, make sure these files are not committed or uploaded:

- `config/api_keys.json`
- `memory/memory.json`
- `memory/phone_book.json`
- `memory/discord_contacts.json`
- `memory/instagram_contacts.json`
