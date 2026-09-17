"""Tests for compatibility utilities."""

import pytest
from regex_droid_builder.compat import (
    normalize_path,
    ensure_dir,
    safe_join,
    atomic_write_bytes,
    atomic_write_text,
    safe_read_bytes,
    safe_read_text,
    get_default_storage_dir,
)


def test_normalize_path():
    p = normalize_path(".")
    assert p.is_absolute()


def test_ensure_dir(tmp_path):
    d = ensure_dir(tmp_path / "a" / "b")
    assert d.is_dir()


def test_safe_join(tmp_path):
    valid = safe_join(tmp_path, "sub", "file.txt")
    assert valid.name == "file.txt"

    with pytest.raises(PermissionError):
        safe_join(tmp_path, "../../etc/passwd")


def test_atomic_write_and_read(tmp_path):
    target = tmp_path / "regex.txt"
    atomic_write_text(target, "pattern = ^[a-z]+$")
    assert target.exists()
    assert "pattern = ^[a-z]+$" in safe_read_text(target)


def test_get_default_storage_dir():
    d = get_default_storage_dir()
    assert d.is_dir()
