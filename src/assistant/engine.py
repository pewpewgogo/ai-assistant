"""Core assistant engine - orchestrates the listen-think-act loop."""

import logging
import sys
import threading
from enum import Enum
from pathlib import Path

from assistant.brain import create_provider
from assistant.config import Settings
from assistant.screen import ScreenCapture
from assistant.speaker import Speaker
from assistant.voice import Transcriber, VoiceCapture
from actions.executor import execute_actions
from knowledge.loader import KnowledgeLoader

logger = logging.getLogger(__name__)


class AssistantState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    ACTING = "acting"
    SPEAKING = "speaking"


class AssistantEngine:
    """Main engine that coordinates voice → AI → actions → speech."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.state = AssistantState.IDLE
        self._on_state_change = None
        self._on_transcript = None
        self._on_response = None
        self._worker_thread: threading.Thread | None = None

        # Components
        self.voice = VoiceCapture(
            sample_rate=settings.sample_rate,
            silence_threshold=settings.silence_threshold,
            silence_duration=settings.silence_duration,
            max_seconds=settings.max_recording_seconds,
        )
        self.screen = ScreenCapture(monitor=settings.screen_monitor)
        self.speaker = Speaker(rate=settings.tts_rate, enabled=settings.tts_enabled)

        # AI provider and transcriber are lazy-initialized (need API keys)
        self._transcriber = None
        self._ai = None

        # Overlay
        self._overlay_callback = None

        # Knowledge base
        self._knowledge_loader = None
        knowledge_dir = self.settings.knowledge_dir
        if not knowledge_dir:
            if getattr(sys, '_MEIPASS', None):
                knowledge_dir = str(Path(sys._MEIPASS) / "knowledge")
            else:
                knowledge_dir = str(Path(__file__).parent.parent / "knowledge")
        try:
            self._knowledge_loader = KnowledgeLoader(knowledge_dir)
            logger.info("Knowledge base loaded: %d sections", len(self._knowledge_loader.sections))
        except Exception as e:
            logger.warning("Could not load knowledge base: %s", e)

    def set_callbacks(self, on_state_change=None, on_transcript=None, on_response=None):
        """Set UI callbacks for state updates."""
        self._on_state_change = on_state_change
        self._on_transcript = on_transcript
        self._on_response = on_response

    def set_overlay_callback(self, callback):
        """Set callback for overlay highlights: callback(type, x, y, w, h, label)."""
        self._overlay_callback = callback

    def _set_state(self, state: AssistantState):
        self.state = state
        if self._on_state_change:
            self._on_state_change(state)

    def _ensure_initialized(self) -> bool:
        """Lazy-init transcriber and AI provider."""
        if not self.settings.openai_api_key and not self.settings.anthropic_api_key:
            logger.error("No API key configured. Open settings to add one.")
            return False

        # Transcriber uses Whisper (OpenAI). It needs SOME OpenAI key.
        # If user only has Anthropic key, we can't transcribe.
        if self._transcriber is None:
            if self.settings.openai_api_key:
                self._transcriber = Transcriber(api_key=self.settings.openai_api_key)
            else:
                logger.error("Whisper transcription requires an OpenAI API key.")
                return False

        if self._ai is None:
            if self.settings.ai_provider == "anthropic" and self.settings.anthropic_api_key:
                key = self.settings.anthropic_api_key
            elif self.settings.openai_api_key:
                key = self.settings.openai_api_key
            else:
                key = self.settings.anthropic_api_key

            self._ai = create_provider(
                provider=self.settings.ai_provider,
                api_key=key,
                model=self.settings.ai_model,
            )

        return True

    def listen_and_respond(self):
        """Start a single listen → think → act cycle in a background thread."""
        if self.state != AssistantState.IDLE:
            logger.warning("Already busy: %s", self.state)
            return

        if not self._ensure_initialized():
            if self._on_response:
                self._on_response(
                    "⚠️ Откройте Настройки и введите API ключ OpenAI.\n"
                    "Ключ OpenAI нужен для распознавания голоса (Whisper)."
                )
            self._set_state(AssistantState.IDLE)
            return

        def _worker():
            try:
                # 1. Listen
                self._set_state(AssistantState.LISTENING)
                logger.info("Recording started...")
                audio = self.voice.record()
                if audio is None:
                    logger.info("No speech detected.")
                    if self._on_response:
                        self._on_response("🎤 Не услышал речь. Попробуйте говорить громче или ближе к микрофону.")
                    self._set_state(AssistantState.IDLE)
                    return

                duration = len(audio) / self.settings.sample_rate
                logger.info("Recorded %.1f seconds. Transcribing...", duration)

                # 2. Transcribe
                self._set_state(AssistantState.THINKING)
                text = self._transcriber.transcribe(audio, self.settings.sample_rate)
                if not text:
                    if self._on_response:
                        self._on_response("🎤 Не удалось распознать речь. Попробуйте ещё раз.")
                    self._set_state(AssistantState.IDLE)
                    return

                if self._on_transcript:
                    self._on_transcript(text)

                # 3. Capture screen
                screen_b64 = self.screen.capture_base64()

                # 3b. Get relevant knowledge context
                knowledge_context = ""
                if self._knowledge_loader and text:
                    knowledge_context = self._knowledge_loader.get_context(text)

                # 3c. Build enhanced system prompt
                system_prompt = self.settings.system_prompt
                if knowledge_context:
                    system_prompt = system_prompt + "\n\n" + knowledge_context

                # 4. Ask AI
                response = self._ai.chat(text, screen_b64, system_prompt)
                if self._on_response:
                    self._on_response(response)

                # 5. Execute actions if present
                self._set_state(AssistantState.ACTING)
                results = execute_actions(response)
                if results:
                    logger.info("Actions executed: %s", results)

                # 5b. Route highlight actions to overlay
                if results and self._overlay_callback:
                    for result in results:
                        if isinstance(result, dict) and result.get("action") == "highlight":
                            try:
                                self._overlay_callback(
                                    result.get("type", "point"),
                                    result.get("x", 0),
                                    result.get("y", 0),
                                    result.get("w", 0),
                                    result.get("h", 0),
                                    result.get("label", ""),
                                )
                            except Exception as e:
                                logger.error("Overlay callback error: %s", e)

                # 6. Speak response
                self._set_state(AssistantState.SPEAKING)
                self.speaker.speak(response)

            except Exception as e:
                logger.exception("Error in assistant loop")
                if self._on_response:
                    self._on_response(f"⚠️ Произошла ошибка: {e}\nПопробуйте ещё раз.")
            finally:
                self._set_state(AssistantState.IDLE)

        self._worker_thread = threading.Thread(target=_worker, daemon=True)
        self._worker_thread.start()

    def stop(self):
        """Stop any ongoing operation."""
        self.voice.stop()
        self.speaker.stop()
        self._set_state(AssistantState.IDLE)

    def reload_settings(self, settings: Settings):
        """Reload settings (e.g., after user changes config)."""
        self.settings = settings
        self.voice = VoiceCapture(
            sample_rate=settings.sample_rate,
            silence_threshold=settings.silence_threshold,
            silence_duration=settings.silence_duration,
            max_seconds=settings.max_recording_seconds,
        )
        self.screen = ScreenCapture(monitor=settings.screen_monitor)
        self.speaker = Speaker(rate=settings.tts_rate, enabled=settings.tts_enabled)
        # Force re-init of AI provider on next call
        self._transcriber = None
        self._ai = None
