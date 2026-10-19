import io
import stat
import zipfile

import httpx
import pytest

from app.services.github_service import (
    RepoRef,
    archive_url,
    download_archive,
    parse_repo_url,
    run_github_scan,
)
from app.services.repository_service import ArchiveLimits, ArchiveRejected, ingest_zip_upload


def mock_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_parse_repository_url_and_build_archive_url() -> None:
    ref = parse_repo_url("HTTPS://GitHub.com/octocat/Hello-World/tree/feature/login/")
    assert ref == RepoRef("octocat", "Hello-World", "feature/login")
    assert archive_url(ref).endswith("/archive/refs/heads/feature/login.zip")


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/octocat/Hello-World",
        "https://evil.example/octocat/Hello-World",
        "https://github.com/octocat/Hello-World/issues",
        "https://github.com/octocat/Hello-World/tree/../secret",
        "https://github.com:8443/octocat/Hello-World",
    ],
)
def test_invalid_repository_urls_are_rejected(url: str) -> None:
    with pytest.raises(ArchiveRejected):
        parse_repo_url(url)


def test_redirects_are_limited_to_github_hosts(tmp_path) -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.host or "")
        return httpx.Response(302, headers={"location": "https://evil.example/repo.zip"})

    with pytest.raises(ArchiveRejected) as error:
        download_archive("https://github.com/o/r/archive/HEAD.zip", tmp_path / "repo.zip", 1000, mock_client(handler))

    assert error.value.status_code == 502
    assert requested == ["github.com"]


def test_github_scan_skips_unsafe_entries_but_upload_rejects(make_zip) -> None:
    data = make_zip(
        {"repo-main/app.py": "x = 1", "repo-main/APP.py": "y = 2", "../evil.py": "z"},
        symlinks={"repo-main/link.py": "/etc/passwd"},
    )
    client = mock_client(lambda request: httpx.Response(200, content=data))

    result = run_github_scan(
        "https://github.com/octocat/Hello-World", client=client, scanners=[]
    )

    assert result.metadata.archive_name == "octocat-Hello-World.zip"
    assert result.metadata.source_files == 1
    assert result.metadata.skipped_entries == 3
    with pytest.raises(ArchiveRejected):
        ingest_zip_upload(io.BytesIO(data), "repo.zip", ArchiveLimits())


def test_download_status_and_size_errors_are_safe(tmp_path) -> None:
    client = mock_client(lambda request: httpx.Response(404, text="private details"))
    with pytest.raises(ArchiveRejected) as error:
        download_archive("https://github.com/o/r/archive/HEAD.zip", tmp_path / "repo.zip", 1000, client)
    assert error.value.status_code == 404
    assert "private details" not in error.value.message

    oversized = mock_client(
        lambda request: httpx.Response(200, content=b"x", headers={"content-length": "1001"})
    )
    with pytest.raises(ArchiveRejected) as error:
        download_archive("https://github.com/o/r/archive/HEAD.zip", tmp_path / "repo.zip", 1000, oversized)
    assert error.value.status_code == 413
