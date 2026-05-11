"""Shared AI advisor client.

AI output is recommendation-only. The bot engine and execution gate remain the
only code paths that can open/close trades.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Literal

from app.config import Settings

logger = logging.getLogger(__name__)

AiProvider = Literal["MOCK", "OPENAI", "GEMINI"]

_ACTIONS = {"BUY", "SELL", "HOLD"}
_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH"}
_DEFAULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["action", "confidence", "risk_level", "reason", "short_reason", "veto"],
    "properties": {
        "action": {"enum": ["BUY", "SELL", "HOLD"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 100},
        "risk_level": {"enum": ["LOW", "MEDIUM", "HIGH"]},
        "reason": {"type": "string"},
        "short_reason": {"type": "string"},
        "veto": {"type": "boolean"},
    },
}
_MARKET_SENTIMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "market_bias",
        "sentiment_score",
        "action",
        "confidence",
        "risk_level",
        "short_reason",
        "reason",
        "veto",
    ],
    "properties": {
        "market_bias": {"enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
        "sentiment_score": {"type": "number", "minimum": -100, "maximum": 100},
        "action": {"enum": ["BUY", "SELL", "HOLD"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 100},
        "risk_level": {"enum": ["LOW", "MEDIUM", "HIGH"]},
        "short_reason": {"type": "string"},
        "reason": {"type": "string"},
        "veto": {"type": "boolean"},
    },
}
_MARKET_BIASES = {"BULLISH", "BEARISH", "NEUTRAL"}


class AIProviderService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._last_error: str | None = None
        self._last_used_provider: AiProvider = "MOCK"

    @property
    def configured_provider(self) -> AiProvider:
        raw = (self._settings.ai_advisor_provider or "MOCK").strip().upper()
        if raw in ("OPENAI", "GEMINI"):
            return raw  # type: ignore[return-value]
        return "MOCK"

    @property
    def active_provider(self) -> AiProvider:
        provider = self.configured_provider
        if provider == "OPENAI" and not self._settings.openai_api_key.strip():
            return "MOCK"
        if provider == "GEMINI" and not self._settings.gemini_api_key.strip():
            return "MOCK"
        return provider

    @property
    def active_model(self) -> str:
        provider = self.active_provider
        if provider == "OPENAI":
            return self._settings.openai_model or "gpt-4o-mini"
        if provider == "GEMINI":
            return self._settings.gemini_model or "gemini-1.5-flash"
        return "mock"

    def status(self) -> dict[str, Any]:
        return {
            "configured_provider": self.configured_provider,
            "active_provider": self.active_provider,
            "model": self.active_model,
            "default_is_mock": True,
            "last_used_provider": self._last_used_provider,
            "last_error": self._last_error,
            "can_execute_trades": False,
            "note": "AI advisor recommends only; execution gate and engine safety rules remain authoritative.",
        }

    def analyze_with_ai(self, prompt: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return normalized strict JSON advice, falling back safely on any problem."""
        expected_schema = schema or _DEFAULT_SCHEMA
        provider = self.active_provider
        if provider == "MOCK":
            self._last_used_provider = "MOCK"
            self._last_error = None
            return self._mock_response(prompt)

        try:
            if provider == "OPENAI":
                raw = self._call_openai(prompt, expected_schema)
            else:
                raw = self._call_gemini(prompt, expected_schema)
        except Exception as exc:
            self._last_error = str(exc)
            logger.warning("AI advisor provider %s failed; falling back to MOCK: %s", provider, exc)
            self._last_used_provider = "MOCK"
            return self._mock_response(prompt)
        try:
            normalized = self._normalize(raw)
        except Exception as exc:
            self._last_error = f"Invalid AI response: {exc}"
            logger.warning("AI advisor returned invalid JSON; using HOLD fallback: %s", exc)
            self._last_used_provider = provider
            return _hold_response("Invalid AI response; safety fallback to HOLD.")
        self._last_used_provider = provider
        self._last_error = None
        return normalized

    def analyze_market_sentiment(self, prompt: str) -> dict[str, Any]:
        """Return strict macro/news sentiment JSON, falling back to NEUTRAL/HOLD."""
        provider = self.active_provider
        if provider == "MOCK":
            self._last_used_provider = "MOCK"
            self._last_error = None
            return _neutral_market_sentiment("AI provider is MOCK; neutral advisory fallback.")

        try:
            if provider == "OPENAI":
                raw = self._call_openai(prompt, _MARKET_SENTIMENT_SCHEMA)
            else:
                raw = self._call_gemini(prompt, _MARKET_SENTIMENT_SCHEMA)
        except Exception as exc:
            self._last_error = str(exc)
            logger.warning("AI market sentiment provider %s failed; using neutral fallback: %s", provider, exc)
            self._last_used_provider = "MOCK"
            return _neutral_market_sentiment("AI provider failed; neutral HOLD fallback.")

        try:
            normalized = self._normalize_market_sentiment(raw)
        except Exception as exc:
            self._last_error = f"Invalid AI market sentiment response: {exc}"
            logger.warning("AI market sentiment returned invalid JSON; using neutral fallback: %s", exc)
            self._last_used_provider = provider
            return _neutral_market_sentiment("Invalid AI sentiment response; neutral HOLD fallback.")

        self._last_used_provider = provider
        self._last_error = None
        return normalized

    def _call_openai(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        body = {
            "model": self._settings.openai_model or "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": _system_prompt(schema),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        payload = _http_json(req, self._settings.ai_advisor_timeout_seconds)
        content = payload["choices"][0]["message"]["content"]
        return _json_object(content)

    def _call_gemini(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        model = self._settings.gemini_model or "gemini-1.5-flash"
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={self._settings.gemini_api_key}"
        )
        body = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"{_system_prompt(schema)}\n\nUser prompt:\n{prompt}",
                        },
                    ],
                },
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        payload = _http_json(req, self._settings.ai_advisor_timeout_seconds)
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        return _json_object(text)

    def _normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        action = str(raw.get("action") or "HOLD").strip().upper()
        risk_level = str(raw.get("risk_level") or "MEDIUM").strip().upper()
        if action not in _ACTIONS or risk_level not in _RISK_LEVELS:
            raise ValueError("AI response has invalid enum values")
        confidence_raw = raw.get("confidence", 0)
        if not isinstance(confidence_raw, (int, float)):
            confidence_raw = float(str(confidence_raw))
        confidence = max(0.0, min(100.0, float(confidence_raw)))
        reason = str(raw.get("reason") or "").strip()
        short_reason = str(raw.get("short_reason") or "").strip()
        veto = raw.get("veto")
        if not isinstance(veto, bool):
            if str(veto).lower() in ("true", "1", "yes"):
                veto = True
            elif str(veto).lower() in ("false", "0", "no"):
                veto = False
            else:
                raise ValueError("AI response veto is not boolean")
        if not reason or not short_reason:
            raise ValueError("AI response missing reason fields")
        return {
            "action": action,
            "confidence": round(confidence, 2),
            "risk_level": risk_level,
            "reason": reason[:2000],
            "short_reason": short_reason[:180],
            "veto": veto,
        }

    def _normalize_market_sentiment(self, raw: dict[str, Any]) -> dict[str, Any]:
        base = self._normalize(raw)
        market_bias = str(raw.get("market_bias") or "NEUTRAL").strip().upper()
        if market_bias not in _MARKET_BIASES:
            raise ValueError("AI response has invalid market_bias")
        score_raw = raw.get("sentiment_score", 0)
        if not isinstance(score_raw, (int, float)):
            score_raw = float(str(score_raw))
        sentiment_score = max(-100.0, min(100.0, float(score_raw)))
        return {
            "market_bias": market_bias,
            "sentiment_score": round(sentiment_score, 2),
            **base,
        }

    def _mock_response(self, prompt: str) -> dict[str, Any]:
        p = prompt.lower()
        action = "HOLD"
        confidence = 55.0
        risk_level = "MEDIUM"
        veto = False
        short = "Waiting for clearer setup"
        if "overbought" in p or "risk veto" in p or "loss streak" in p:
            action = "HOLD"
            confidence = 64.0
            risk_level = "HIGH"
            veto = "risk veto" in p or "loss streak" in p
            short = "Risk needs caution"
        elif "ema12>ema26" in p or "bullish" in p:
            action = "BUY"
            confidence = 66.0
            risk_level = "MEDIUM"
            short = "Setup leans bullish"
        elif "ema12<=ema26" in p or "bearish" in p:
            action = "SELL"
            confidence = 62.0
            risk_level = "MEDIUM"
            short = "Setup leans weak"
        return {
            "action": action,
            "confidence": confidence,
            "risk_level": risk_level,
            "reason": (
                "MOCK advisor used deterministic prompt cues. This is an advisory "
                "recommendation only and cannot execute or bypass safety gates."
            ),
            "short_reason": short,
            "veto": veto,
        }


def _system_prompt(schema: dict[str, Any]) -> str:
    required = schema.get("required")
    keys = ", ".join(str(item) for item in required) if isinstance(required, list) else "the required"
    return (
        "You are an AI trading advisor for a paper/Testnet bot. "
        "You may recommend only; you cannot execute trades. "
        f"Return strict JSON only matching the provided schema. Required keys: {keys}. "
        "Allowed action values: BUY, SELL, HOLD. "
        "Allowed risk_level values: LOW, MEDIUM, HIGH. "
        f"Schema: {json.dumps(schema, separators=(',', ':'))}"
    )


def _hold_response(reason: str) -> dict[str, Any]:
    return {
        "action": "HOLD",
        "confidence": 0.0,
        "risk_level": "HIGH",
        "reason": reason,
        "short_reason": "Invalid AI response",
        "veto": True,
    }


def _neutral_market_sentiment(reason: str) -> dict[str, Any]:
    return {
        "market_bias": "NEUTRAL",
        "sentiment_score": 0.0,
        "action": "HOLD",
        "confidence": 0.0,
        "risk_level": "MEDIUM",
        "short_reason": "Neutral sentiment fallback",
        "reason": reason,
        "veto": False,
    }


def _http_json(req: urllib.request.Request, timeout: float) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return _json_object(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body[:500]}") from exc


def _json_object(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object")
    return parsed
