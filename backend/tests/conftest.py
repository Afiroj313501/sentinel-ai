import io
import stat
import zipfile

import pytest


@pytest.fixture
def make_zip():
    """Return a function that builds ZIP bytes, optionally with symlink entries."""

    def _make(entries: dict[str, bytes | str], symlinks: dict[str, str] | None = None) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, content in entries.items():
                zf.writestr(name, content)
            for name, target in (symlinks or {}).items():
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                zf.writestr(info, target)
        return buffer.getvalue()

    return _make
