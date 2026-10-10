import io
import tempfile

import pytest

from app.services.repository_service import ArchiveLimits, ArchiveRejected, ingest_zip_upload


def ingest(data: bytes, name: str = "repo.zip", **limit_overrides):
    return ingest_zip_upload(io.BytesIO(data), name, ArchiveLimits(**limit_overrides))


def test_valid_archive_returns_metadata(make_zip) -> None:
    data = make_zip(
        {
            "repo-main/app.py": "print(1)",
            "repo-main/requirements.txt": "flask",
            "repo-main/node_modules/x/index.js": "x",
            "repo-main/logo.png": b"\x89PNG",
        }
    )
    meta = ingest(data)

    assert meta.archive_name == "repo.zip"
    assert meta.source_files == 2
    assert meta.skipped_entries == 2
    assert meta.languages == {"Python": 1, "Text": 1}
    assert meta.dependency_manifests == ["requirements.txt"]


def test_path_traversal_is_rejected(make_zip) -> None:
    with pytest.raises(ArchiveRejected) as exc:
        ingest(make_zip({"../evil.py": "x", "ok.py": "y"}))
    assert "unsafe" in exc.value.message


def test_symlink_is_rejected(make_zip) -> None:
    with pytest.raises(ArchiveRejected) as exc:
        ingest(make_zip({"ok.py": "y"}, symlinks={"link.py": "/etc/passwd"}))
    assert "symbolic link" in exc.value.message


def test_case_insensitive_duplicates_are_rejected(make_zip) -> None:
    with pytest.raises(ArchiveRejected):
        ingest(make_zip({"A.py": "1", "a.py": "2"}))


def test_too_many_entries_is_rejected(make_zip) -> None:
    data = make_zip({f"f{i}.py": "x" for i in range(5)})
    with pytest.raises(ArchiveRejected):
        ingest(data, max_archive_entries=3)


def test_too_many_source_files_is_rejected(make_zip) -> None:
    data = make_zip({f"f{i}.py": "x" for i in range(3)})
    with pytest.raises(ArchiveRejected):
        ingest(data, max_extracted_files=2)


def test_oversized_upload_returns_413(make_zip) -> None:
    with pytest.raises(ArchiveRejected) as exc:
        ingest(make_zip({"a.py": "a" * 10_000}), max_upload_bytes=50)
    assert exc.value.status_code == 413


def test_extracted_size_bomb_is_rejected(make_zip) -> None:
    data = make_zip({"a.py": "a" * 600, "b.py": "b" * 600})
    with pytest.raises(ArchiveRejected) as exc:
        ingest(data, max_total_extracted_bytes=1000)
    assert "extracted size" in exc.value.message


def test_oversized_single_file_is_skipped(make_zip) -> None:
    meta = ingest(make_zip({"big.py": "a" * 500, "ok.py": "x"}), max_file_bytes=100)
    assert meta.source_files == 1
    assert meta.skipped_entries == 1


def test_binary_file_with_source_extension_is_skipped(make_zip) -> None:
    meta = ingest(make_zip({"a.py": "ok", "b.py": b"\x00\x01\x02"}))
    assert meta.source_files == 1
    assert meta.skipped_entries == 1


def test_extraction_timeout_is_enforced(make_zip) -> None:
    with pytest.raises(ArchiveRejected) as exc:
        ingest(make_zip({"a.py": "x"}), max_extraction_seconds=0.0)
    assert "too long" in exc.value.message


def test_non_zip_content_is_rejected() -> None:
    with pytest.raises(ArchiveRejected):
        ingest(b"this is not a zip")


def test_wrong_extension_returns_415(make_zip) -> None:
    with pytest.raises(ArchiveRejected) as exc:
        ingest(make_zip({"a.py": "x"}), name="repo.tar")
    assert exc.value.status_code == 415


def test_archive_without_source_files_returns_422(make_zip) -> None:
    with pytest.raises(ArchiveRejected) as exc:
        ingest(make_zip({"logo.png": b"\x89PNG"}))
    assert exc.value.status_code == 422


def test_uploaded_filename_is_sanitized(make_zip) -> None:
    meta = ingest(make_zip({"a.py": "x"}), name="..\\..\\evil\\repo.zip")
    assert meta.archive_name == "repo.zip"


def test_temp_workspace_is_cleaned_up(make_zip, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))

    ingest(make_zip({"a.py": "x"}))
    assert list(tmp_path.iterdir()) == []

    with pytest.raises(ArchiveRejected):
        ingest(make_zip({"../evil.py": "x"}))
    assert list(tmp_path.iterdir()) == []
