# AI Assistant

Voice-controlled Windows desktop assistant. Speak to it, it sees your screen, and performs actions for you.

## Download & Install (Windows)

**No programming knowledge needed.**

1. Go to the [Releases page](../../releases/latest)
2. Download **`AI.Assistant.exe`**
3. Double-click to run it
4. Right-click the blue **A** icon in your system tray → **Settings**
5. Paste your OpenAI API key and click **Save**
6. Click **"Hold to Talk"** and speak

That's it. The assistant will listen, see your screen, and help you.

> **Need an OpenAI API key?** Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys), create an account, and generate a key.

## What It Does

- **Voice input** — press a button, speak naturally
- **Screen awareness** — sees what's on your screen and understands it
- **AI-powered** — uses GPT-4o or Claude to figure out what you need
- **Takes action** — clicks, types, opens apps, presses keyboard shortcuts
- **Talks back** — reads answers aloud

## One-Click Installer

For an even simpler install, download `install.bat` and double-click it. It will:
- Download the latest version
- Create a Desktop shortcut
- Add it to your Start Menu

---

## For Developers

### Run from source

```bash
pip install -e ".[dev]"
ai-assistant
```

### Build the .exe yourself

```bash
pip install pyinstaller
pyinstaller build.spec
```

### Architecture

```
src/
  assistant/
    main.py       — Entry point
    config.py     — Settings management
    engine.py     — Core listen→think→act loop
    voice.py      — Microphone capture + Whisper transcription
    screen.py     — Screenshot capture
    brain.py      — AI provider (OpenAI / Anthropic) with vision
    speaker.py    — Text-to-speech output
  actions/
    executor.py   — Desktop automation (click, type, hotkey, open)
  ui/
    tray.py       — PyQt6 system tray app + chat window + settings
```

### Requirements (source only)

- Python 3.10+
- Windows 10/11 (primary target), also works on macOS/Linux
- OpenAI API key (for Whisper speech-to-text)
- Microphone access
