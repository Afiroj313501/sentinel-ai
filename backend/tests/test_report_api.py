import json
import re

from app.api.routes import findings as findings_routes
from app.main import app
from app.scanners.base import ScannerOutcome
from app.schemas.finding import Finding, ScannerRun
from app.services import scan_service

TITLE = "Evil <script>alert(1)</script> [click](javascript:alert(1))\n# Injected heading"
EVIDENCE = (
    "line one\n===\n| a | b |\n- list item\n"
    "![img](http://evil.example/x.png) http://evil.example/phish"
)
SNIPPET = "1 | eval(x) ```\n2 | ````\n3 | ~~~"

EXPLAIN_JSON = json.dumps(
    {
        "summary": "Summary <img src=x onerror=alert(1)> **bold**",
        "impact": "Code injection if the input is attacker-controlled.",
        "confidence": "medium",
        "remediation": "Avoid eval.",
        "evidence_sufficient": True,
    }
)
FIX_JSON = json.dumps(
    {
        "can_fix": True,
        "rationale": "Parse the value instead of evaluating it.",
        "start_line": 1,
        "end_line": 1,
        "new_lines": ["int(x)"],
    }
)

def make_finding(scan_id: str, **overrides) -> Finding:
    base = {
        "id": "", "scan_id": scan_id, "scanner": "clean", "rule_id": "R1",
        "title": "Dangerous eval call", "severity": "high", "confidence": "medium",
        "category": "security", "file_path": "app.py", "line_start": 1, "line_end": 1,
        "evidence": "eval is unsafe", "snippet": "1 | eval(x)", "cwe": "CWE-95",
    }
    base.update(overrides)
    return Finding(**base)

class HostileScanner:
    name = "evil`scanner"

    def scan(self, workspace, scan_id, timeout):
        finding = make_finding(
            scan_id, scanner="evil`scanner", rule_id="R|1", title=TITLE, evidence=EVIDENCE,
            snippet=SNIPPET, file_path="src/app.py",
        )
        run = ScannerRun(
            scanner="evil`scanner", status="partial", findings_count=1, message="a | b <b>bold</b>"
        )
        return ScannerOutcome(run=run, findings=[finding])

class CleanScanner:
    name = "clean"

    def scan(self, workspace, scan_id, timeout):
        run = ScannerRun(scanner="clean", status="completed", findings_count=1)
        return ScannerOutcome(run=run, findings=[make_finding(scan_id)])

class EmptyScanner:
    name = "empty"

    def scan(self, workspace, scan_id, timeout):
        return ScannerOutcome(run=ScannerRun(scanner="empty", status="completed"), findings=[])

class QueueProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)

    def complete_json(self, messages) -> str:
        return self.responses.pop(0)

def upload(client, make_zip, monkeypatch, scanner) -> str:
    monkeypatch.setattr(scan_service, "default_scanners", lambda: [scanner])
    response = client.post(
        "/api/scans/upload",
        files={"file": ("repo.zip", make_zip({"app.py": "x = 1"}), "application/zip")},
    )
    assert response.status_code == 200
    return response.json()["metadata"]["scan_id"]

def markdown(client, scan_id: str, **params) -> str:
    response = client.get(f"/api/scans/{scan_id}/report", params={"format": "markdown", **params})
    assert response.status_code == 200
    return response.text

def test_json_report_keeps_raw_scanner_evidence_and_no_ai_by_default(client, make_zip, monkeypatch) -> None:
    scan_id = upload(client, make_zip, monkeypatch, HostileScanner())

    response = client.get(f"/api/scans/{scan_id}/report")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert re.fullmatch(
        r'attachment; filename="sentinel-report-[0-9a-f]{8}\.json"',
        response.headers["content-disposition"],
    )
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    body = json.loads(response.text)
    assert body["report_version"] == 1
    assert body["scan"]["metadata"]["scan_id"] == scan_id
    assert body["ai_content_included"] is False
    assert body["ai_disclaimer"] is None
    finding = body["findings"][0]
    assert finding["evidence"] == EVIDENCE
    assert finding["ai_explanation"] is None and finding["suggested_fix"] is None

def test_markdown_report_neutralizes_hostile_repository_text(client, make_zip, monkeypatch) -> None:
    scan_id = upload(client, make_zip, monkeypatch, HostileScanner())

    response = client.get(f"/api/scans/{scan_id}/report", params={"format": "markdown"})
    text = response.text

    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["content-disposition"].endswith('.md"')
    assert "<script>" not in text and "<b>" not in text
    assert "[click](" not in text and "![img](" not in text
    assert "http://evil" not in text
    assert "\n===" not in text and "\n# Injected" not in text
    injected = [line for line in text.splitlines() if line.startswith("#") and "Injected" in line]
    assert len(injected) == 1 and injected[0].startswith("### 1. [HIGH]")
    assert "a \\| b" in text
    assert "``evil`scanner``" in text
    assert "`````text" in text

def test_ai_content_is_opt_in_and_clearly_labelled(client, make_zip, monkeypatch) -> None:
    scan_id = upload(client, make_zip, monkeypatch, CleanScanner())
    finding_id = client.get(f"/api/scans/{scan_id}/findings").json()["items"][0]["id"]
    provider = QueueProvider([EXPLAIN_JSON, FIX_JSON])
    app.dependency_overrides[findings_routes.provider_dependency] = lambda: provider
    assert client.post(f"/api/findings/{finding_id}/explain").status_code == 200
    assert client.post(f"/api/findings/{finding_id}/suggest-fix").status_code == 200

    default_json = json.loads(client.get(f"/api/scans/{scan_id}/report").text)
    assert default_json["findings"][0]["ai_explanation"] is None
    assert default_json["findings"][0]["suggested_fix"] is None
    assert "AI explanation" not in markdown(client, scan_id)

    with_ai = json.loads(client.get(f"/api/scans/{scan_id}/report", params={"include_ai": "true"}).text)
    assert with_ai["ai_content_included"] is True and with_ai["ai_disclaimer"]
    explanation = with_ai["findings"][0]["ai_explanation"]
    assert explanation["provider"] == "fake" and "AI-generated" in explanation["notice"]
    fix = with_ai["findings"][0]["suggested_fix"]
    assert fix["tested"] is False and fix["requires_human_review"] is True
    assert "-eval(x)" in fix["diff"]

    text = markdown(client, scan_id, include_ai="true")
    assert "AI explanation (AI-generated" in text
    assert "UNTESTED" in text
    assert "```diff" in text
    assert "<img" not in text and "**bold**" not in text

def test_report_for_a_scan_without_findings_does_not_claim_safety(client, make_zip, monkeypatch) -> None:
    scan_id = upload(client, make_zip, monkeypatch, EmptyScanner())

    text = markdown(client, scan_id)

    assert "does not prove the code is secure" in text

def test_report_errors(client) -> None:
    assert client.get(f"/api/scans/{'0' * 32}/report").status_code == 404
    assert client.get("/api/scans/not-valid/report").status_code == 422
    assert client.get(f"/api/scans/{'0' * 32}/report", params={"format": "pdf"}).status_code == 422
