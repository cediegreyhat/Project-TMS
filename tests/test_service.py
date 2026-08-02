"""Tests for the business logic layer (ToolService / AuthService)."""

import pytest

from service import ServiceError


class TestAuthService:
    def test_register_valid(self, auth):
        assert auth.register("bob", "secret123", "secret123", "Bob", 20, "b@b.com")

    def test_register_short_password(self, auth):
        with pytest.raises(ServiceError):
            auth.register("bob", "short", "short", "Bob", 20, "b@b.com")

    def test_register_mismatched_password(self, auth):
        with pytest.raises(ServiceError):
            auth.register("bob", "secret123", "nomatch", "Bob", 20, "b@b.com")

    def test_register_bad_email(self, auth):
        with pytest.raises(ServiceError):
            auth.register("bob", "secret123", "secret123", "Bob", 20, "notanemail")

    def test_register_invalid_age(self, auth):
        with pytest.raises(ServiceError):
            auth.register("bob", "secret123", "secret123", "Bob", 5, "b@b.com")

    def test_register_duplicate_username(self, auth, db):
        auth.register("bob", "secret123", "secret123", "Bob", 20, "b@b.com")
        with pytest.raises(ServiceError):
            auth.register("bob", "other123", "other123", "Bob2", 22, "b2@b.com")

    def test_login_success_and_failure(self, auth):
        auth.register("bob", "secret123", "secret123", "Bob", 20, "b@b.com")
        user = auth.login("bob", "secret123")
        assert user["username"] == "bob"
        with pytest.raises(ServiceError):
            auth.login("bob", "wrongpass")


class TestToolServiceRBAC:
    def test_non_admin_cannot_add(self, tools, regular_user):
        with pytest.raises(ServiceError):
            tools.add_tool("Hammer", "Tools", "Good", 5, "Shelf", actor=regular_user)

    def test_admin_can_add(self, tools, admin_user):
        assert tools.add_tool("Hammer", "Tools", "Good", 5, "Shelf", actor=admin_user)

    def test_non_admin_cannot_delete(self, tools, db, admin_user, regular_user):
        tools.add_tool("Hammer", "Tools", "Good", 5, "Shelf", actor=admin_user)
        tool_id = db.fetch_tool_by_name("Hammer")[0]["tool_id"]
        with pytest.raises(ServiceError):
            tools.delete_tool(tool_id, actor=regular_user)

    def test_duplicate_name_blocked(self, tools, admin_user):
        tools.add_tool("Hammer", "Tools", "Good", 5, "Shelf", actor=admin_user)
        with pytest.raises(ServiceError):
            tools.add_tool("Hammer", "Tools", "Good", 5, "Shelf", actor=admin_user)

    def test_invalid_condition_blocked(self, tools, admin_user):
        with pytest.raises(ServiceError):
            tools.add_tool("Hammer", "Tools", "Broken", 5, "Shelf", actor=admin_user)

    def test_negative_quantity_blocked(self, tools, admin_user):
        with pytest.raises(ServiceError):
            tools.add_tool("Hammer", "Tools", "Good", -3, "Shelf", actor=admin_user)

    def test_clear_inventory_admin_only(self, tools, db, admin_user, regular_user):
        tools.add_tool("Hammer", "Tools", "Good", 5, "Shelf", actor=admin_user)
        with pytest.raises(ServiceError):
            tools.clear_inventory(regular_user)
        assert tools.clear_inventory(admin_user)
        assert db.count_tools() == 0


class TestToolServiceBorrowReturn:
    def _seed(self, tools, admin_user):
        tools.add_tool("Hammer", "Tools", "Good", 5, "Shelf", actor=admin_user)
        return tools.search_tools("Hammer")[0]["tool_id"]

    def test_borrow_own_and_return(self, tools, admin_user, regular_user):
        tool_id = self._seed(tools, admin_user)
        tools.borrow_tool(tool_id, regular_user)
        assert len(tools.my_borrowed_tools(regular_user)) == 1
        tools.return_tool(tool_id, regular_user)
        assert tools.my_borrowed_tools(regular_user) == []

    def test_cannot_return_others_tool(self, tools, admin_user, regular_user):
        tool_id = self._seed(tools, admin_user)
        tools.borrow_tool(tool_id, regular_user)
        with pytest.raises(ServiceError):
            tools.return_tool(tool_id, 999)

    def test_cannot_borrow_twice(self, tools, admin_user, regular_user):
        tool_id = self._seed(tools, admin_user)
        tools.borrow_tool(tool_id, regular_user)
        with pytest.raises(ServiceError):
            tools.borrow_tool(tool_id, regular_user)

    def test_cannot_borrow_unavailable(self, tools, admin_user, regular_user):
        tools.add_tool("Broken", "Tools", "Good", 0, "Shelf", actor=admin_user)
        bad = tools.search_tools("Broken")[0]["tool_id"]
        with pytest.raises(ServiceError):
            tools.borrow_tool(bad, regular_user)
