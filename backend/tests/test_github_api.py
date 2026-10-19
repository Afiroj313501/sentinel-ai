import httpx

from app.api.routes import github as github_routes
from app.services import github_service


def test_github_scan_route_stores_result(client, make_zip, monkeypatch) -> None:
    data = make_zip({"repo-main/app.py": "print(1)"})
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=data))
    http_client = httpx.Client(transport=transport)
    real_scan = github_service.run_github_scan
    monkeypatch.setattr(
        github_routes,
        "run_github_scan",
        lambda url: real_scan(url, client=http_client, scanners=[]),
    )

    response = client.post(
        "/api/scans/github", json={"url": "https://github.com/octocat/Hello-World"}
    )

    assert response.status_code == 200
    assert response.json()["metadata"]["archive_name"] == "octocat-Hello-World.zip"


def test_github_scan_route_validates_url_and_request_size(client) -> None:
    invalid = client.post("/api/scans/github", json={"url": "https://evil.example/o/r"})
    assert invalid.status_code == 400
    assert "public GitHub repository URL" in invalid.json()["detail"]

    oversized = client.post("/api/scans/github", json={"url": "x" * 10_000})
    assert oversized.status_code == 413
    assert oversized.headers["x-content-type-options"] == "nosniff"
