"""
Project-LMS Business Logic Layer
================================

Service classes sit BETWEEN the presentation layers (GUI/CLI) and the
DatabaseManager persistence seam. They own the business rules:

- input validation (lengths, numeric ranges, allowed enum values)
- role-based access control (admin gating)
- ownership checks (borrow/return authorization)
- consistent, user-facing error strings

Both the GUI and the CLI depend on this module so the rules live in exactly
one place. DatabaseManager stays a dumb persistence seam; these services are
the seam for business rules.
"""

import datetime

# Allowed enum for tool condition (kept single-source here).
VALID_CONDITIONS = ("Good", "Fair", "Poor")


class ServiceError(Exception):
    """A business-logic error with a message safe to show to the user."""


class ToolService:
    """Business rules for inventory, borrowing, and returning."""

    def __init__(self, db):
        self.db = db

    # -- Validation helpers ----------------------------------------------------
    @staticmethod
    def _validate_tool_inputs(name, category, condition, quantity, location):
        if not name or not name.strip():
            raise ServiceError("Tool name is required.")
        if not category or not category.strip():
            raise ServiceError("Category is required.")
        if not location or not location.strip():
            raise ServiceError("Location is required.")
        cond = (condition or "").strip().capitalize()
        if cond not in VALID_CONDITIONS:
            raise ServiceError(f"Condition must be one of: {', '.join(VALID_CONDITIONS)}.")
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise ServiceError("Quantity must be a whole number.")
        if quantity < 0:
            raise ServiceError("Quantity cannot be negative.")
        return name.strip(), category.strip(), cond, quantity, location.strip()

    # -- Inventory --------------------------------------------------------------
    def add_tool(self, name, category, condition, quantity, location, actor=None):
        """Add a new tool. Requires admin unless actor is None (seed/test)."""
        if actor is not None and not self.db.is_admin(actor):
            raise ServiceError("Only admins can add tools.")
        name, category, cond, qty, location = self._validate_tool_inputs(
            name, category, condition, quantity, location
        )
        # Duplicate name guard (case-insensitive).
        existing = self.db.fetch_tool_by_name(name)
        if existing:
            raise ServiceError("A tool with this name already exists.")
        return self.db.add_tool(name, category, cond, qty, location)

    def update_tool(self, tool_id, actor, **fields):
        """Update a tool's fields. Requires admin unless actor is None."""
        if actor is not None and not self.db.is_admin(actor):
            raise ServiceError("Only admins can update tools.")
        if not self.db.fetch_tool_by_id(tool_id):
            raise ServiceError("Tool not found.")
        return self.db.update_tool(tool_id, **fields)

    def delete_tool(self, tool_id, actor=None):
        """Delete a tool. Requires admin unless actor is None (seed/test)."""
        if actor is not None and not self.db.is_admin(actor):
            raise ServiceError("Only admins can delete tools.")
        return self.db.delete_tool(tool_id)

    def list_tools(self, page=1, page_size=20):
        return self.db.fetch_tools_paginated(page, page_size)

    def search_tools(self, keyword):
        keyword = (keyword or "").strip()
        if not keyword:
            raise ServiceError("Search keyword cannot be empty.")
        return self.db.search_tool(keyword)

    # -- Borrow / return ---------------------------------------------------------
    def borrow_tool(self, tool_id, user_id, borrow_date=None):
        """Borrow a tool for a user, with availability + idempotency checks."""
        tool = self.db.fetch_tool_by_id(tool_id)
        if not tool:
            raise ServiceError("Tool not found.")
        if tool["quantity"] <= 0 or tool["status"] != "available":
            raise ServiceError("Tool is unavailable or quantity is insufficient.")
        # A user cannot borrow the same tool they currently hold.
        held = [t["tool_id"] for t in self.db.fetch_borrowed_by_user(user_id)]
        if tool_id in held:
            raise ServiceError("You already hold this tool.")
        date = borrow_date or datetime.date.today().isoformat()
        if not self.db.borrow_tool(tool_id, user_id, "", date):
            raise ServiceError("Failed to borrow tool. It may have just become unavailable.")
        return True

    def return_tool(self, tool_id, user_id, return_date=None):
        """Return a tool only if the actor currently owns it (ownership check)."""
        held = [t["tool_id"] for t in self.db.fetch_borrowed_by_user(user_id)]
        if tool_id not in held:
            raise ServiceError("You can only return a tool you currently hold.")
        date = return_date or datetime.date.today().isoformat()
        if not self.db.return_tool(tool_id, user_id, date):
            raise ServiceError("Failed to return tool (already returned or not owned).")
        return True

    def my_borrowed_tools(self, user_id):
        return self.db.fetch_borrowed_by_user(user_id)

    def available_tools(self):
        return self.db.fetch_tools_by_status("available")

    # -- Admin --------------------------------------------------------------------
    def clear_inventory(self, actor):
        """Clear all tools and transactions. Admin-only."""
        if not self.db.is_admin(actor):
            raise ServiceError("Only admins can clear the inventory.")
        return self.db.clear_tables()


class AuthService:
    """Authentication and account business rules."""

    MIN_PASSWORD_LEN = 6
    MIN_USERNAME_LEN = 3

    def __init__(self, db):
        self.db = db

    def register(self, username, password, confirm, name, age, email):
        """Validate and create a new standard (non-admin) user."""
        username = (username or "").strip()
        name = (name or "").strip()
        email = (email or "").strip()
        if len(username) < self.MIN_USERNAME_LEN:
            raise ServiceError("Username must be at least 3 characters.")
        if not password or len(password) < self.MIN_PASSWORD_LEN:
            raise ServiceError("Password must be at least 6 characters.")
        if password != confirm:
            raise ServiceError("Passwords do not match.")
        if not name:
            raise ServiceError("Full name is required.")
        try:
            age = int(age)
        except (TypeError, ValueError):
            raise ServiceError("Age must be a number.")
        if not (10 <= age <= 120):
            raise ServiceError("Enter a valid age (10-120).")
        if "@" not in email or "." not in email:
            raise ServiceError("Enter a valid email address.")
        # Duplicate username check with a user-facing message.
        existing = self.db._execute_query(
            "SELECT id FROM users WHERE username = ?", (username,), fetch=True
        )
        if existing:
            raise ServiceError("Username already exists. Please choose another.")
        ok = self.db.insert_user(username, password, name, age, email, is_admin=0)
        if not ok:
            raise ServiceError("Signup failed. Try again.")
        return True

    def login(self, username, password):
        user = self.db.authenticate(username, password)
        if not user:
            raise ServiceError("Incorrect username or password.")
        return user
