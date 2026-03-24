"""AI reasoning engine - sends screen + voice to LLM and gets responses."""

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class AIProvider(Protocol):
    def chat(self, user_text: str, screen_b64: str, system_prompt: str) -> str: ...


class OpenAIProvider:
    """Uses GPT-4o with vision for reasoning."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.history: list[dict] = []

    def chat(self, user_text: str, screen_b64: str, system_prompt: str) -> str:
        messages = [{"role": "system", "content": system_prompt}]

        # Include recent history for context (last 6 exchanges)
        messages.extend(self.history[-12:])

        # Current turn with screenshot
        user_content = [
            {"type": "text", "text": user_text},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{screen_b64}", "detail": "high"},
            },
        ]
        messages.append({"role": "user", "content": user_content})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_completion_tokens=2048,
        )

        reply = response.choices[0].message.content or ""

        # Store in history (text only, no images — saves tokens)
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": reply})

        logger.info("AI response: %s", reply[:200])
        return reply


class AnthropicProvider:
    """Uses Claude with vision for reasoning."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        from anthropic import Anthropic

        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.history: list[dict] = []

    def chat(self, user_text: str, screen_b64: str, system_prompt: str) -> str:
        messages = list(self.history[-12:])

        user_content = [
            {"type": "text", "text": user_text},
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": screen_b64},
            },
        ]
        messages.append({"role": "user", "content": user_content})

        response = self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=messages,
            max_tokens=2048,
        )

        reply = response.content[0].text

        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": reply})

        logger.info("AI response: %s", reply[:200])
        return reply


def create_provider(provider: str, api_key: str, model: str) -> AIProvider:
    if provider == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model)
    return OpenAIProvider(api_key=api_key, model=model)
