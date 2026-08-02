"""Shared pytest fixtures for Project-LMS tests."""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager  # noqa: E402
from service import AuthService, ToolService  # noqa: E402


@pytest.fixture
def db():
    """A fresh, isolated DatabaseManager on a throwaway file."""
    tmp = tempfile.mktemp(suffix=".db")
    mgr = DatabaseManager(tmp)
    yield mgr
    mgr.close()
    try:
        os.remove(tmp)
    except OSError:
        pass


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
