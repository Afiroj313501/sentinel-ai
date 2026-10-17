"""Generate and validate explanations returned by an AI provider."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from app.ai.prompts import build_messages
from app.ai.provider import AIProvider, AIProviderError
from app.schemas.explanation import Explanation
from app.schemas.finding import Finding


class InvalidModelOutput(Exception):
    """The provider returned content that cannot become a safe explanation."""


def _json_object(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if match is None:
            raise InvalidModelOutput("The AI provider returned unusable explanation content.")
        try:
            value = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise InvalidModelOutput("The AI provider returned unusable explanation content.") from exc
    if not isinstance(value, dict):
        raise InvalidModelOutput("The AI provider returned unusable explanation content.")
    return value


def parse_explanation(raw: str) -> Explanation:
    data = _json_object(raw)
    for field in ("summary", "impact", "remediation"):
        value = data.get(field)
        if isinstance(value, str):
            data[field] = value.strip()[: {"summary": 600, "impact": 1200, "remediation": 1200}[field]]
    confidence = data.get("confidence")
    if isinstance(confidence, str):
        data["confidence"] = confidence.strip().lower()
    try:
        return Explanation.model_validate(data)
    except ValidationError as exc:
        raise InvalidModelOutput("The AI provider returned unusable explanation content.") from exc


def generate_explanation(provider: AIProvider, finding: Finding) -> Explanation:
    messages = build_messages(finding)
    last_error: InvalidModelOutput | None = None
    for _ in range(2):
        try:
            return parse_explanation(provider.complete_json(messages))
        except InvalidModelOutput as exc:
            last_error = exc
    assert last_error is not None
    raise last_error
