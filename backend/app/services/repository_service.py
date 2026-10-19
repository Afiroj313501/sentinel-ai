"""Secure repository ingestion: bounded upload, safe ZIP extraction, metadata."""

from __future__ import annotations

import re
import stat
import tempfile
import time
import zipfile
import zlib
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import BinaryIO
from uuid import uuid4

from app.core.config import get_settings
from app.core.security import UnsafePathError, ensure_within, normalize_member_name
from app.schemas.scan import RepositoryMetadata

CHUNK_SIZE = 64 * 1024

IGNORED_DIRS = frozenset({
    ".git", ".hg", ".svn", "node_modules", "__pycache__", "__MACOSX",
    ".venv", "venv", "dist", "build", ".next", "coverage",
    ".idea", ".vscode", ".pytest_cache", ".mypy_cache",
})

LANGUAGE_BY_EXTENSION = {
    ".py": "Python",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".json": "JSON", ".yml": "YAML", ".yaml": "YAML", ".toml": "TOML",
    ".html": "HTML", ".css": "CSS", ".md": "Markdown", ".txt": "Text",
    ".ini": "Config", ".cfg": "Config", ".sh": "Shell",
}
ALLOWED_EXTENSIONS = frozenset(LANGUAGE_BY_EXTENSION)
LANGUAGE_BY_FILENAME = {"Dockerfile": "Dockerfile", "Pipfile": "TOML", "Makefile": "Makefile"}
MANIFEST_NAMES = frozenset(
    {"requirements.txt", "pyproject.toml", "Pipfile", "package.json", "package-lock.json"}
)


class ArchiveRejected(Exception):
    """Raised when an upload is refused. The message is safe to show to users."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class ArchiveLimits:
    max_upload_bytes: int = 25 * 1024 * 1024
    max_archive_entries: int = 5000
    max_extracted_files: int = 2000
    max_file_bytes: int = 1024 * 1024
    max_total_extracted_bytes: int = 100 * 1024 * 1024
    max_extraction_seconds: float = 30.0
    lenient: bool = False

    @classmethod
    def from_settings(cls) -> ArchiveLimits:
        s = get_settings()
        return cls(
            max_upload_bytes=s.max_upload_bytes,
            max_archive_entries=s.max_archive_entries,
            max_extracted_files=s.max_extracted_files,
            max_file_bytes=s.max_file_bytes,
            max_total_extracted_bytes=s.max_total_extracted_bytes,
            max_extraction_seconds=s.max_extraction_seconds,
        )


@dataclass
class ExtractionResult:
    files: list[PurePosixPath] = field(default_factory=list)
    skipped: int = 0
    total_bytes: int = 0


@dataclass(frozen=True)
class IngestedRepository:
    scan_id: str
    workspace: Path
    metadata: RepositoryMetadata


def _display_name(filename: str) -> str:
    """Return a safe, short display name for an uploaded file."""
    base = filename.replace("\\", "/").rsplit("/", 1)[-1]
    base = re.sub(r"[\x00-\x1f]", "", base).strip()[:100]
    return base or "upload.zip"


def save_upload(source: BinaryIO, destination: Path, max_bytes: int) -> int:
    """Stream an upload to disk, refusing anything larger than max_bytes."""
    written = 0
    with destination.open("wb") as out:
        while chunk := source.read(CHUNK_SIZE):
            written += len(chunk)
            if written > max_bytes:
                raise ArchiveRejected("Upload exceeds the maximum allowed size.", 413)
            out.write(chunk)
    if written == 0:
        raise ArchiveRejected("Uploaded file is empty.")
    return written


def _validate_entries(
    infos: list[zipfile.ZipInfo], lenient: bool = False
) -> tuple[list[tuple[zipfile.ZipInfo, PurePosixPath]], int]:
    """Check every entry, optionally skipping unsafe GitHub entries."""
    planned: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
    seen: set[str] = set()
    skipped = 0
    for info in infos:
        try:
            rel = normalize_member_name(info.filename)
        except UnsafePathError as exc:
            if lenient:
                skipped += 1
                continue
            raise ArchiveRejected(f"Archive contains an unsafe entry: {exc}.") from exc
        if info.flag_bits & 0x1:
            raise ArchiveRejected("Encrypted archives are not supported.")
        mode = info.external_attr >> 16
        is_symlink = stat.S_ISLNK(mode)
        if is_symlink or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
            if lenient:
                skipped += 1
                continue
            if is_symlink:
                raise ArchiveRejected("Archive contains a symbolic link.")
            raise ArchiveRejected("Archive contains a special file entry.")
        key = str(rel).lower()
        if key in seen:
            if lenient:
                skipped += 1
                continue
            raise ArchiveRejected("Archive contains duplicate entries.")
        seen.add(key)
        planned.append((info, rel))
    return planned, skipped


def _strip_common_root(
    planned: list[tuple[zipfile.ZipInfo, PurePosixPath]],
) -> list[tuple[zipfile.ZipInfo, PurePosixPath]]:
    """Drop a single top-level folder (e.g. GitHub's 'repo-main/') from all paths."""
    if not planned:
        return planned
    roots = {rel.parts[0] for _, rel in planned}
    files_at_top = any(len(rel.parts) < 2 for info, rel in planned if not info.is_dir())
    if len(roots) != 1 or files_at_top:
        return planned
    return [
        (info, PurePosixPath(*rel.parts[1:])) for info, rel in planned if len(rel.parts) > 1
    ]


def _should_extract(rel: PurePosixPath) -> bool:
    if any(part in IGNORED_DIRS for part in rel.parts[:-1]):
        return False
    if rel.name.endswith((".min.js", ".min.css")):
        return False
    return rel.suffix.lower() in ALLOWED_EXTENSIONS or rel.name in LANGUAGE_BY_FILENAME


def _copy_member(
    zf: zipfile.ZipFile, info: zipfile.ZipInfo, target: Path, max_bytes: int
) -> int | None:
    """Copy one entry to disk. Returns bytes written, or None if it looks binary."""
    written = 0
    with zf.open(info) as src:
        head = src.read(1024)
        if b"\x00" in head:
            return None
        with target.open("xb") as out:
            chunk = head
            while chunk:
                written += len(chunk)
                if written > max_bytes:
                    raise ArchiveRejected("Archive entry exceeds the allowed file size.")
                out.write(chunk)
                chunk = src.read(CHUNK_SIZE)
    return written


def extract_zip(archive_path: Path, dest: Path, limits: ArchiveLimits) -> ExtractionResult:
    """Safely extract supported source files from a ZIP archive into dest."""
    try:
        zf = zipfile.ZipFile(archive_path)
    except zipfile.BadZipFile as exc:
        raise ArchiveRejected("File is not a valid ZIP archive.") from exc

    result = ExtractionResult()
    deadline = time.monotonic() + limits.max_extraction_seconds
    dest_root = dest.resolve()

    try:
        with zf:
            infos = zf.infolist()
            if len(infos) > limits.max_archive_entries:
                raise ArchiveRejected("Archive contains too many entries.")
            planned_entries, unsafe_skipped = _validate_entries(infos, limits.lenient)
            planned = _strip_common_root(planned_entries)
            result.skipped += unsafe_skipped

            for info, rel in planned:
                if time.monotonic() >= deadline:
                    raise ArchiveRejected("Archive extraction took too long.")
                if info.is_dir():
                    continue
                if not _should_extract(rel) or info.file_size > limits.max_file_bytes:
                    result.skipped += 1
                    continue
                if len(result.files) >= limits.max_extracted_files:
                    raise ArchiveRejected("Archive contains too many source files.")
                if result.total_bytes + info.file_size > limits.max_total_extracted_bytes:
                    raise ArchiveRejected("Archive exceeds the maximum extracted size.")

                target = ensure_within(dest_root, dest_root / Path(*rel.parts))
                target.parent.mkdir(parents=True, exist_ok=True)
                written = _copy_member(zf, info, target, limits.max_file_bytes)
                if written is None:
                    result.skipped += 1
                    continue
                result.total_bytes += written
                result.files.append(rel)
    except UnsafePathError as exc:
        raise ArchiveRejected(f"Archive contains an unsafe entry: {exc}.") from exc
    except (OSError, zipfile.BadZipFile, zlib.error, EOFError, NotImplementedError, RuntimeError) as exc:
        raise ArchiveRejected("Archive could not be extracted safely.") from exc

    return result


def build_metadata(scan_id: str, archive_name: str, result: ExtractionResult) -> RepositoryMetadata:
    languages: Counter[str] = Counter()
    manifests: list[str] = []
    for rel in result.files:
        language = LANGUAGE_BY_EXTENSION.get(rel.suffix.lower()) or LANGUAGE_BY_FILENAME.get(rel.name)
        if language:
            languages[language] += 1
        if rel.name in MANIFEST_NAMES:
            manifests.append(str(rel))
    return RepositoryMetadata(
        scan_id=scan_id,
        archive_name=archive_name,
        source_files=len(result.files),
        skipped_entries=result.skipped,
        total_bytes=result.total_bytes,
        languages=dict(languages),
        dependency_manifests=sorted(manifests),
    )


@contextmanager
def ingest_zip_workspace(
    source: BinaryIO, filename: str, limits: ArchiveLimits | None = None
) -> Iterator[IngestedRepository]:
    """Validate and extract an uploaded ZIP while its workspace is in use."""
    limits = limits or ArchiveLimits.from_settings()
    archive_name = _display_name(filename)
    if not archive_name.lower().endswith(".zip"):
        raise ArchiveRejected("Only .zip uploads are supported.", 415)

    scan_id = uuid4().hex
    with tempfile.TemporaryDirectory(prefix="sentinel_", ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        archive_path = tmp_path / "upload.zip"
        save_upload(source, archive_path, limits.max_upload_bytes)

        workspace = tmp_path / "repo"
        workspace.mkdir()
        result = extract_zip(archive_path, workspace, limits)
        if not result.files:
            raise ArchiveRejected("No supported source files were found in the archive.", 422)
        yield IngestedRepository(
            scan_id=scan_id,
            workspace=workspace,
            metadata=build_metadata(scan_id, archive_name, result),
        )


def ingest_zip_upload(
    source: BinaryIO, filename: str, limits: ArchiveLimits | None = None
) -> RepositoryMetadata:
    """Validate and extract an uploaded ZIP, return metadata, and clean up."""
    with ingest_zip_workspace(source, filename, limits) as repo:
        return repo.metadata
