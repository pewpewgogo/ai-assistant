"""Text-to-speech module for spoken responses."""

import logging
import re
import threading

logger = logging.getLogger(__name__)


class Speaker:
    """Speaks text aloud using pyttsx3 (offline TTS)."""

    def __init__(self, rate: int = 170, enabled: bool = True):
        self.rate = rate
        self.enabled = enabled
        self._engine = None
        self._lock = threading.Lock()

    def _get_engine(self):
        if self._engine is None:
            import pyttsx3

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.rate)
            voices = self._engine.getProperty("voices")
            # Prefer a female voice if available
            for voice in voices:
                if "female" in voice.name.lower() or "zira" in voice.name.lower():
                    self._engine.setProperty("voice", voice.id)
                    break
        return self._engine

    def speak(self, text: str) -> None:
        """Speak the given text. Strips JSON action blocks before speaking."""
        if not self.enabled or not text.strip():
            return

        # Remove JSON blocks — don't read action commands aloud
        clean = re.sub(r"```json.*?```", "", text, flags=re.DOTALL)
        clean = re.sub(r"\{[^}]*\"action\"[^}]*\}", "", clean)
        clean = re.sub(r"\[.*?\]", "", clean, flags=re.DOTALL)
        clean = clean.strip()

        if not clean:
            return

        def _do_speak():
            with self._lock:
                try:
                    engine = self._get_engine()
                    engine.say(clean)
                    engine.runAndWait()
                except Exception:
                    logger.exception("TTS error")

        thread = threading.Thread(target=_do_speak, daemon=True)
        thread.start()

    def stop(self) -> None:
        with self._lock:
            if self._engine:
                try:
                    self._engine.stop()
                except Exception:
                    pass
