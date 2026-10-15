from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def post_zip(data: bytes, name: str = "repo.zip"):
    return client.post("/api/scans/upload", files={"file": (name, data, "application/zip")})


def test_upload_valid_zip(make_zip) -> None:
    response = post_zip(make_zip({"repo/app.py": "print(1)", "repo/package.json": "{}"}))

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["source_files"] == 2
    assert body["metadata"]["languages"] == {"Python": 1, "JSON": 1}
    assert body["metadata"]["dependency_manifests"] == ["package.json"]
    assert len(body["metadata"]["scan_id"]) == 32
    assert {run["scanner"] for run in body["scanner_runs"]} == {
        "bandit", "semgrep", "pip-audit", "npm-audit"
    }
    assert body["findings"] == []
    assert set(body["severity_counts"]) == {"critical", "high", "medium", "low", "info"}
    assert body["notice"]


def test_upload_traversal_returns_400_without_echoing_entry_name(make_zip) -> None:
    response = post_zip(make_zip({"../evil.py": "x"}))

    assert response.status_code == 400
    assert "evil" not in response.json()["detail"]


def test_upload_wrong_extension_returns_415(make_zip) -> None:
    assert post_zip(make_zip({"a.py": "x"}), name="repo.tar").status_code == 415


def test_upload_without_file_returns_422() -> None:
    assert client.post("/api/scans/upload").status_code == 422
