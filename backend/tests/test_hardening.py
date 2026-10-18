import io
import sys
import threading

import pytest
from fastapi.testclient import TestClient

from app.api.routes import scans as scans_routes
from app.core.config import get_settings
from app.main import app
from app.scanners import base
from app.scanners.base import ToolExecutionError, ToolTimeoutError, run_tool
from app.services import scan_service
from app.services.repository_service import ArchiveLimits, ArchiveRejected, ingest_zip_upload

HOSTILE_NAMES = [
    "../evil.py",
    "..\\evil.py",
    "a/../../evil.py",
    "/etc/evil.py",
    "C:/evil.py",
    "C:\\evil.py",
    "CON.py",
    "dir/NUL.txt",
    "trailing.dot.",
    "space.py ",
    "ctrl/\x01evil.py",
    "x" * 300 + ".py",
]

def ingest(data: bytes):
    return ingest_zip_upload(io.BytesIO(data), "repo.zip", ArchiveLimits())

def files(data: bytes, name: str = "repo.zip") -> dict:
    return {"file": (name, data, "application/zip")}

# --- Hostile archives -------------------------------------------------------

@pytest.mark.parametrize("name", HOSTILE_NAMES)
def test_hostile_entry_names_are_rejected_without_echoing_them(make_zip, name: str) -> None:
    with pytest.raises(ArchiveRejected) as exc:
        ingest(make_zip({name: "x", "ok.py": "y"}))

    assert exc.value.status_code == 400
    assert "evil" not in exc.value.message

def test_truncated_and_empty_archives_are_rejected(make_zip) -> None:
    data = make_zip({"a.py": "x" * 200})

    with pytest.raises(ArchiveRejected) as truncated:
        ingest(data[: len(data) // 2])
    assert "valid ZIP" in truncated.value.message

    with pytest.raises(ArchiveRejected) as empty:
        ingest(b"")
    assert "empty" in empty.value.message

def test_a_compression_bomb_entry_is_skipped_not_extracted(make_zip) -> None:
    meta = ingest(make_zip({"bomb.py": "a" * 3_000_000, "ok.py": "x"}))

    assert meta.source_files == 1
    assert meta.skipped_entries == 1

# --- Running scanner tools --------------------------------------------------

def py(code: str, *extra: str) -> list[str]:
    return [sys.executable, "-c", code, *extra]

def test_a_slow_tool_is_stopped_at_the_timeout(tmp_path) -> None:
    with pytest.raises(ToolTimeoutError):
        run_tool(py("import time; time.sleep(30)"), tmp_path, 0.5)

def test_secrets_in_the_environment_never_reach_scanners(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SECRET_TEST_KEY", "leak")
    monkeypatch.setenv("SENTINEL_AI_API_KEY", "super-secret")
    code = (
        "import os; "
        "print(os.environ.get('SECRET_TEST_KEY', 'absent'), "
        "os.environ.get('SENTINEL_AI_API_KEY', 'absent'))"
    )

    result = run_tool(py(code), tmp_path, 30)

    assert result.stdout.strip() == "absent absent"

def test_arguments_are_never_interpreted_by_a_shell(tmp_path) -> None:
    hostile = "x; echo HACKED & whoami | cat"

    result = run_tool(py("import sys; print(sys.argv[1])", hostile), tmp_path, 30)

    assert result.stdout.strip() == hostile

def test_oversized_tool_output_is_refused(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(base, "MAX_OUTPUT_CHARS", 1000)

    with pytest.raises(ToolExecutionError):
        run_tool(py("print('x' * 5000)"), tmp_path, 30)

def test_a_missing_tool_is_a_clean_error(tmp_path) -> None:
    with pytest.raises(ToolExecutionError):
        run_tool(["definitely-not-a-real-tool-xyz"], tmp_path, 5)

# --- HTTP layer -------------------------------------------------------------

@pytest.fixture
def no_scanners(monkeypatch) -> None:
    monkeypatch.setattr(scan_service, "default_scanners", lambda: [])

@pytest.fixture
def small_upload_limit(monkeypatch):
    monkeypatch.setenv("SENTINEL_MAX_UPLOAD_BYTES", "2000")
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()

def test_security_headers_are_on_every_response(client) -> None:
    for path in ("/api/health", "/api/scans/not-valid"):
        response = client.get(path)
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["cache-control"] == "no-store"

def test_oversized_declared_upload_is_rejected_early(client, small_upload_limit) -> None:
    response = client.post("/api/scans/upload", files=files(b"x" * 200_000))

    assert response.status_code == 413
    assert "maximum allowed size" in response.json()["detail"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert client.get("/api/scans").json()["total"] == 0

def test_oversized_chunked_upload_is_rejected_while_streaming(client, small_upload_limit) -> None:
    def chunks():
        for _ in range(10):
            yield b"x" * 20_000

    response = client.post(
        "/api/scans/upload",
        content=chunks(),
        headers={"content-type": "multipart/form-data; boundary=xyz"},
    )

    assert response.status_code == 413
    assert client.get("/api/scans").json()["total"] == 0

def test_file_over_the_exact_limit_is_rejected_by_the_route(client, small_upload_limit) -> None:
    response = client.post("/api/scans/upload", files=files(b"x" * 10_000))

    assert response.status_code == 413

def test_small_valid_upload_still_works_under_a_small_limit(
    client, make_zip, small_upload_limit, no_scanners
) -> None:
    response = client.post("/api/scans/upload", files=files(make_zip({"a.py": "x = 1"})))

    assert response.status_code == 200

def test_busy_server_returns_429_and_always_frees_its_slot(
    client, make_zip, monkeypatch, no_scanners
) -> None:
    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(scan_service, "_scan_slots", slots)
    valid = files(make_zip({"a.py": "x = 1"}))

    assert slots.acquire(blocking=False)
    busy = client.post("/api/scans/upload", files=valid)
    assert busy.status_code == 429
    assert busy.headers["retry-after"]
    slots.release()

    assert client.post("/api/scans/upload", files=valid).status_code == 200
    assert client.post("/api/scans/upload", files=files(make_zip({"../x.py": "y"}))).status_code == 400
    assert slots.acquire(blocking=False)

def test_unexpected_errors_do_not_leak_details(client, make_zip, monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise RuntimeError("secret C:\\server\\path token=abc123")

    monkeypatch.setattr(scans_routes, "run_zip_scan", boom)
    safe_client = TestClient(app, raise_server_exceptions=False)

    response = safe_client.post("/api/scans/upload", files=files(make_zip({"a.py": "x = 1"})))

    assert response.status_code == 500
    assert "secret" not in response.text and "abc123" not in response.text
    assert "server" not in response.text.lower()
