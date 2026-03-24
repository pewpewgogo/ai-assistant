"""Configuration management for AI Assistant."""

import json
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

CONFIG_DIR = Path.home() / ".ai-assistant"
CONFIG_FILE = CONFIG_DIR / "config.json"


class Settings(BaseSettings):
    # AI provider settings
    ai_provider: str = Field(default="openai", description="AI provider: 'openai' or 'anthropic'")
    openai_api_key: str = Field(default="", description="OpenAI API key for Whisper + GPT-4o")
    anthropic_api_key: str = Field(default="", description="Anthropic API key for Claude")
    ai_model: str = Field(default="gpt-4o", description="Model to use for reasoning")

    # Voice settings
    sample_rate: int = Field(default=16000, description="Audio sample rate in Hz")
    silence_threshold: float = Field(default=0.02, description="RMS threshold for silence detection")
    silence_duration: float = Field(default=1.5, description="Seconds of silence before stopping recording")
    max_recording_seconds: int = Field(default=30, description="Maximum recording duration")

    # TTS settings
    tts_enabled: bool = Field(default=True, description="Enable text-to-speech responses")
    tts_rate: int = Field(default=170, description="Speech rate for TTS")

    # Screen settings
    screen_monitor: int = Field(default=1, description="Monitor index to capture (1 = primary)")

    # Hotkey
    hotkey: str = "f1"

    # Overlay
    overlay_enabled: bool = True
    overlay_timeout: int = 8
    overlay_color: str = "#ff6b6b"

    # Mode
    default_mode: str = "guide"  # "guide" or "do"

    # Knowledge
    knowledge_dir: str = ""

    # System prompt for the AI
    system_prompt: str = Field(
        default=(
            "\u0422\u044b \u2014 \u043f\u043e\u043c\u043e\u0449\u043d\u0438\u043a \u043d\u0430 \u0440\u0430\u0431\u043e\u0447\u0435\u043c \u0441\u0442\u043e\u043b\u0435. \u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c \u0433\u043e\u0432\u043e\u0440\u0438\u0442 \u0441 \u0442\u043e\u0431\u043e\u0439 \u043f\u043e-\u0440\u0443\u0441\u0441\u043a\u0438, \u0438 \u0442\u044b \u0432\u0438\u0434\u0438\u0448\u044c \u0435\u0433\u043e \u044d\u043a\u0440\u0430\u043d. "
            "\u0410\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u0439 \u0442\u043e, \u0447\u0442\u043e \u043d\u0430 \u044d\u043a\u0440\u0430\u043d\u0435, \u0438 \u043f\u043e\u043c\u043e\u0433\u0430\u0439 \u0432\u044b\u043f\u043e\u043b\u043d\u044f\u0442\u044c \u0437\u0430\u0434\u0430\u0447\u0438. "
            "\u0412\u0441\u0435\u0433\u0434\u0430 \u043e\u0442\u0432\u0435\u0447\u0430\u0439 \u043d\u0430 \u0440\u0443\u0441\u0441\u043a\u043e\u043c \u044f\u0437\u044b\u043a\u0435.\n\n"
            "\u0414\u043e\u0441\u0442\u0443\u043f\u043d\u044b\u0435 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u044f (\u043e\u0442\u0432\u0435\u0447\u0430\u0439 JSON-\u0431\u043b\u043e\u043a\u043e\u043c):\n"
            "- {\"action\": \"click\", \"x\": <int>, \"y\": <int>} - \u041a\u043b\u0438\u043a \u043f\u043e \u043a\u043e\u043e\u0440\u0434\u0438\u043d\u0430\u0442\u0430\u043c\n"
            "- {\"action\": \"double_click\", \"x\": <int>, \"y\": <int>} - \u0414\u0432\u043e\u0439\u043d\u043e\u0439 \u043a\u043b\u0438\u043a\n"
            "- {\"action\": \"right_click\", \"x\": <int>, \"y\": <int>} - \u041f\u0440\u0430\u0432\u044b\u0439 \u043a\u043b\u0438\u043a\n"
            "- {\"action\": \"type\", \"text\": \"<string>\"} - \u041d\u0430\u043f\u0435\u0447\u0430\u0442\u0430\u0442\u044c \u0442\u0435\u043a\u0441\u0442\n"
            "- {\"action\": \"hotkey\", \"keys\": [\"ctrl\", \"c\"]} - \u041d\u0430\u0436\u0430\u0442\u044c \u043a\u043e\u043c\u0431\u0438\u043d\u0430\u0446\u0438\u044e \u043a\u043b\u0430\u0432\u0438\u0448\n"
            "- {\"action\": \"scroll\", \"x\": <int>, \"y\": <int>, \"clicks\": <int>} - \u041f\u0440\u043e\u043a\u0440\u0443\u0442\u043a\u0430\n"
            "- {\"action\": \"open\", \"target\": \"<app or url>\"} - \u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u0438\u043b\u0438 \u0441\u0441\u044b\u043b\u043a\u0443\n"
            "- {\"action\": \"wait\", \"seconds\": <int>} - \u041f\u043e\u0434\u043e\u0436\u0434\u0430\u0442\u044c\n\n"
            "\u041c\u043e\u0436\u043d\u043e \u043e\u0431\u044a\u0435\u0434\u0438\u043d\u044f\u0442\u044c \u043d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u043e \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0439 \u0432 JSON-\u043c\u0430\u0441\u0441\u0438\u0432.\n"
            "\u0415\u0441\u043b\u0438 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435 \u043d\u0435 \u043d\u0443\u0436\u043d\u043e, \u043f\u0440\u043e\u0441\u0442\u043e \u043e\u0442\u0432\u0435\u0442\u044c \u0442\u0435\u043a\u0441\u0442\u043e\u043c."
        ),
        description="System prompt for the AI assistant",
    )

    model_config = {"env_prefix": "AI_ASSISTANT_"}

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = self.model_dump()
        CONFIG_FILE.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls) -> "Settings":
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text())
            return cls(**data)
        settings = cls()
        settings.save()
        return settings
