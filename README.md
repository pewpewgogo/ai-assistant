# AI Assistant

Voice-controlled Windows desktop assistant. Speak to it, it sees your screen, and performs actions for you.

## Features

- **Voice input** — press a button, speak naturally, release
- **Screen awareness** — captures your screen and understands what's displayed
- **AI-powered** — uses GPT-4o or Claude to reason about your request
- **Action execution** — clicks, types, opens apps, presses hotkeys
- **Spoken responses** — reads answers aloud via text-to-speech
- **System tray** — runs quietly in the background

## Quick Start

### 1. Install

```bash
pip install -e ".[dev]"
```

### 2. Configure

Run the app and open **Settings** from the system tray:

- Add your **OpenAI API key** (required for voice transcription via Whisper)
- Optionally add an **Anthropic API key** if you prefer Claude for reasoning
- Choose your AI model

Settings are saved to `~/.ai-assistant/config.json`.

### 3. Run

```bash
ai-assistant
```

Or directly:

```bash
python src/assistant/main.py
```

### 4. Use

1. Click **"Hold to Talk"** in the assistant window
2. Speak your request (e.g., "Open Chrome and go to Google")
3. The assistant captures your screen, understands your request, and acts

## Build Windows Executable

```bash
pip install pyinstaller
pyinstaller build.spec
```

The executable will be in `dist/AI Assistant.exe`.

## Architecture

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

## Requirements

- Python 3.10+
- Windows 10/11 (primary target), also works on macOS/Linux
- OpenAI API key (for Whisper speech-to-text)
- Microphone access
