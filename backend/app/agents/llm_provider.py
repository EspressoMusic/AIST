"""
Future hook for OpenAI / Gemini / other LLMs.

Mock provider returns structured hints without network calls.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BrainLLMProvider(Protocol):
    """Async-friendly contract for a future real LLM debate pass."""

    def name(self) -> str:
        """Provider id for logs (e.g. openai-gpt-4o)."""

    async def enrich_debate_context(self, context: dict[str, Any]) -> dict[str, Any] | None:
        """
        Optional second pass over assembled agent context.

        Returns None to keep pure mock/debate logic, or a dict merged into debate payload.
        """


class MockBrainLLMProvider:
    """No I/O — reserved for future JSON tool-calling."""

    def name(self) -> str:
        return "mock"

    async def enrich_debate_context(self, context: dict[str, Any]) -> dict[str, Any] | None:
        _ = context
        return None
