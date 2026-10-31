# User Guide

Project-TMS is a desktop Tool Management System with two interfaces: a
customtkinter GUI (primary) and a CLI (scripted / admin use).

## Roles

- **Admin** — full inventory control: add, update, delete, clear, borrow, return.
- **Regular User** — view and borrow/return tools they hold.

## First Run

1. Launch the GUI: `python project-lms.py`
2. A default admin is seeded: username `admin`, password `admin123`.
3. **Change this password immediately** (Security section).
4. Register regular users via the Sign Up screen.

## GUI Workflows

### Admin
- **Add tool** — name, category, condition (Good/Fair/Poor), quantity, location.
- **Update tool** — edit fields on an existing row.
- **Delete tool** — removes tool (ever-borrowed tools purge child rows first).
- **Clear inventory** — admin-only, removes all tools and transactions.
- **Search / filter** — live keyword search plus category and status filters.
- **Dashboard** — totals, available, borrowed, category donut chart.

### Regular User
- **Browse** available tools.
- **Borrow** a tool (quantity > 0 and unheld).
- **Return** a tool you currently hold.
- **My borrowed tools** view.

## CLI Workflows

Launch: `python lms-cli.py`. Menu mirrors GUI operations and adds:
- **Admin-only read-only SQL console** — statements must start with `SELECT`,
  `PRAGMA`, `EXPLAIN`, or `WITH`; executed on a read-only connection.

## Data Location

- Database: `db/inventory.db` (auto-created on first run).
- Logs: `logs/app.log` (rotating, 1 MB × 3).
- Assets: `assets/` (optional background images / avatar).

## Tips

- Keep quantities accurate; borrow requires stock > 0 and no current holder.
- A user cannot borrow the same tool twice while holding it.
- Successful login clears the failed-attempt log for that user.
