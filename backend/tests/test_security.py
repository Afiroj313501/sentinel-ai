import pytest

from app.core.security import UnsafePathError, ensure_within, normalize_member_name

BAD_NAMES = [
    "../evil.py",
    "a/../../evil.py",
    "/etc/passwd",
    "C:/Windows/evil.py",
    "C:\\evil.py",
    "a\\..\\..\\evil.py",
    "CON.txt",
    "src/nul",
    "file.py ",
    "dir/file.",
    "bad\x00name.py",
    "",
]


@pytest.mark.parametrize("name", BAD_NAMES)
def test_unsafe_names_are_rejected(name: str) -> None:
    with pytest.raises(UnsafePathError):
        normalize_member_name(name)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("src/app.py", "src/app.py"),
        ("./src//app.py", "src/app.py"),
        ("src\\app.py", "src/app.py"),
        (".github/workflows/ci.yml", ".github/workflows/ci.yml"),
    ],
)
def test_safe_names_are_normalized(name: str, expected: str) -> None:
    assert str(normalize_member_name(name)) == expected


def test_ensure_within_accepts_inside_and_rejects_outside(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    assert ensure_within(root, root / "a" / "b.py")
    with pytest.raises(UnsafePathError):
        ensure_within(root, root / ".." / "outside.py")
