"""Tests for the DatabaseManager persistence layer."""

import datetime

import pytest


def test_add_tool_roundtrip(db):
    assert db.add_tool("Hammer", "Tools", "Good", 5, "Shelf A")
    rows = db.fetch_tool_by_name("Hammer")
    assert len(rows) == 1
    assert rows[0]["quantity"] == 5
    assert rows[0]["status"] == "available"


def test_update_tool_partial(db):
    db.add_tool("Hammer", "Tools", "Good", 5, "Shelf A")
    tool_id = db.fetch_tool_by_name("Hammer")[0]["tool_id"]
    assert db.update_tool(tool_id, quantity=9, location="Shelf Z")
    row = db.fetch_tool_by_id(tool_id)
    assert row["quantity"] == 9
    assert row["location"] == "Shelf Z"
    assert row["name"] == "Hammer"  # untouched field preserved


def test_update_tool_missing_returns_false(db):
    assert db.update_tool(99999, quantity=1) is False


def test_delete_tool(db):
    db.add_tool("Hammer", "Tools", "Good", 5, "Shelf A")
    tool_id = db.fetch_tool_by_name("Hammer")[0]["tool_id"]
    assert db.delete_tool(tool_id)
    assert db.fetch_tool_by_id(tool_id) is None


def test_delete_missing_returns_false(db):
    assert db.delete_tool(99999) is False


def test_clear_tables(db, admin_user, regular_user):
    db.add_tool("A", "C", "Good", 1, "L")
    db.add_tool("B", "C", "Good", 1, "L")
    assert db.count_tools() == 2
    # actor_id is mandatory; the DB-layer gate must actually reject non-admins.
    assert db.clear_tables(regular_user) is False
    assert db.clear_tables(admin_user)
    assert db.count_tools() == 0


def test_search_tool_case_insensitive(db):
    db.add_tool("Hammer", "Tools", "Good", 5, "Shelf A")
    db.add_tool("Screwdriver", "Tools", "Good", 3, "Shelf B")
    assert len(db.search_tool("HAMMER")) == 1
    assert len(db.search_tool("tool")) == 2


def test_pagination(db):
    for i in range(25):
        db.add_tool(f"Tool{i}", "C", "Good", 1, "L")
    page1 = db.fetch_tools_paginated(1, 20)
    page2 = db.fetch_tools_paginated(2, 20)
    assert len(page1) == 20
    assert len(page2) == 5


def test_user_insert_and_authenticate(db):
    assert db.insert_user("alice", "secret123", "Alice", 20, "a@b.c")
    user = db.authenticate("alice", "secret123")
    assert user is not None
    assert db.authenticate("alice", "wrong") is None
    assert db.authenticate("ghost", "secret123") is None


def test_insert_duplicate_user_fails(db):
    assert db.insert_user("alice", "secret123", "Alice", 20, "a@b.c")
    assert db.insert_user("alice", "other123", "Alice", 20, "a@b.c") is False


def test_is_admin_flag(db):
    # insert_user returns bool; fetch id separately
    db.insert_user("bob", "secret123", "Bob", 25, "b@b.c")
    bob = db._execute_query("SELECT id FROM users WHERE username='bob'", fetch=True)[0]
    assert db.is_admin(bob["id"]) is False
    assert db.set_admin(bob["id"], True)
    assert db.is_admin(bob["id"]) is True


def test_borrow_return_ownership(db, regular_user):
    db.add_tool("Hammer", "Tools", "Good", 5, "Shelf A")
    tool_id = db.fetch_tool_by_name("Hammer")[0]["tool_id"]
    assert db.borrow_tool(tool_id, regular_user, "", "2026-08-02")
    borrowed = db.fetch_borrowed_by_user(regular_user)
    assert [t["tool_id"] for t in borrowed] == [tool_id]

    # Wrong owner cannot return.
    assert db.return_tool(tool_id, 999, "2026-08-03") is False
    # Right owner can return.
    assert db.return_tool(tool_id, regular_user, "2026-08-03") is True
    assert db.fetch_borrowed_by_user(regular_user) == []


def test_borrow_unavailable_tool(db, regular_user):
    db.add_tool("Hammer", "Tools", "Good", 0, "Shelf A")
    tool_id = db.fetch_tool_by_name("Hammer")[0]["tool_id"]
    # Documented contract: distinguishable rejection (ValueError), not a
    # bare False that collapses every failure mode together.
    with pytest.raises(ValueError):
        db.borrow_tool(tool_id, regular_user, "", "2026-08-02")


def test_login_rate_limiting(db):
    db.insert_user("alice", "secret123", "Alice", 20, "a@b.c")
    # Exhaust the window.
    for _ in range(db.MAX_LOGIN_ATTEMPTS):
        db.authenticate("alice", "wrong")
    assert db._too_many_attempts("alice")
    # Even a correct password is rejected while rate-limited.
    assert db.authenticate("alice", "secret123") is None


# ---------------------------------------------------------------------------
# Regression tests from code review (Q1/Q2/Q3/S2 coverage gaps)
# ---------------------------------------------------------------------------


def test_delete_tool_with_transactions(db, regular_user):
    """Q1 regression: parent delete must not precede child purge (FK order)."""
    db.add_tool("Hammer", "Tools", "Good", 5, "Shelf A")
    tool_id = db.fetch_tool_by_name("Hammer")[0]["tool_id"]
    assert db.borrow_tool(tool_id, regular_user, "", "2026-08-02")
    # With foreign_keys=ON, the old delete-parent-first ordering raised
    # IntegrityError here and made every ever-borrowed tool undeletable.
    assert db.delete_tool(tool_id)
    assert db.fetch_tool_by_id(tool_id) is None


def test_multi_quantity_single_borrower_semantics(db, regular_user):
    """Q2/Q3 regression: return status + documented single-borrower model."""
    db.add_tool("Drill", "Tools", "Good", 5, "Shelf A")
    tool_id = db.fetch_tool_by_name("Drill")[0]["tool_id"]
    assert db.borrow_tool(tool_id, regular_user, "", "2026-08-02")
    row = db.fetch_tool_by_id(tool_id)
    assert row["quantity"] == 4
    assert row["status"] == "borrowed"
    # Single-owner model: remaining stock is NOT borrowable by others until
    # the holder returns (documented in fetch_borrowable_tools). The
    # distinguishable ValueError contract applies to this path too.
    with pytest.raises(ValueError):
        db.borrow_tool(tool_id, 999, "", "2026-08-02")
    assert db.return_tool(tool_id, regular_user, "2026-08-03")
    row = db.fetch_tool_by_id(tool_id)
    assert row["quantity"] == 5
    assert row["status"] == "available"
    assert row["user_id"] is None


def test_lockout_applies_to_unknown_usernames(db):
    """S2 regression: attempts for missing users are recorded (lockout holds)."""
    for _ in range(db.MAX_LOGIN_ATTEMPTS):
        db.authenticate("ghost", "whatever")
    assert db.is_locked_out("ghost")
    assert db.authenticate("ghost", "anything") is None


def test_borrow_records_username(db, regular_user):
    """Q4 regression: borrower column carries a real username."""
    db.add_tool("Saw", "Tools", "Good", 1, "Shelf B")
    tool_id = db.fetch_tool_by_name("Saw")[0]["tool_id"]
    assert db.borrow_tool(tool_id, regular_user, "userx", "2026-08-02")
    assert db.fetch_tool_by_id(tool_id)["borrower"] == "userx"


def test_case_insensitive_duplicate_names_blocked_at_db_level(db):
    """Q5 regression: schema-level COLLATE NOCASE unique index.

    insert_tool catches sqlite3.IntegrityError and reports False, so the
    duplicate must surface as a False return, not an exception.
    """
    assert db.add_tool("Hammer", "Tools", "Good", 1, "Shelf A")
    assert db.add_tool("HAMMER", "Tools", "Good", 1, "Shelf B") is False
