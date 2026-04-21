"""OpenAI-compatible LLM interface."""

from openai import OpenAI
from src.config import LLMConfig


class LLM:
    def __init__(self, config: LLMConfig):
        self.client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
        )
        self.model = config.model

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """Call chat completions with optional tool definitions.
        
        Returns the raw response message dict.
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message

    def chat_stream(self, messages: list[dict], tools: list[dict] | None = None):
        """Streaming chat completions. Yields delta chunks."""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        return self.client.chat.completions.create(**kwargs)
