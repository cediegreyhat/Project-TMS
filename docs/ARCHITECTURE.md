# Architecture

Project-TMS follows a strict three-layer split so business rules live in exactly
one place and both the GUI and the CLI can be maintained independently.

## Layers

### 1. Persistence — `database.py` (`DatabaseManager`)
- Single seam to SQLite. One connection per manager instance, WAL mode, foreign
  keys enabled, `sqlite3.Row` factory.
- Schema creation (`create_tables`) + versioned, idempotent migrations
  (`_migrate`).
- Parameterised queries everywhere. The only f-string-built fragment is the
  column-name list in `update_tool`, sourced from a hard-coded `allowed` set.
- Atomic borrow/return using `BEGIN IMMEDIATE` + `RETURNING`.
- Audit logging to stdout **and** `logs/app.log` (rotating, 1 MB × 3).
- Auth: bcrypt hashing, per-username rate limiting, lockout windows.

### 2. Service — `service.py` (`ToolService`, `AuthService`)
- Input validation (lengths, numeric ranges, allowed enum values).
- Role-based access control (admin gating).
- Ownership checks for borrow/return.
- Consistent, user-facing error strings via `ServiceError`.
- Translates DB-layer errors into `ServiceError` so presentation code never
  leaks raw SQLite messages.

### 3. Presentation — `project-lms.py` (GUI), `lms-cli.py` (CLI)
- GUI: `LoginApp` + `ToolManagementApp` shell, sidebar, dashboard, dialogs.
- CLI: banner + menu, table printer, admin-only read-only SQL console.
- Both delegate all business rules to the service layer.

## Data Flow

```
User action (GUI/CLI)
   → Service (validate, RBAC, ownership)
      → DatabaseManager (parameterised SQL, transaction)
         → SQLite (db/inventory.db)
      ← rows / bool
   ← ServiceError on failure, value on success
← UI feedback
```

## Schema (summary)

- `tools` — `tool_id`, `name`, `category`, `condition`, `quantity`, `location`,
  `status`, `borrower`, `borrow_date`, `user_id` (FK → users.id)
- `users` — `id`, `username` (UNIQUE), `password` (bcrypt hash), `name`, `age`,
  `email`, `is_admin`, `created_at`
- `transactions` — `transaction_id`, `tool_id`, `user_id`, `transaction_type`,
  `quantity`, `date`, `notes`

Indexes are created in `create_tables`; migrations are additive and idempotent.

## Key Contracts

| Layer | Entry point | Returns |
|---|---|---|
| Service | `ToolService.borrow_tool(tool_id, user_id)` | `True` or raises `ServiceError` |
| Service | `ToolService.add_tool(name, cat, cond, qty, loc, actor)` | `True` or raises `ServiceError` |
| Service | `ToolService.update_tool(tool_id, actor, **fields)` | `True` or raises `ServiceError` |
| DB | `DatabaseManager.borrow_tool(...)` | `True` / `False` (never raises `ServiceError`) |
| DB | `DatabaseManager.clear_tables(actor)` | requires admin; defense-in-depth gate |

## Why three layers?

GUI and CLI both delegate business rules to the service layer. A change to
"what counts as available" is a one-file edit in `service.py`, not a
two-interface search-and-replace.
