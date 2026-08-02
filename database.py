"""
Project-LMS Data Access Layer
=============================

DatabaseManager exposes the persistence layer for the Learner's/Tool Management
System. It is the single seam every higher layer (GUI service, CLI) talks to.

Design notes:
- Parameterised queries everywhere: no user input is ever interpolated into SQL.
- One connection per manager instance, WAL mode enabled for concurrent reads.
- Logging goes to BOTH stdout and `logs/app.log` (rotating) for an audit trail.
- Passwords are stored as bcrypt hashes only; plaintext is never persisted.
- Role-based access: users table carries an `is_admin` flag.
"""

import datetime
import logging
import logging.handlers
import os
import sqlite3
from contextlib import closing

import bcrypt

# ---------------------------------------------------------------------------
# Logging setup (module-level, idempotent)
# ---------------------------------------------------------------------------
_LOGGER = logging.getLogger("project_lms")
if not _LOGGER.handlers:
    _LOGGER.setLevel(logging.INFO)
    _fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    stream = logging.StreamHandler()
    stream.setFormatter(_fmt)
    _LOGGER.addHandler(stream)

    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "app.log"), maxBytes=1_000_000, backupCount=3
    )
    file_handler.setFormatter(_fmt)
    _LOGGER.addHandler(file_handler)

logger = _LOGGER


class DatabaseManager:
    """Persistence seam for the Project-LMS application."""

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.connect()
        self.create_tables()
        self._migrate()

    # -- Connection management --------------------------------------------------
    def connect(self):
        """Establish or reconnect to the database with WAL mode and Row factory."""
        try:
            if not self.conn:
                self.conn = sqlite3.connect(self.db_path, timeout=10)
                self.conn.row_factory = sqlite3.Row
                self.conn.execute("PRAGMA foreign_keys = ON")
                self.conn.execute("PRAGMA journal_mode = WAL")
                logger.info("Connected to database: %s", self.db_path)
        except sqlite3.Error as e:
            logger.error("Failed to connect to database: %s", e)
            raise

    def ensure_connection_open(self):
        """Make sure the connection is still usable, reconnecting if needed."""
        if self.conn is None:
            self.connect()
        try:
            self.conn.execute("SELECT 1")
        except sqlite3.ProgrammingError:
            logger.warning("Connection lost, reconnecting...")
            self.connect()

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed.")

    # -- Schema -----------------------------------------------------------------
    def create_tables(self):
        """Create necessary tables and indexes if they don't exist."""
        table_queries = [
            """CREATE TABLE IF NOT EXISTS tools (
                tool_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                condition TEXT DEFAULT 'Good',
                quantity INTEGER NOT NULL,
                location TEXT,
                status TEXT DEFAULT 'available',
                borrower TEXT,
                borrow_date TEXT,
                user_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );""",
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                name TEXT,
                age INTEGER,
                email TEXT,
                is_admin INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );""",
            """CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_id INTEGER,
                user_id INTEGER,
                transaction_type TEXT NOT NULL,
                transaction_date TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tool_id) REFERENCES tools(tool_id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );""",
            """CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                attempted_at TEXT DEFAULT CURRENT_TIMESTAMP
            );""",
        ]
        index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(name)",
            "CREATE INDEX IF NOT EXISTS idx_tools_category ON tools(category)",
            "CREATE INDEX IF NOT EXISTS idx_tools_status ON tools(status)",
            "CREATE INDEX IF NOT EXISTS idx_tools_condition ON tools(condition)",
            "CREATE INDEX IF NOT EXISTS idx_tx_tool ON transactions(tool_id)",
            "CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id)",
        ]
        try:
            with closing(self.conn.cursor()) as cursor:
                for query in table_queries + index_queries:
                    cursor.execute(query)
                self.conn.commit()
                logger.info("Tables and indexes verified.")
        except sqlite3.Error as e:
            logger.error("Failed to create tables or indexes: %s", e)
            raise

    def _migrate(self):
        """Add any missing columns to an existing database schema."""
        try:
            cols = [
                c[1] for c in self.conn.execute("PRAGMA table_info(users)").fetchall()
            ]
            if "is_admin" not in cols:
                self.conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
                self.conn.commit()
                logger.info("Migrated users table: added is_admin column.")
            if "created_at" not in cols:
                self.conn.execute("ALTER TABLE users ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
                self.conn.commit()
                logger.info("Migrated users table: added created_at column.")
        except sqlite3.Error as e:
            logger.error("Migration failed: %s", e)

    # -- Generic query helper ----------------------------------------------------
    def _execute_query(self, query, params=None, fetch=False):
        """Execute a parameterised query. `fetch=True` returns a list of dicts."""
        try:
            with closing(self.conn.cursor()) as cursor:
                cursor.execute(query, params or [])
                if fetch:
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
                self.conn.commit()
                return True
        except sqlite3.IntegrityError as e:
            logger.error("Integrity error in query: %s -- %s", query, e)
            raise
        except Exception as e:
            logger.error("Error executing query: %s -- %s", query, e)
            raise

    # -- Role-based access control ------------------------------------------------
    def is_admin(self, user_id):
        """Return True if the given user id is an admin."""
        if user_id is None:
            return False
        rows = self._execute_query(
            "SELECT is_admin FROM users WHERE id = ?", (user_id,), fetch=True
        )
        if not rows:
            return False
        return bool(rows[0].get("is_admin"))

    def set_admin(self, user_id, is_admin=True):
        """Promote/demote a user to/from admin. Returns True on success."""
        try:
            self._execute_query(
                "UPDATE users SET is_admin = ? WHERE id = ?",
                (1 if is_admin else 0, user_id),
            )
            logger.info("User %s admin flag set to %s", user_id, is_admin)
            return True
        except Exception as e:
            logger.error("Failed to set admin flag: %s", e)
            return False

    # -- Authentication -----------------------------------------------------------
    LOGIN_ATTEMPT_WINDOW_MINUTES = 10
    MAX_LOGIN_ATTEMPTS = 5

    def _too_many_attempts(self, username):
        """Rate-limit check: block login after too many failed attempts.

        Timestamps are stored/compared in ISO 8601 format so string comparison
        is chronologically correct.
        """
        cutoff = (
            datetime.datetime.now() - datetime.timedelta(minutes=self.LOGIN_ATTEMPT_WINDOW_MINUTES)
        ).isoformat()
        rows = self._execute_query(
            """SELECT COUNT(*) AS c FROM login_attempts
               WHERE username = ? AND attempted_at > ?""",
            (username, cutoff),
            fetch=True,
        )
        return (rows[0]["c"] if rows else 0) >= self.MAX_LOGIN_ATTEMPTS

    def _record_attempt(self, username):
        self._execute_query(
            "INSERT INTO login_attempts (username, attempted_at) VALUES (?, ?)",
            (username, datetime.datetime.now().isoformat()),
        )

    def insert_user(self, username, password, name, age, email, is_admin=0):
        """Register a new user with a bcrypt-hashed password."""
        try:
            hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
            self._execute_query(
                "INSERT INTO users (username, password, name, age, email, is_admin) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (username, hashed_pw, name, age, email, 1 if is_admin else 0),
            )
            logger.info("Inserted user: %s", username)
            return True
        except sqlite3.IntegrityError as e:
            logger.error("Error inserting user (likely duplicate): %s", e)
            return False
        except Exception as e:
            logger.error("Error inserting user: %s", e)
            return False

    def authenticate(self, username, password):
        """Verify credentials against the bcrypt hash. Returns user dict or None.

        Rate limiting applies here.
        """
        if self._too_many_attempts(username):
            logger.warning("Login rate-limited for username %s", username)
            return None
        user_rows = self._execute_query(
            "SELECT * FROM users WHERE username = ?", (username,), fetch=True
        )
        if not user_rows:
            self._record_attempt(username)
            return None
        user = user_rows[0]
        stored_hash = user["password"]
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode("utf-8")
        try:
            if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
                return user
        except ValueError as e:
            logger.error("Invalid hash format for user %s: %s", username, e)
        self._record_attempt(username)
        return None

    # -- Tool CRUD --------------------------------------------------------------
    def insert_tool(self, name, category, condition, quantity, location):
        """Insert a new tool. Returns True on success."""
        try:
            self._execute_query(
                "INSERT INTO tools (name, category, condition, quantity, location, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (name, category, condition, quantity, location, "available"),
            )
            logger.info("Inserted tool: %s", name)
            return True
        except Exception as e:
            logger.error("Error inserting tool: %s", e)
            return False

    # Alias so the CLI's `add_tool` call and any external callers work uniformly.
    def add_tool(self, name, category, condition, quantity, location):
        return self.insert_tool(name, category, condition, quantity, location)

    def update_tool(self, tool_id, **fields):
        """Update any subset of tool fields for a given tool_id.

        Accepts name/category/condition/quantity/location. Only the keys passed
        are updated. Returns True on success, False if the tool doesn't exist.
        """
        allowed = {"name", "category", "condition", "quantity", "location"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return False
        assignments = ", ".join(f"{col} = ?" for col in updates)
        params = list(updates.values()) + [tool_id]
        query = f"UPDATE tools SET {assignments} WHERE tool_id = ?"
        try:
            self.ensure_connection_open()
            with closing(self.conn.cursor()) as cursor:
                cursor.execute(query, params)
                if cursor.rowcount == 0:
                    logger.warning("Update: tool %s not found", tool_id)
                    return False
                self.conn.commit()
                logger.info("Updated tool %s fields: %s", tool_id, list(updates))
                return True
        except Exception as e:
            logger.error("Error updating tool %s: %s", tool_id, e)
            self.conn.rollback()
            return False

    def delete_tool(self, tool_id):
        """Delete a tool by id. Returns True on success."""
        self.ensure_connection_open()
        try:
            with closing(self.conn.cursor()) as cursor:
                cursor.execute("DELETE FROM tools WHERE tool_id = ?", (tool_id,))
                if cursor.rowcount == 0:
                    raise ValueError(f"Tool with ID {tool_id} does not exist.")
                # Also purge related transactions to keep referential integrity.
                cursor.execute(
                    "DELETE FROM transactions WHERE tool_id = ?", (tool_id,)
                )
                self.conn.commit()
                logger.info("Tool %s deleted (and its transactions purged).", tool_id)
                return True
        except Exception as e:
            logger.error("Error deleting tool %s: %s", tool_id, e)
            self.conn.rollback()
            return False

    def clear_tables(self):
        """Clear tools and transactions tables (admin-only operation enforced upstream)."""
        self.ensure_connection_open()
        try:
            with closing(self.conn.cursor()) as cursor:
                cursor.execute("DELETE FROM transactions")
                cursor.execute("DELETE FROM tools")
                self.conn.commit()
                logger.info("Cleared tools and transactions tables.")
                return True
        except Exception as e:
            logger.error("Error clearing tables: %s", e)
            self.conn.rollback()
            return False

    # -- Inventory queries --------------------------------------------------------
    def fetch_all_tools(self):
        return self._execute_query("SELECT * FROM tools", fetch=True)

    def fetch_tool_by_name(self, name):
        return self._execute_query("SELECT * FROM tools WHERE name = ?", (name,), fetch=True)

    def fetch_tool_by_id(self, tool_id):
        rows = self._execute_query(
            "SELECT * FROM tools WHERE tool_id = ?", (tool_id,), fetch=True
        )
        return rows[0] if rows else None

    def fetch_tools_by_status(self, status, user_id=None):
        query = "SELECT tool_id, name, status, quantity FROM tools WHERE status = ?"
        params = [status]
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        return self._execute_query(query, tuple(params), fetch=True)

    def search_tool(self, keyword):
        """Case-insensitive partial search on name or category."""
        query = """
            SELECT * FROM tools
            WHERE name LIKE ? OR category LIKE ?
            ORDER BY tool_id DESC
            LIMIT 50
        """
        param = f"%{keyword}%"
        return self._execute_query(query, (param, param), fetch=True)

    def fetch_tools_paginated(self, page=1, page_size=20):
        offset = (page - 1) * page_size
        query = "SELECT * FROM tools LIMIT ? OFFSET ?"
        return self._execute_query(query, (page_size, offset), fetch=True)

    def count_tools(self):
        rows = self._execute_query("SELECT COUNT(*) AS count FROM tools", fetch=True)
        return rows[0]["count"] if rows else 0

    # -- Borrow / return -----------------------------------------------------------
    def borrow_tool(self, tool_id, user_id, borrower_name, borrow_date):
        """Atomically decrement quantity, mark the borrower, and log a transaction."""
        self.ensure_connection_open()
        try:
            with closing(self.conn.cursor()) as cursor:
                tool_update = """
                    UPDATE tools SET
                        quantity = quantity - 1,
                        status = CASE WHEN quantity - 1 <= 0 THEN 'unavailable' ELSE 'available' END,
                        user_id = ?, borrower = ?, borrow_date = ?
                    WHERE tool_id = ? AND quantity > 0
                """
                cursor.execute(tool_update, (user_id, borrower_name, borrow_date, tool_id))
                if cursor.rowcount == 0:
                    raise ValueError("Tool is unavailable or quantity is insufficient.")
                cursor.execute(
                    "INSERT INTO transactions (tool_id, user_id, transaction_type, transaction_date) "
                    "VALUES (?, ?, 'borrow', ?)",
                    (tool_id, user_id, borrow_date),
                )
                self.conn.commit()
                logger.info("Tool %s borrowed by user %s", tool_id, user_id)
                return True
        except Exception as e:
            logger.error("Error in borrow_tool: %s", e)
            self.conn.rollback()
            return False

    def return_tool(self, tool_id, user_id, return_date):
        """Return a tool, only if the given user currently owns it (ownership check).

        Returns True on success, False if not the owner / already returned.
        """
        self.ensure_connection_open()
        try:
            with closing(self.conn.cursor()) as cursor:
                # Ownership check: the tool must be currently borrowed by this user.
                owned_rows = cursor.execute(
                    "SELECT 1 FROM tools WHERE tool_id = ? AND user_id = ? "
                    "AND borrower IS NOT NULL",
                    (tool_id, user_id),
                ).fetchone()
                if not owned_rows:
                    logger.warning(
                        "Return DENIED: user %s does not own tool %s", user_id, tool_id
                    )
                    return False
                cursor.execute(
                    "UPDATE tools SET status='available', borrower=NULL, borrow_date=NULL, user_id=NULL "
                    "WHERE tool_id = ?",
                    (tool_id,),
                )
                cursor.execute(
                    "INSERT INTO transactions (tool_id, user_id, transaction_type, transaction_date) "
                    "VALUES (?, ?, 'return', ?)",
                    (tool_id, user_id, return_date),
                )
                self.conn.commit()
                logger.info("Tool %s returned by user %s", tool_id, user_id)
                return True
        except Exception as e:
            logger.error("Error in return_tool: %s", e)
            self.conn.rollback()
            return False

    def fetch_borrowed_by_user(self, user_id):
        """Tools currently borrowed by a user (ownership-scoped).

        Uses the tools.borrower/user_id columns (the single source of truth for
        current ownership) rather than status, which may remain 'available'
        for tools with quantity > 1.
        """
        return self._execute_query(
            """SELECT result.* FROM (
                  SELECT t.tool_id, t.name, t.status, t.borrow_date
                  FROM tools t
                  JOIN transactions tr ON t.tool_id = tr.tool_id
                  WHERE tr.user_id = ? AND tr.transaction_type = 'borrow'
                  GROUP BY t.tool_id
               ) result
               WHERE result.tool_id IN (
                   SELECT tool_id FROM tools WHERE borrower IS NOT NULL AND user_id = ?
               )""",
            (user_id, user_id),
            fetch=True,
        )

    # -- Misc ---------------------------------------------------------------------
    def check_and_add_default_data(self):
        """Idempotent seed: create an admin account if none exists."""
        try:
            admins = self._execute_query(
                "SELECT COUNT(*) AS c FROM users WHERE is_admin = 1", fetch=True
            )
            if admins[0]["c"] == 0:
                self.insert_user(
                    "admin", "admin123", "Administrator", 30, "admin@lms.local", is_admin=1
                )
                logger.info("Seeded default admin account (username='admin').")
        except Exception as e:
            logger.error("Failed to seed default data: %s", e)


if __name__ == "__main__":
    inventory_db = DatabaseManager("db/inventory.db")
    inventory_db.check_and_add_default_data()
    tools = inventory_db.fetch_all_tools()
    logger.info("Tools fetched: %s", tools)
    inventory_db.close()
