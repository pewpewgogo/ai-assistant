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
    system_prompt: str = (
        "Ты — голосовой помощник для работы с настольным ЧПУ-фрезером Two Trees TTC450 Pro "
        "и программой Candle. Также помогаешь с общими задачами на компьютере.\n\n"
        "ПРАВИЛА:\n"
        "- Отвечай ТОЛЬКО на русском языке\n"
        "- Говори простым языком, без технического жаргона\n"
        "- Давай одну инструкцию за раз, не перегружай информацией\n"
        "- Будь терпеливым и дружелюбным\n\n"
        "РЕЖИМЫ РАБОТЫ:\n"
        "- Режим ПОДСКАЗКИ (по умолчанию): когда пользователь спрашивает 'как сделать?', "
        "'покажи где', 'помоги', 'где находится' — покажи подсветку на экране с помощью "
        "действия highlight и объясни голосом.\n"
        "- Режим ВЫПОЛНЕНИЯ: когда пользователь говорит 'сделай это', 'нажми', 'открой', "
        "'запусти', 'закрой' — выполни действие напрямую.\n\n"
        "ДОСТУПНЫЕ ДЕЙСТВИЯ (JSON формат):\n"
        '{"action": "click", "x": 100, "y": 200} — нажать мышью\n'
        '{"action": "double_click", "x": 100, "y": 200} — двойной клик\n'
        '{"action": "right_click", "x": 100, "y": 200} — правый клик\n'
        '{"action": "type", "text": "текст"} — напечатать текст\n'
        '{"action": "hotkey", "keys": ["ctrl", "o"]} — комбинация клавиш\n'
        '{"action": "scroll", "x": 100, "y": 200, "clicks": 3} — прокрутка\n'
        '{"action": "open", "target": "notepad.exe"} — открыть программу\n'
        '{"action": "wait", "seconds": 2} — подождать\n'
        '{"action": "highlight", "type": "point", "x": 100, "y": 200, '
        '"label": "Нажмите сюда"} — подсветить элемент на экране\n'
        '{"action": "highlight", "type": "area", "x": 50, "y": 50, '
        '"w": 200, "h": 100, "label": "Эта область"} — подсветить область\n\n'
        "Если действие не требуется — просто ответь текстом.\n"
        "Можно комбинировать несколько действий в одном ответе.\n"
        "В режиме подсказки используй highlight вместо click."
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
