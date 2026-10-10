"""Path-safety helpers for untrusted archive entries."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

MAX_PATH_CHARS = 240

WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_INVALID_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')
_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")


class UnsafePathError(ValueError):
    """Raised when an archive entry name is unsafe to extract."""


def normalize_member_name(name: str) -> PurePosixPath:
    """Validate an archive entry name and return a clean relative POSIX path."""
    if not name or "\x00" in name:
        raise UnsafePathError("empty or invalid entry name")

    unified = name.replace("\\", "/")
    if len(unified) > MAX_PATH_CHARS:
        raise UnsafePathError("entry path is too long")
    if unified.startswith("/") or _DRIVE_PREFIX.match(unified):
        raise UnsafePathError("absolute path in archive")

    parts = [part for part in unified.split("/") if part not in ("", ".")]
    if not parts:
        raise UnsafePathError("empty entry path")

    for part in parts:
        if part == "..":
            raise UnsafePathError("path traversal in archive")
        if _INVALID_CHARS.search(part):
            raise UnsafePathError("invalid characters in entry name")
        if part.endswith((" ", ".")):
            raise UnsafePathError("entry name ends with a space or dot")
        if part.split(".")[0].upper() in WINDOWS_RESERVED:
            raise UnsafePathError("reserved device name in entry")

    return PurePosixPath(*parts)


def ensure_within(root: Path, target: Path) -> Path:
    """Return the resolved target, or raise if it escapes the root directory."""
    resolved_root = root.resolve()
    resolved = target.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise UnsafePathError("entry escapes the extraction directory")
    return resolved
