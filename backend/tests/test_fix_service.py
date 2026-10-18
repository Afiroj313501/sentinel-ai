import json

import pytest

from app.ai.patch_service import (
    InvalidPatch,
    build_unified_diff,
    editable_region,
    generate_fix,
    interpret_patch,
)
from app.schemas.finding import Finding


SNIPPET = "10 | import os\n11 | eval(value)\n12 | print(value)"


def make_finding(**overrides: object) -> Finding:
    values = {
        "id": "abc123456789-0001",
        "scan_id": "s" * 32,
        "scanner": "bandit",
        "rule_id": "B307",
        "title": "Use of eval",
        "severity": "high",
        "confidence": "high",
        "category": "security",
        "file_path": "src/app.py",
        "line_start": 11,
        "line_end": 11,
        "evidence": "eval is unsafe",
        "snippet": SNIPPET,
    }
    values.update(overrides)
    return Finding(**values)


def patch(**overrides: object) -> str:
    values: dict[str, object] = {
        "can_fix": True,
        "rationale": "Replace the unsafe evaluation with a safe conversion.",
        "start_line": 11,
        "end_line": 11,
        "new_lines": ["int(value)"],
    }
    values.update(overrides)
    return json.dumps(values)


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def complete_json(self, messages: list[dict[str, str]]) -> str:
        self.calls += 1
        return self.response


def test_editable_region_preserves_line_numbers_and_blank_lines() -> None:
    assert editable_region("9 |     return 1\n10 | ") == {9: "    return 1", 10: ""}


def test_editable_region_rejects_gaps() -> None:
    assert editable_region("1 | a\n3 | c") == {}


def test_build_unified_diff_uses_absolute_line_numbers() -> None:
    diff = build_unified_diff("src/app.py", 10, ["a", "b", "c"], ["a", "B", "c"])
    assert "@@ -10,3 +10,3 @@" in diff
    assert "-b\n+B" in diff


def test_interpret_patch_validates_and_builds_diff() -> None:
    proposal = interpret_patch(patch(), make_finding(), editable_region(SNIPPET))
    assert proposal.can_fix is True
    assert proposal.syntax_check == "passed"
    assert "-eval(value)\n+int(value)" in (proposal.diff or "")


@pytest.mark.parametrize(
    "overrides",
    [
        {"start_line": 99, "end_line": 99},
        {"start_line": 12, "end_line": 12},
        {"new_lines": ["eval(value)"]},
        {"new_lines": ["bad\x00line"]},
        {"can_fix": "yes"},
    ],
)
def test_invalid_patch_is_rejected(overrides: dict[str, object]) -> None:
    with pytest.raises(InvalidPatch):
        interpret_patch(patch(**overrides), make_finding(), editable_region(SNIPPET))


def test_no_safe_fix_is_valid_and_has_no_diff() -> None:
    proposal = interpret_patch(
        json.dumps({"can_fix": False, "rationale": "The change needs another file."}),
        make_finding(),
        editable_region(SNIPPET),
    )
    assert proposal.can_fix is False
    assert proposal.diff is None


def test_generate_retries_once_after_invalid_output() -> None:
    class RetryingProvider(FakeProvider):
        def complete_json(self, messages: list[dict[str, str]]) -> str:
            self.calls += 1
            return "invalid" if self.calls == 1 else patch()

    provider = RetryingProvider("")
    assert generate_fix(provider, make_finding()).can_fix is True
    assert provider.calls == 2
