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

    # System prompt for the AI
    system_prompt: str = Field(
        default=(
            "You are a helpful desktop assistant. The user speaks to you and you can see their screen. "
            "Analyze what's on screen and help them accomplish tasks. "
            "When you need to perform an action, respond with a JSON action block.\n\n"
            "Available actions:\n"
            "- {\"action\": \"click\", \"x\": <int>, \"y\": <int>} - Click at screen coordinates\n"
            "- {\"action\": \"double_click\", \"x\": <int>, \"y\": <int>} - Double-click\n"
            "- {\"action\": \"right_click\", \"x\": <int>, \"y\": <int>} - Right-click\n"
            "- {\"action\": \"type\", \"text\": \"<string>\"} - Type text\n"
            "- {\"action\": \"hotkey\", \"keys\": [\"ctrl\", \"c\"]} - Press key combination\n"
            "- {\"action\": \"scroll\", \"x\": <int>, \"y\": <int>, \"clicks\": <int>} - Scroll\n"
            "- {\"action\": \"open\", \"target\": \"<app or url>\"} - Open application or URL\n"
            "- {\"action\": \"wait\", \"seconds\": <int>} - Wait before next action\n\n"
            "You can chain multiple actions by returning a JSON array of action objects.\n"
            "If no action is needed, just respond with helpful text."
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
