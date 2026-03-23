# CNC Assistant Redesign — Design Spec

**Date:** 2026-03-23
**Status:** Draft
**Goal:** Transform the existing AI assistant into an accessible desktop helper for a basic PC user operating a Two Trees TTC450 Pro CNC router with Candle software.

---

## Context

### User Profile
- Basic PC user — can open apps and do simple things, but gets lost with unfamiliar interfaces
- Operates a Two Trees TTC450 Pro desktop CNC router
- Uses Candle (GRBL controller) as the CNC control software
- Primary language: Russian
- Needs both CNC-specific help and general Windows desktop assistance

### Existing App
A working Python desktop assistant with:
- Voice input (microphone + OpenAI Whisper, Russian)
- Screen capture (mss screenshots sent to AI for vision analysis)
- AI reasoning (OpenAI GPT-4o / Anthropic Claude with vision)
- Desktop automation (pyautogui — click, type, hotkey, scroll, open, wait)
- Text-to-speech (pyttsx3, offline)
- System tray UI with chat window (PyQt6, Russian)
- Persistent settings (JSON config at ~/.ai-assistant/config.json)
- PyInstaller build for Windows .exe

### Problem
The current UI is too small and complex for a basic user. There is no visual guidance on screen (overlay). The system prompt lacks CNC domain knowledge. The only activation method is hold-to-talk.

---

## Design

### 1. Main Window UI Redesign

**File:** `src/ui/tray.py` (rewrite)

Replace the current small chat window with a large, simple interface:

- **Giant talk button** — large, centered, impossible to miss. Single click to start recording, auto-stops on silence (existing silence detection). Label: "НАЖМИ ЧТОБЫ ГОВОРИТЬ".
- **Status indicator** — large colored dot + text at the top. Green "Готов помочь" (ready), orange "Слушаю..." (listening), blue "Думаю..." (thinking), yellow "Выполняю..." (acting), purple "Говорю..." (speaking).
- **Chat log** — large readable text (16px minimum). Clear icons: 🗣 for user, 🤖 for assistant. Shows last few exchanges, scrollable.
- **Settings link** — small, at the bottom. Opens the existing settings dialog. Does not clutter the main view.
- **Window behavior** — always-on-top option (toggleable). Stays visible while user works in Candle. Can be minimized to tray.

**Design principles:**
- Minimum font size: 14px for body, 18px for status, 22px for button
- High contrast dark theme (keep existing Catppuccin palette)
- Maximum 3 interactive elements visible at once (talk button, stop button, settings)
- No technical jargon in UI labels

### 2. Screen Overlay System

**New file:** `src/ui/overlay.py`

A transparent, click-through PyQt6 window that covers the full screen and draws visual guides on top of any application.

**Overlay types:**

| Type | Visual | Use Case |
|------|--------|----------|
| Point highlight | Pulsing colored circle + arrow + label | "Click this button" |
| Area highlight | Pulsing rectangle border + label | "Look at this area" |
| Step sequence | Numbered circles (1→2→3) with labels | Multi-step guidance |
| Text tooltip | Floating label near a coordinate | Explanation without highlight |

**Technical approach:**
- PyQt6 frameless, transparent window with `Qt.WindowStaysOnTopHint` and `Qt.WindowTransparentForInput`
- Covers the full primary screen
- Renders highlights using QPainter with animation (pulsing opacity)
- Click-through: all mouse events pass to underlying windows
- Auto-dismiss: overlay clears after configurable timeout (default 8 seconds) or on next voice command
- API: `overlay.show_highlight(type, x, y, w, h, label)` and `overlay.clear()`

**AI integration:**
- The system prompt instructs the AI to include overlay coordinates in its response when guiding
- Response format: JSON action `{"action": "highlight", "type": "point", "x": 150, "y": 40, "label": "Нажмите сюда"}`
- The executor module parses highlight actions and calls the overlay API
- When in "do" mode, the AI executes clicks directly (existing behavior). When in "guide" mode, it shows highlights instead.

### 3. Guide vs Do Mode

**Modified file:** `src/assistant/engine.py`

The assistant operates in two modes, switchable by voice:

- **Guide mode (default):** The assistant explains what to do and shows overlay highlights. The user performs the actions themselves. Triggered by questions like "как сделать?", "покажи где", "помоги".
- **Do mode:** The assistant performs actions directly using pyautogui. Triggered by commands like "сделай это", "нажми", "открой файл".

The AI determines the mode from the user's intent in their voice command. The system prompt provides examples of both modes. No explicit toggle button needed — natural language switching.

### 4. CNC Knowledge Base

**New directory:** `src/knowledge/`

**Files:**
- `src/knowledge/ttc450_manual.txt` — extracted text from the TTC450 Pro PDF manual, organized by section (safety, setup, operation, maintenance, troubleshooting)
- `src/knowledge/candle_guide.txt` — Candle GRBL controller usage guide (loading G-code, setting zero, jogging, running jobs, GRBL settings)
- `src/knowledge/loader.py` — module that loads relevant knowledge sections based on the user's question

**How it works:**
1. User asks a question
2. The loader does keyword matching to select relevant knowledge sections
3. Selected sections are appended to the system prompt context
4. The AI receives: system prompt + relevant knowledge + chat history + screenshot
5. Token budget: knowledge sections are trimmed to stay within ~2000 tokens

**System prompt enhancement:**
- Identity: "You are a helpful assistant for operating a Two Trees TTC450 Pro CNC router and general PC tasks"
- Personality: patient, simple language, one step at a time, Russian only
- CNC expertise: understands Candle UI, GRBL commands, G-code basics
- Overlay awareness: knows how to output highlight coordinates
- Mode awareness: guide (show highlights) vs do (execute actions)

### 5. Global Hotkey

**New file:** `src/assistant/hotkey.py`

- **F1 key** — global keyboard shortcut to start/stop listening (works even when the assistant window is not focused)
- Implementation: `pynput` library for global hotkey capture (cross-platform)
- Toggle behavior: first press starts listening, second press stops (or auto-stop on silence)
- Audio feedback: short beep/chime on activation so the user knows it's listening
- Configurable key in settings (default F1)

### 6. Activation Methods Summary

| Method | How | When |
|--------|-----|------|
| Big button click | Single click the talk button in the main window | Window is visible |
| F1 hotkey | Press F1 anywhere | Hands on keyboard, any app focused |
| System tray | Click tray icon to show window, then use button | Window was minimized |

### 7. Settings Additions

**Modified file:** `src/assistant/config.py`

New settings added to the existing config schema:

- `hotkey` — global hotkey key name (default: "f1")
- `overlay_enabled` — enable/disable overlay highlights (default: true)
- `overlay_timeout` — seconds before overlay auto-clears (default: 8)
- `overlay_color` — highlight color hex (default: "#ff6b6b")
- `default_mode` — "guide" or "do" (default: "guide")
- `knowledge_dir` — path to knowledge base files (default: bundled)

### 8. Action Executor Changes

**Modified file:** `src/actions/executor.py`

New action type added:

```json
{"action": "highlight", "type": "point|area|steps|tooltip", "x": 150, "y": 40, "w": 100, "h": 30, "label": "Нажмите сюда"}
```

The executor routes `highlight` actions to the overlay module instead of pyautogui. All existing actions (click, type, hotkey, scroll, open, wait) remain unchanged.

### 9. Error Handling & Safety

- If the overlay fails to render, fall back to voice-only guidance
- If the AI returns invalid coordinates, skip the highlight and just speak the instruction
- PyAutoGUI failsafe remains (move mouse to corner to abort)
- Action delay between steps remains (0.3s default)
- All errors logged and spoken simply: "Произошла ошибка, попробуйте ещё раз" (An error occurred, try again)

---

## What Is NOT In Scope

- Multi-monitor overlay support (primary monitor only)
- Voice wake word / always-listening mode (requires continuous mic access, battery/privacy concerns)
- Custom voice/avatar for the assistant
- Web-based or Electron UI (staying with PyQt6)
- Real-time G-code editing or generation
- Direct GRBL serial communication (Candle handles this)
- Multi-language support (Russian only for now)

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `src/ui/tray.py` | Rewrite | Big, simple UI with giant talk button |
| `src/ui/overlay.py` | New | Transparent screen overlay for visual guidance |
| `src/assistant/engine.py` | Modify | Guide/do mode, overlay trigger integration |
| `src/assistant/config.py` | Modify | New settings for hotkey, overlay, mode |
| `src/assistant/hotkey.py` | New | Global F1 keyboard shortcut |
| `src/actions/executor.py` | Modify | Add highlight action type |
| `src/knowledge/loader.py` | New | Knowledge base section loader |
| `src/knowledge/ttc450_manual.txt` | New | TTC450 Pro manual text |
| `src/knowledge/candle_guide.txt` | New | Candle usage guide |
| `pyproject.toml` | Modify | Add pynput dependency |
| `build.spec` | Modify | Add new files to PyInstaller bundle |

---

## Dependencies

New Python dependency:
- `pynput` — global hotkey capture (cross-platform keyboard listener)

Everything else is already in the project.

---

## Build Order

1. **Knowledge base** — create knowledge files and loader (independent, no UI needed)
2. **System prompt** — rewrite with CNC expertise, mode awareness, overlay instructions
3. **UI redesign** — rewrite tray.py with big simple layout
4. **Global hotkey** — add F1 listener with pynput
5. **Overlay module** — transparent window with highlight rendering
6. **Executor update** — add highlight action routing
7. **Engine integration** — wire guide/do mode, overlay triggers, knowledge loading
8. **Testing** — end-to-end testing on Windows with Candle
9. **Build update** — update PyInstaller spec with new files and dependencies
