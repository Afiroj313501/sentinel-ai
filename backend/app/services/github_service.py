"""Download and scan public GitHub repositories without fetching user-controlled URLs."""

from __future__ import annotations

import re
import tempfile
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

from app.core.config import get_settings
from app.scanners.base import Scanner
from app.schemas.finding import ScanResult
from app.services.repository_service import ArchiveLimits, ArchiveRejected
from app.services.scan_service import ScanBusy, run_zip_scan

REPO_URL_ERROR = "Enter a public GitHub repository URL, like https://github.com/owner/repo."
USER_AGENT = "sentinel-ai-scanner/0.1"
ALLOWED_HOSTS = frozenset({"github.com", "codeload.github.com"})
MAX_URL_CHARS = 300
MAX_REDIRECTS = 3
DOWNLOAD_TIMEOUT_SECONDS = 60.0
CHUNK_SIZE = 64 * 1024
MAX_CONCURRENT_DOWNLOADS = 2
_download_slots = threading.BoundedSemaphore(MAX_CONCURRENT_DOWNLOADS)

_OWNER = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}")
_REPO = re.compile(r"[A-Za-z0-9._-]{1,100}")
_BRANCH = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,99}")
_URL_FORBIDDEN = re.compile(r"[\s\x00-\x1f\x7f\\]")


@dataclass(frozen=True)
class RepoRef:
    owner: str
    repo: str
    branch: str | None


def parse_repo_url(raw: str) -> RepoRef:
    text = raw.strip()
    if not text or len(text) > MAX_URL_CHARS or _URL_FORBIDDEN.search(text):
        raise ArchiveRejected(REPO_URL_ERROR)
    try:
        parts = urlsplit(text)
        host, port = parts.hostname, parts.port
    except ValueError as exc:
        raise ArchiveRejected(REPO_URL_ERROR) from exc
    if (
        parts.scheme.lower() != "https"
        or (host or "").lower() != "github.com"
        or port is not None
        or parts.username
        or parts.password
    ):
        raise ArchiveRejected(REPO_URL_ERROR)

    segments = [part for part in parts.path.split("/") if part]
    if len(segments) < 2:
        raise ArchiveRejected(REPO_URL_ERROR)
    owner, repo = segments[:2]
    if repo.endswith(".git"):
        repo = repo[:-4]
    branch = None
    if len(segments) > 2:
        if segments[2] != "tree" or len(segments) < 4:
            raise ArchiveRejected(REPO_URL_ERROR)
        branch = "/".join(segments[3:])
    if not _OWNER.fullmatch(owner) or not _REPO.fullmatch(repo) or repo in (".", ".."):
        raise ArchiveRejected(REPO_URL_ERROR)
    if branch is not None and (
        not _BRANCH.fullmatch(branch) or any(part in (".", "..") for part in branch.split("/"))
    ):
        raise ArchiveRejected(REPO_URL_ERROR)
    return RepoRef(owner, repo, branch)


def archive_url(ref: RepoRef) -> str:
    target = f"refs/heads/{ref.branch}" if ref.branch else "HEAD"
    return f"https://github.com/{ref.owner}/{ref.repo}/archive/{target}.zip"


def display_filename(ref: RepoRef) -> str:
    return f"{ref.owner}-{ref.repo}"[:90] + ".zip"


def _redirect_target(current: str, response: httpx.Response) -> str:
    target = urljoin(current, response.headers.get("location", ""))
    try:
        parts = urlsplit(target)
        host, port = parts.hostname, parts.port
    except ValueError as exc:
        raise ArchiveRejected("GitHub redirected to an unexpected address.", 502) from exc
    if (
        parts.scheme != "https"
        or host not in ALLOWED_HOSTS
        or port is not None
        or parts.username
        or parts.password
    ):
        raise ArchiveRejected("GitHub redirected to an unexpected address.", 502)
    return target


def _save_response(response: httpx.Response, dest: Path, max_bytes: int, deadline: float) -> int:
    status = response.status_code
    if status == 404:
        raise ArchiveRejected("Repository or branch not found. Only public repositories can be scanned.", 404)
    if status in (401, 403):
        raise ArchiveRejected("GitHub refused the download. The repository may be private, or GitHub is limiting requests.", 502)
    if status == 429:
        raise ArchiveRejected("GitHub rate limit reached. Try again later.", 503)
    if status != 200:
        raise ArchiveRejected(f"GitHub returned an unexpected response (HTTP {status}).", 502)
    too_large = ArchiveRejected("Repository archive exceeds the maximum allowed size.", 413)
    declared = response.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > max_bytes:
        raise too_large
    written = 0
    with dest.open("wb") as out:
        for chunk in response.iter_bytes(CHUNK_SIZE):
            if time.monotonic() > deadline:
                raise ArchiveRejected("Downloading the repository took too long.", 504)
            written += len(chunk)
            if written > max_bytes:
                raise too_large
            out.write(chunk)
    if written == 0:
        raise ArchiveRejected("GitHub returned an empty archive.", 502)
    return written


def download_archive(
    url: str,
    dest: Path,
    max_bytes: int,
    client: httpx.Client | None = None,
    timeout: float = DOWNLOAD_TIMEOUT_SECONDS,
) -> int:
    deadline = time.monotonic() + timeout
    http = client or httpx.Client(
        timeout=httpx.Timeout(timeout),
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT, "Accept": "application/zip"},
    )
    try:
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            with http.stream("GET", current) as response:
                if response.is_redirect:
                    current = _redirect_target(current, response)
                    continue
                return _save_response(response, dest, max_bytes, deadline)
        raise ArchiveRejected("GitHub redirected too many times.", 502)
    except httpx.TimeoutException as exc:
        raise ArchiveRejected("Downloading the repository took too long.", 504) from exc
    except httpx.HTTPError as exc:
        raise ArchiveRejected("Could not download the repository from GitHub.", 502) from exc
    finally:
        if client is None:
            http.close()


def run_github_scan(
    url: str,
    client: httpx.Client | None = None,
    scanners: Sequence[Scanner] | None = None,
) -> ScanResult:
    ref = parse_repo_url(url)
    if not _download_slots.acquire(blocking=False):
        raise ScanBusy()
    try:
        with tempfile.TemporaryDirectory(prefix="sentinel_dl_") as tmp:
            archive = Path(tmp) / "repo.zip"
            download_archive(archive_url(ref), archive, get_settings().max_upload_bytes, client)
            limits = replace(ArchiveLimits.from_settings(), lenient=True)
            with archive.open("rb") as stream:
                return run_zip_scan(stream, display_filename(ref), limits, scanners)
    finally:
        _download_slots.release()
