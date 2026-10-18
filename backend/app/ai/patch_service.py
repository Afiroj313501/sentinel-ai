"""Validate AI line replacements and build reviewable unified diffs."""

from __future__ import annotations

import ast
import difflib
import json
import re
import textwrap
from dataclasses import dataclass

from app.ai.patch_prompts import build_patch_messages
from app.ai.provider import AIProvider, AIProviderError
from app.core.security import UnsafePathError, normalize_member_name
from app.schemas.finding import Finding
from app.services.normalization_service import SNIPPET_MAX_CHARS, truncate

MAX_ATTEMPTS = 2
MAX_NEW_LINES = 60
MAX_LINE_CHARS = 300
MAX_TOTAL_CHARS = 4000
MAX_RATIONALE_CHARS = 800
DEFAULT_NO_FIX = "The AI could not propose a safe fix from the available code."
_SNIPPET_LINE = re.compile(r"^\s*(\d+) \| ?(.*)$")
_HUNK_HEADER = re.compile(r"^@@ -(\d+)(,\d+)? \+(\d+)(,\d+)? @@")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


class NoSourceExcerpt(Exception):
    """No usable code excerpt is stored for this finding."""


class InvalidPatch(AIProviderError):
    def __init__(self) -> None:
        super().__init__(
            "The AI model proposed a patch that failed validation. "
            "Try again, or use a different model."
        )


@dataclass(frozen=True)
class FixProposal:
    can_fix: bool
    rationale: str
    diff: str | None
    syntax_check: str


def editable_region(snippet: str | None) -> dict[int, str]:
    if not snippet:
        return {}
    region: dict[int, str] = {}
    for raw in snippet.split("\n"):
        match = _SNIPPET_LINE.match(raw)
        if not match:
            return {}
        number = int(match.group(1))
        if region and number != max(region) + 1:
            return {}
        region[number] = match.group(2)
    if len(snippet) >= SNIPPET_MAX_CHARS and region:
        del region[max(region)]
    return region


def _shift_hunk(header: str, offset: int) -> str:
    match = _HUNK_HEADER.match(header)
    if not match:
        return header
    old_start, old_len, new_start, new_len = match.groups()
    return (
        f"@@ -{int(old_start) + offset}{old_len or ''} "
        f"+{int(new_start) + offset}{new_len or ''} @@"
    )


def build_unified_diff(path: str, first_line: int, original: list[str], patched: list[str]) -> str:
    offset = first_line - 1
    lines = [
        _shift_hunk(line, offset) if line.startswith("@@") else line
        for line in difflib.unified_diff(
            original, patched, fromfile=f"a/{path}", tofile=f"b/{path}", lineterm="", n=3
        )
    ]
    return "\n".join(lines) + "\n"


def _int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _extract_object(raw: str) -> dict:
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise InvalidPatch()
    try:
        data = json.loads(raw[start : end + 1])
    except (ValueError, RecursionError) as exc:
        raise InvalidPatch() from exc
    if not isinstance(data, dict):
        raise InvalidPatch()
    return data


def _parses_as_python(text: str) -> bool:
    try:
        ast.parse(textwrap.dedent(text))
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return False
    return True


def interpret_patch(raw: str, finding: Finding, region: dict[int, str]) -> FixProposal:
    data = _extract_object(raw)
    rationale_value = data.get("rationale")
    rationale = (
        truncate(rationale_value.strip(), MAX_RATIONALE_CHARS)
        if isinstance(rationale_value, str)
        else ""
    )
    can_fix = data.get("can_fix")
    if can_fix is False:
        return FixProposal(False, rationale or DEFAULT_NO_FIX, None, "not_checked")
    if can_fix is not True or not rationale or not region:
        raise InvalidPatch()

    first, last = min(region), max(region)
    start, end = _int(data.get("start_line")), _int(data.get("end_line"))
    new_lines = data.get("new_lines")
    if start is None or end is None or not isinstance(new_lines, list):
        raise InvalidPatch()
    if not first <= start <= end <= last or end < finding.line_start or start > finding.line_end:
        raise InvalidPatch()
    if not all(isinstance(line, str) for line in new_lines):
        raise InvalidPatch()
    replacement = "\n".join(new_lines).split("\n") if new_lines else []
    if (
        len(replacement) > MAX_NEW_LINES
        or sum(len(line) for line in replacement) > MAX_TOTAL_CHARS
        or any(len(line) > MAX_LINE_CHARS or _CONTROL_CHARS.search(line) for line in replacement)
    ):
        raise InvalidPatch()

    original = [region[number] for number in range(first, last + 1)]
    patched = original[: start - first] + replacement + original[end - first + 1 :]
    if patched == original:
        raise InvalidPatch()

    syntax_check = "not_checked"
    if finding.file_path.lower().endswith(".py") and _parses_as_python("\n".join(original)):
        if not _parses_as_python("\n".join(patched)):
            raise InvalidPatch()
        syntax_check = "passed"
    return FixProposal(True, rationale, build_unified_diff(finding.file_path, first, original, patched), syntax_check)


def generate_fix(provider: AIProvider, finding: Finding) -> FixProposal:
    region = editable_region(finding.snippet)
    if not region:
        raise NoSourceExcerpt()
    try:
        if str(normalize_member_name(finding.file_path)) != finding.file_path:
            raise NoSourceExcerpt()
    except UnsafePathError as exc:
        raise NoSourceExcerpt() from exc

    messages = build_patch_messages(finding, region)
    for _ in range(MAX_ATTEMPTS):
        raw = provider.complete_json(messages)
        try:
            return interpret_patch(raw, finding, region)
        except InvalidPatch:
            continue
    raise InvalidPatch()
