# **Project-LMS — Learner's Management System**

A desktop tool-inventory system for schools and small workshops. Admins add and
maintain tools; users borrow and return them. Two interfaces share a single
business-logic and persistence layer: a **customtkinter GUI** (primary) and a
**CLI** (for scripted/admin use).

---

## **Table of Contents**
- [Introduction](#introduction)
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation and Usage](#installation-and-usage)
- [Architecture](#architecture)
- [Testing](#testing)
- [Security Notes](#security-notes)
- [Technology Stack](#technology-stack)
- [Contributors](#contributors)

---

## **Introduction**

Project-LMS is a 2nd-year Computer Engineering final-assessment project that
tracks physical tool inventory: who has what, when it was borrowed, and what
condition it is in. The system supports two roles — **Admin** (full inventory
control) and **Regular User** (view and borrow) — and persists everything to a
local SQLite database.

The codebase is intentionally structured into three layers (database → service
→ presentation) so business rules live in exactly one place and both the GUI
and the CLI can be maintained independently.

---

## **Features**

### Functional
- **Role-based access control** — admins manage inventory, regular users borrow/return.
- **Tool CRUD** — add, update, delete, and search tools by name or category.
- **Borrow / return** with quantity tracking, atomic ownership transitions, and a
  full transaction log.
- **Search + filter** — live keyword search plus category and status filters in
  the GUI; numeric `SELECT`/`PRAGMA`/`EXPLAIN`/`WITH` console in the CLI.
- **Statistics dashboard** — total / available / borrowed / categories counts,
  per-refresh deltas, category donut chart.
- **Password authentication** with bcrypt hashing and per-username rate limiting
  (5 attempts per 10 minutes).
- **Schema migrations** — versioned, idempotent, runs on every startup.

### Non-Functional
- **Offline-first** — no network dependencies; SQLite file at `db/inventory.db`.
- **Audit log** — all writes stream to stdout *and* `logs/app.log` (1 MB × 3 rotation).

---

## **Project Structure**

```plaintext
Project-LMS/
├── project-lms.py        # Main GUI entry point (LoginApp + ToolManagementApp)
├── lms-cli.py            # CLI entry point (banner + menu)
├── database.py           # DatabaseManager — persistence seam, schema, migrations
├── service.py            # ToolService + AuthService — business rules, validation, RBAC
├── gui/
│   ├── __init__.py
│   ├── theme.py          # Color palette constants (single source of truth)
│   └── dialogs.py        # BorrowDialog, ReturnDialog, AddToolDialog, DeleteToolDialog,
│                         # AdvancedToolTip (shared `_BaseDialog` base)
├── tests/
│   ├── conftest.py       # Fixtures: db, auth, tools, admin_user, regular_user
│   ├── test_database.py  # DB-layer tests (auth, CRUD, borrow/return, rate limiting)
│   └── test_service.py   # Service-layer tests (RBAC, validation, ownership)
├── db/
│   └── inventory.db      # SQLite (auto-created on first run)
├── assets/               # Optional background images + avatar
└── logs/                 # Rotating app.log (auto-created)
```

---

## **Installation and Usage**

### Prerequisites
- **Python 3.9+** (matches `pyproject.toml` `requires-python`; tested on 3.13)
- **SQLite ≥ 3.25** (the borrow-history query uses `ROW_NUMBER() OVER`)
- Linux, macOS, or Windows

### Setup
```bash
git clone https://github.com/cediegreyhat/Project-LMS.git
cd Project-LMS

# PEP 668 friendly — use a venv:
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Running

**GUI (recommended):**
```bash
python project-lms.py
```
On first launch the app seeds a default admin account (`admin` / `admin123`).
**Change this password immediately** — see [Security Notes](#security-notes).

**CLI:**
```bash
python lms-cli.py
```
The CLI menu mirrors the GUI operations and adds an admin-only read-only SQL
console.

---

## **Architecture**

Project-LMS follows a strict three-layer split:

```
┌────────────────────────────────────────────────────────────┐
│  Presentation  (project-lms.py, lms-cli.py)                │
│  ─ GUI shell + dashboard, dialogs, sidebar, footer         │
│  ─ CLI banner, menu, table printer                         │
└──────────────────────┬─────────────────────────────────────┘
                       │  ToolService / AuthService (service.py)
                       │  ─ Validation, RBAC, ownership checks
                       │  ─ Translates DB errors → ServiceError
                       ▼
┌────────────────────────────────────────────────────────────┐
│  Persistence  (database.py / DatabaseManager)              │
│  ─ SQL (parameterised everywhere), schema, migrations      │
│  ─ Atomic borrow/return with BEGIN IMMEDIATE + RETURNING   │
│  ─ Rate-limited auth, bcrypt, audit log                    │
└────────────────────────────────────────────────────────────┘
```

**Why three layers?** GUI and CLI both delegate business rules to the service
layer. A change to "what counts as available" is a one-file edit, not a
two-interface search-and-replace.

### Key contracts

| Layer | Entry point | Returns |
|---|---|---|
| Service | `ToolService.borrow_tool(tool_id, user_id)` | `True` or raises `ServiceError` |
| Service | `ToolService.add_tool(name, cat, cond, qty, loc, actor)` | `True` or raises `ServiceError` |
| DB | `DatabaseManager.borrow_tool(...)` | `True` / `False` (never raises `ServiceError`) |
| GUI dialogs | `BorrowDialog(parent, tools, user_id, on_success)` | side effect + `on_success()` callback |

---

## **Testing**

```bash
python -m pytest tests/ -q
```

Currently **43 tests pass**, covering:

- **Database layer** — auth round-trip, duplicate-user rejection, partial
  updates, deletion of ever-borrowed tools (child rows purged before parent),
  multi-quantity borrow/return status transitions, pagination,
  case-insensitive search, login rate limiting (including unknown usernames),
  ownership-checked borrow/return.
- **Service layer** — RBAC matrix (admin vs non-admin × add/update/delete/clear),
  input validation (condition enum, quantity sign, duplicate name, bad email,
  bad age), borrow-then-twice, return-others-tool.

The GUI is intentionally not under automated test in this assessment — it
requires an X server and a running tk event loop. The service and DB layers
cover the behavior the GUI delegates to.

---

## **Security Notes**

- **Default admin credentials are seeded on first run** (`admin` /
  `admin123`) if no admin exists in the database. **Change this password in
  production**; the seed is a convenience for classroom demos, not a security
  feature. The CLI prints no warning — operators should know to delete the
  default account after first login.
- **Passwords** are stored as bcrypt hashes (`bcrypt.gensalt()`, default cost).
  Plaintext never touches disk.
- **Login rate limiting** — 5 failed attempts per username in a rolling
  10-minute window. Even correct credentials are rejected while the window is
  active. Successful login drains the attempt log for that user.
- **SQL injection** — all queries are parameterised; the only f-string-built
  fragment is the column-name list in `update_tool`, and the column names come
  from a hard-coded `allowed` set in the DB layer (defense-in-depth on top of
  service-layer RBAC).
- **CLI SQL console** is admin-only and read-only — statements must start
  with `SELECT`, `PRAGMA`, `EXPLAIN`, or `WITH`, and execution happens on a
  dedicated read-only SQLite connection (`mode=ro` + `PRAGMA query_only`),
  so destructive statements fail at the engine level instead of relying on
  keyword filtering.
- **RBAC** is enforced at both the service layer (where business rules live)
  *and* the DB layer (`clear_tables` re-checks `is_admin`; its actor argument
  is mandatory so omitting it can never skip the check), so a caller that
  bypasses the service still hits the gate.

---

## **Technology Stack**

- **Language:** Python 3.9+
- **GUI:** `customtkinter`, `tkinter.ttk` (Treeview), `PIL` (background images, avatar)
- **Charts:** `matplotlib` (Figure + FigureCanvasTkAgg, donut chart of category counts)
- **Database:** SQLite (WAL mode, `sqlite3.Row` factory)
- **Auth:** `bcrypt` for password hashing
- **Tests:** `pytest`
- **CLI styling:** `colorama`

---

## **Contributors**

- **Lhord Cedrick T. Delos Santos** (Team Leader): full-stack development, database integration, code review, GUI refactor
- **Luis Fernandez**: basic GUI development
- **Warren Dollendo**: basic GUI development
- **Dan Angelo Domagsang**: basic GUI development
- **Charles Benedict Rafols**: database development / debugging
- **Charles Allen Lacsa**: documentation
- **Brix Baldiray**: documentation
- **Dylan Guliquey**: testing and debugging
- **Joe Ckelvin Barboza**: documentation
- **Van Hallen Hayag**: documentation

Feel free to contribute or raise issues in the repository. 🚀
