# Project-TMS — Tool Management System

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](#license)
[![Tests](https://img.shields.io/badge/tests-43%20passing-brightgreen.svg)](#testing)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)](#installation)

A desktop **Tool Management System (TMS)** for schools, workshops, and small
organizations. Admins maintain the physical tool inventory; users borrow and
return items. Two interfaces — a **customtkinter GUI** (primary) and a **CLI**
(for scripted / admin use) — share a single business-logic and persistence
layer.

> Formerly published as *Project-LMS*. The system has always managed **tools**,
> not learners; the documentation and branding now reflect that.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Testing](#testing)
- [Security](#security)
- [Technology Stack](#technology-stack)
- [Contributors](#contributors)
- [License](#license)

---

## Overview

Project-TMS tracks physical tool inventory end-to-end: what exists, who holds
it, when it was borrowed, and what condition it is in. The system supports two
roles — **Admin** (full inventory control) and **Regular User** (view and
borrow) — and persists everything to a local SQLite database.

The codebase is deliberately split into three layers — **database → service →
presentation** — so business rules live in exactly one place and both the GUI
and the CLI can be maintained independently.

---

## Features

### Inventory
- Tool CRUD — add, update, delete, search by name or category
- Quantity tracking with atomic ownership transitions
- Borrow / return with a full transaction log
- Live keyword search plus category and status filters in the GUI
- Statistics dashboard — totals, availability, per-category donut chart

### Access & Security
- Role-based access control (Admin vs. Regular User)
- Password authentication with bcrypt hashing
- Per-username rate limiting (5 attempts / 10 minutes)
- Versioned, idempotent schema migrations on every startup

### Operations
- Offline-first — no network dependencies; SQLite at `db/inventory.db`
- Audit log — all writes stream to stdout and `logs/app.log` (1 MB × 3 rotation)
- Admin-only read-only SQL console in the CLI

---

## Architecture

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
│  ─ Parameterised SQL, schema, migrations                   │
│  ─ Atomic borrow/return (BEGIN IMMEDIATE + RETURNING)      │
│  ─ Rate-limited auth, bcrypt, audit log                    │
└────────────────────────────────────────────────────────────┘
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design rationale.

---

## Project Structure

```
Project-LMS/
├── project-lms.py        # Main GUI entry point
├── lms-cli.py            # CLI entry point
├── database.py           # DatabaseManager — persistence seam
├── service.py            # ToolService + AuthService — business rules
├── gui/
│   ├── __init__.py
│   ├── theme.py          # Color palette (single source of truth)
│   └── dialogs.py        # Borrow/Return/Add/Delete dialogs
├── tests/                # 43 tests (DB + service layers)
├── db/                   # SQLite (auto-created on first run)
├── assets/               # Optional background images + avatar
├── logs/                 # Rotating app.log (auto-created)
└── docs/                 # Project documentation
```

---

## Installation

### Prerequisites

- **Python 3.9+** (tested on 3.13)
- **SQLite ≥ 3.25** (borrow-history query uses `ROW_NUMBER() OVER`)
- Linux, macOS, or Windows

### Setup

```bash
git clone https://github.com/cediegreyhat/Project-LMS.git
cd Project-LMS

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Usage

### GUI (recommended)

```bash
python project-lms.py
```

On first launch the app seeds a default admin account (`admin` / `admin123`).
**Change this password immediately** — see [Security](#security).

### CLI

```bash
python lms-cli.py
```

The CLI mirrors the GUI operations and adds an admin-only read-only SQL
console.

---

## Testing

```bash
python -m pytest tests/ -q
```

43 tests pass, covering authentication, CRUD, borrow/return lifecycle,
pagination, search, RBAC, validation, and rate limiting. The GUI is
intentionally not under automated test (requires an X server); the service and
DB layers cover the behavior the GUI delegates to.

See [`docs/TESTING.md`](docs/TESTING.md).

---

## Security

- Default admin credentials are seeded on first run (`admin` / `admin123`).
  Change them before any non-demo use.
- Passwords are stored as bcrypt hashes; plaintext never touches disk.
- Login rate limiting: 5 failed attempts per username in a rolling 10-minute
  window.
- All queries are parameterised; the only f-string-built fragment is the
  column-name list in `update_tool`, sourced from a hard-coded `allowed` set.
- The CLI SQL console is admin-only and read-only, executed on a dedicated
  read-only SQLite connection (`mode=ro` + `PRAGMA query_only`).
- RBAC is enforced at both the service layer and the DB layer.

See [`docs/SECURITY.md`](docs/SECURITY.md).

---

## Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.9+ |
| GUI | `customtkinter`, `tkinter.ttk`, `Pillow` |
| Charts | `matplotlib` (donut chart of category counts) |
| Database | SQLite (WAL mode, `sqlite3.Row` factory) |
| Auth | `bcrypt` |
| Tests | `pytest` |
| CLI styling | `colorama` |

---

## Contributors

- **Lhord Cedrick T. Delos Santos** (Team Leader) — full-stack development, database integration, code review, GUI refactor
- **Luis Fernandez** — basic GUI development
- **Warren Dollendo** — basic GUI development
- **Dan Angelo Domagsang** — basic GUI development
- **Charles Benedict Rafols** — database development / debugging
- **Charles Allen Lacsa** — documentation
- **Brix Baldiray** — documentation
- **Dylan Guliquey** — testing and debugging
- **Joe Ckelvin Barboza** — documentation
- **Van Hallen Hayag** — documentation

---

## License

Released under the MIT License. See [`LICENSE`](LICENSE) for details.
