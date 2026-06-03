
# JARVIS Windows

JARVIS Windows is a desktop voice assistant for Windows. It uses Google Gemini for
live voice interaction and includes tools for app control, browser actions,
system information, media control, weather, reminders, screen vision, and optional
messaging helpers.

## Features

- Voice-first assistant UI for Windows
- Gemini Live voice model support
- App open/close and system quick actions
- Browser, YouTube, Spotify, weather, reminders, and PC health tools
- Optional WhatsApp, Instagram, and Discord contact helpers
- Local memory files for user preferences and saved contacts

## Requirements

- Windows 10 or newer
- Python 3.11 or newer
- Microphone and speakers
- Gemini API key

Some optional features require installed desktop apps or browser login sessions,
for example WhatsApp Desktop/Web, Discord, Instagram, Google Calendar, or
Microsoft To Do.

## Setup

1. Clone the repository.

```bash
git clone https://github.com/YOUR_USERNAME/jarvis-windows.git
cd jarvis-windows
```

2. Create and activate a virtual environment.

```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies.

```bash
pip install -r requirements.txt
```

4. Create your private config file.

```bash
copy config\api_keys.example.json config\api_keys.json
```

5. Open `config/api_keys.json` and add your Gemini API key.

```json
{
  "gemini_api_key": "YOUR_GEMINI_API_KEY"
}
```

6. Start the app.

```bash
python main.py
```

You can also run `setup.bat` on Windows to create the virtual environment,
install packages, and create the local config file.

## Private Files

Do not upload these files to GitHub. They are ignored by `.gitignore` because
they may contain API keys, personal memory, phone numbers, or account IDs:

- `config/api_keys.json`
- `memory/memory.json`
- `memory/phone_book.json`
- `memory/discord_contacts.json`
- `memory/instagram_contacts.json`

Use the matching `.example.json` files as templates when sharing the project.

## Configuration

The main config lives in `config/api_keys.json`:

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

## Notes

- `enable_whatsapp` is disabled by default for privacy.
- The app is designed for Windows automation, so some actions will not work on
  macOS or Linux.
- If PyAudio fails to install, install the matching Windows wheel for your
  Python version or use a Python version with a compatible PyAudio build.

## License

No license is included yet. Add a license file before publishing if you want
others to reuse, modify, or redistribute the project.
