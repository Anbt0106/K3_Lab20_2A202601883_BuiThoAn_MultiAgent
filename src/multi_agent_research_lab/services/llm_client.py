"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

import os
from dataclasses import dataclass
from typing import Any

from langsmith import Client, tracing_context
from langsmith.wrappers import wrap_openai
from openai import OpenAI

from multi_agent_research_lab.core.config import Settings, get_settings


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """OpenAI-compatible client for OpenAI, OpenRouter, or another provider."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a chat completion through the configured OpenAI-compatible endpoint."""

        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for LLM calls")

        client = OpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
            timeout=self.settings.timeout_seconds,
        )
        tracing_client: Client | None = None
        if self.settings.langsmith_tracing and self.settings.langsmith_api_key:
            os.environ.setdefault("LANGSMITH_API_KEY", self.settings.langsmith_api_key)
            os.environ.setdefault("LANGSMITH_PROJECT", self.settings.langsmith_project)
            os.environ.setdefault("LANGSMITH_TRACING", "true")
            os.environ.setdefault("LANGCHAIN_API_KEY", self.settings.langsmith_api_key)
            os.environ.setdefault("LANGCHAIN_PROJECT", self.settings.langsmith_project)
            os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
            tracing_client = Client(api_key=self.settings.langsmith_api_key)
            client = wrap_openai(client)

        request: dict[str, Any] = {
            "model": self.settings.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if tracing_client is not None:
            with tracing_context(
                project_name=self.settings.langsmith_project,
                enabled=True,
                client=tracing_client,
            ):
                completion = client.chat.completions.create(**request)
        else:
            completion = client.chat.completions.create(**request)

        choice = completion.choices[0]
        usage = completion.usage
        return LLMResponse(
            content=choice.message.content or "",
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            cost_usd=getattr(usage, "cost", None),
        )
