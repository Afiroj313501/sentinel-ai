from app.scanners.base import ScannerOutcome
from app.schemas.finding import Finding, ScannerRun
from app.services import scan_service


class FakeScanner:
    name = "fake"

    def scan(self, workspace, scan_id, timeout):
        findings = [
            Finding(
                id="",
                scan_id=scan_id,
                scanner=self.name,
                rule_id="FAKE1",
                title="Dangerous eval call",
                severity="high",
                confidence="high",
                category="security",
                file_path="app.py",
                line_start=1,
                line_end=1,
                evidence="eval is unsafe",
            )
        ]
        return ScannerOutcome(
            run=ScannerRun(scanner=self.name, status="completed", findings_count=1),
            findings=findings,
        )


def _post_scan(client, make_zip) -> str:
    response = client.post(
        "/api/scans/upload",
        files={"file": ("repo.zip", make_zip({"app.py": "x = 1"}), "application/zip")},
    )
    assert response.status_code == 200
    return response.json()["metadata"]["scan_id"]


def test_scan_history_and_finding_filters(client, make_zip, monkeypatch) -> None:
    monkeypatch.setattr(scan_service, "default_scanners", lambda: [FakeScanner()])
    scan_id = _post_scan(client, make_zip)

    history = client.get("/api/scans")
    assert history.status_code == 200
    assert history.json()["total"] == 1
    assert history.json()["items"][0]["scanner_statuses"] == {"fake": "completed"}

    findings = client.get(
        f"/api/scans/{scan_id}/findings", params={"severity": "high", "q": "EVAL"}
    )
    assert findings.status_code == 200
    assert findings.json()["total"] == 1
    finding = findings.json()["items"][0]
    assert client.get(f"/api/findings/{finding['id']}").json() == finding


def test_deleting_scan_deletes_findings(client, make_zip, monkeypatch) -> None:
    monkeypatch.setattr(scan_service, "default_scanners", lambda: [FakeScanner()])
    scan_id = _post_scan(client, make_zip)
    finding_id = client.get(f"/api/scans/{scan_id}/findings").json()["items"][0]["id"]

    assert client.delete(f"/api/scans/{scan_id}").status_code == 204
    assert client.get(f"/api/scans/{scan_id}").status_code == 404
    assert client.get(f"/api/findings/{finding_id}").status_code == 404


def test_malformed_scan_id_is_rejected(client) -> None:
    assert client.get("/api/scans/not-a-scan-id").status_code == 422
