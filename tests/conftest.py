"""Shared pytest fixtures for Project-LMS tests."""

import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager  # noqa: E402
from service import AuthService, ToolService  # noqa: E402


def _cleanup_db(path):
    """Remove a temp SQLite database, handling WAL checkpoint delays.

    SQLite WAL mode can delay file handle release on some filesystems even
    after close().  We retry the remove up to 3 times with a brief sleep.
    """
    if not os.path.exists(path):
        return
    for attempt in range(3):
        try:
            os.remove(path)
            return
        except OSError:
            if attempt < 2:
                time.sleep(0.05)


@pytest.fixture
def db():
    """A fresh, isolated DatabaseManager on a throwaway file."""
    tmp = tempfile.mktemp(suffix=".db")
    mgr = DatabaseManager(tmp)
    yield mgr
    mgr.close()
    _cleanup_db(tmp)
    # Also clean up WAL/Journal sidecars.
    for sidecar in f"{tmp}-wal", f"{tmp}-shm", f"{tmp}-journal":
        _cleanup_db(sidecar)


@pytest.fixture
def tools(db):
    return ToolService(db)


@pytest.fixture
def auth(db):
    return AuthService(db)


@pytest.fixture
def admin_user(db):
    """Create an admin user and return its id."""
    db.insert_user("adminx", "adminpass1", "Admin", 30, "admin@x.com", is_admin=1)
    return db._execute_query(
        "SELECT id FROM users WHERE username='adminx'", fetch=True
    )[0]["id"]


@pytest.fixture
def regular_user(db):
    """Create a regular (non-admin) user and return its id."""
    db.insert_user("userx", "userpass1", "User", 20, "user@x.com", is_admin=0)
    return db._execute_query(
        "SELECT id FROM users WHERE username='userx'", fetch=True
    )[0]["id"]
