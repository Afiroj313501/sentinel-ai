"""Provider abstraction for local Ollama and OpenAI-compatible APIs."""

from __future__ import annotations

from typing import Protocol

import httpx

from app.core.config import get_settings

ChatMessage = dict[str, str]
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
MAX_RESPONSE_BYTES = 200_000
MAX_COMPLETION_CHARS = 20_000
MAX_OUTPUT_TOKENS = 800
TEMPERATURE = 0.2


class AIProviderError(Exception):
    """An AI request failed with a safe, user-facing message."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AIProviderUnavailable(AIProviderError):
    """The provider is missing, misconfigured, or unreachable."""


class AIProvider(Protocol):
    name: str
    model: str

    def complete_json(self, messages: list[ChatMessage]) -> str:
        ...


def _check_status(response: httpx.Response) -> None:
    status = response.status_code
    if status < 400:
        return
    if status in (401, 403):
        raise AIProviderError("The AI provider rejected the credentials.")
    if status == 404:
        raise AIProviderUnavailable(
            "The AI provider could not find the configured model or endpoint. "
            "Check SENTINEL_AI_MODEL and SENTINEL_AI_BASE_URL "
            "(for Ollama, run: ollama pull <model>)."
        )
    if status == 429:
        raise AIProviderError("The AI provider's rate limit or quota was reached. Try again later.")
    raise AIProviderError(f"The AI provider returned an error (HTTP {status}).")


def _post_json(
    client: httpx.Client | None,
    url: str,
    payload: dict,
    headers: dict[str, str],
    timeout: float,
) -> object:
    http = client or httpx.Client(timeout=timeout)
    try:
        response = http.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        raise AIProviderError("The AI provider took too long to respond.") from exc
    except httpx.ConnectError as exc:
        raise AIProviderUnavailable("Cannot reach the AI provider. Is it running?") from exc
    except httpx.HTTPError as exc:
        raise AIProviderError("The AI request failed.") from exc
    finally:
        if client is None:
            http.close()

    _check_status(response)
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise AIProviderError("The AI provider returned an oversized response.")
    try:
        return response.json()
    except ValueError as exc:
        raise AIProviderError("The AI provider returned an unreadable response.") from exc


def _content(read) -> str:
    try:
        content = read()
    except (KeyError, IndexError, TypeError) as exc:
        raise AIProviderError("The AI provider returned an unexpected response.") from exc
    if not isinstance(content, str) or not content.strip():
        raise AIProviderError("The AI provider returned an empty response.")
    if len(content) > MAX_COMPLETION_CHARS:
        raise AIProviderError("The AI provider returned an oversized response.")
    return content


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: float, client: httpx.Client | None = None):
        self.model = model
        self._url = base_url.rstrip("/") + "/api/chat"
        self._timeout = timeout
        self._client = client

    def complete_json(self, messages: list[ChatMessage]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {"temperature": TEMPERATURE, "num_predict": MAX_OUTPUT_TOKENS},
        }
        data = _post_json(self._client, self._url, payload, {}, self._timeout)
        return _content(lambda: data["message"]["content"])  # type: ignore[index]


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float,
        client: httpx.Client | None = None,
    ):
        self.model = model
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._api_key = api_key
        self._timeout = timeout
        self._client = client

    def complete_json(self, messages: list[ChatMessage]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": TEMPERATURE,
            "max_tokens": MAX_OUTPUT_TOKENS,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        data = _post_json(self._client, self._url, payload, headers, self._timeout)
        return _content(lambda: data["choices"][0]["message"]["content"])  # type: ignore[index]


def get_provider() -> AIProvider:
    settings = get_settings()
    if settings.ai_provider == "ollama":
        return OllamaProvider(
            settings.ai_base_url or DEFAULT_OLLAMA_URL,
            settings.ai_model,
            settings.ai_timeout_seconds,
        )
    if not settings.ai_base_url or settings.ai_api_key is None:
        raise AIProviderUnavailable(
            "The AI provider is not configured. Set SENTINEL_AI_BASE_URL and SENTINEL_AI_API_KEY."
        )
    return OpenAICompatibleProvider(
        settings.ai_base_url,
        settings.ai_api_key.get_secret_value(),
        settings.ai_model,
        settings.ai_timeout_seconds,
    )
