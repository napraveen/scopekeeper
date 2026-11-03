"""Live LLM provider adapters (Gemini, Anthropic, OpenAI) with retry and cache."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from clerk.adapters.llm_scripted import ScriptedLLM
from clerk.ports.protocols import LLMPort
from clerk.settings import Settings

TModel = TypeVar("TModel", bound=BaseModel)


def _extract_json_object(raw: str) -> str:
    """Strip optional markdown code fences and return the outermost JSON object string."""
    stripped = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL)
    if fence:
        return fence.group(1)
    first_brace = stripped.find("{")
    last_brace = stripped.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return stripped[first_brace : last_brace + 1]
    return stripped


class BaseHTTPProviderLLM:
    """Base LLMPort implementation with SHA-256 caching, one repair retry, and safe fallback."""

    def __init__(
        self,
        *,
        api_key: str,
        model_fast: str,
        model_writer: str,
        http_client: httpx.AsyncClient | None = None,
        fallback: LLMPort | None = None,
    ) -> None:
        self._api_key = api_key
        self._model_fast = model_fast
        self._model_writer = model_writer
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=30.0)
        self._fallback: LLMPort = fallback or ScriptedLLM()
        self._cache: dict[str, Any] = {}

    async def close(self) -> None:
        """Close the HTTP client if owned."""
        if self._owns_client:
            await self._http.aclose()

    async def _complete(self, *, system: str, user: str, model: str, json_mode: bool) -> str:
        """Vendor-specific completion request at temperature 0."""
        raise NotImplementedError

    async def json(self, system: str, user: str, schema: type[TModel]) -> TModel:
        """Generate a validated Pydantic model at temperature 0 with 1 repair retry and fallback."""
        cache_key = hashlib.sha256(f"{schema.__name__}::{system}::{user}".encode()).hexdigest()
        if cache_key in self._cache:
            cached: TModel = self._cache[cache_key]
            return cached.model_copy(deep=True)

        if not self._api_key:
            res = await self._fallback.json(system, user, schema)
            self._cache[cache_key] = res
            return res

        schema_json = json.dumps(schema.model_json_schema())
        augmented_system = (
            f"{system}\n\nReturn strictly valid JSON matching this JSON Schema:\n{schema_json}"
        )

        last_err = ""
        for attempt in range(2):
            prompt_user = (
                user
                if attempt == 0
                else (
                    f"{user}\n\nYour previous JSON failed validation ({last_err}). "
                    "Return repaired JSON only."
                )
            )
            try:
                raw_text = await self._complete(
                    system=augmented_system,
                    user=prompt_user,
                    model=self._model_fast,
                    json_mode=True,
                )
                cleaned = _extract_json_object(raw_text)
                parsed: TModel = schema.model_validate_json(cleaned)
                self._cache[cache_key] = parsed
                return parsed.model_copy(deep=True)
            except Exception as exc:
                last_err = str(exc)

        safe_res = await self._fallback.json(system, user, schema)
        self._cache[cache_key] = safe_res
        return safe_res

    async def text(self, system: str, user: str, max_words: int = 120) -> str:
        """Generate concise plain-text wording at temperature 0 with fallback."""
        cache_key = hashlib.sha256(f"TEXT::{max_words}::{system}::{user}".encode()).hexdigest()
        if cache_key in self._cache:
            return str(self._cache[cache_key])

        if not self._api_key:
            fallback_txt = await self._fallback.text(system, user, max_words=max_words)
            self._cache[cache_key] = fallback_txt
            return fallback_txt

        try:
            raw = await self._complete(
                system=f"{system}\nKeep response under {max_words} words.",
                user=user,
                model=self._model_writer,
                json_mode=False,
            )
            words = raw.strip().split()
            result = " ".join(words[:max_words])
            self._cache[cache_key] = result
            return result
        except Exception:
            fallback_txt = await self._fallback.text(system, user, max_words=max_words)
            self._cache[cache_key] = fallback_txt
            return fallback_txt


class GeminiLLMAdapter(BaseHTTPProviderLLM):
    """Google Gemini API adapter (`generativelanguage.googleapis.com`)."""

    async def _complete(self, *, system: str, user: str, model: str, json_mode: bool) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            f"?key={self._api_key}"
        )
        gen_cfg: dict[str, Any] = {"temperature": 0.0}
        if json_mode:
            gen_cfg["responseMimeType"] = "application/json"
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": gen_cfg,
        }
        resp = await self._http.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", [])
        return str(parts[0].get("text") or "")


class AnthropicLLMAdapter(BaseHTTPProviderLLM):
    """Anthropic Messages API adapter (`api.anthropic.com/v1/messages`)."""

    async def _complete(self, *, system: str, user: str, model: str, json_mode: bool) -> str:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": 1024,
            "temperature": 0.0,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        resp = await self._http.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("content") or []
        return str(content[0].get("text") or "")


class OpenAILLMAdapter(BaseHTTPProviderLLM):
    """OpenAI Chat Completions API adapter (`api.openai.com/v1/chat/completions`)."""

    async def _complete(self, *, system: str, user: str, model: str, json_mode: bool) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model,
            "temperature": 0.0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        resp = await self._http.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        return str(choices[0].get("message", {}).get("content") or "")


def create_llm_adapter(settings: Settings) -> LLMPort:
    """Create the configured LLMPort implementation from `Settings`."""
    provider = settings.llm_provider
    if provider == "gemini":
        return GeminiLLMAdapter(
            api_key=settings.gemini_api_key or settings.google_api_key,
            model_fast=settings.llm_model_fast,
            model_writer=settings.llm_model_writer,
        )
    if provider == "anthropic":
        return AnthropicLLMAdapter(
            api_key=settings.anthropic_api_key,
            model_fast=settings.llm_model_fast,
            model_writer=settings.llm_model_writer,
        )
    if provider == "openai":
        return OpenAILLMAdapter(
            api_key=settings.openai_api_key,
            model_fast=settings.llm_model_fast,
            model_writer=settings.llm_model_writer,
        )
    return ScriptedLLM()
