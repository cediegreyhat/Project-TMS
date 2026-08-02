# FEATURE_INTEGRATION_PLAN.md
## Project-LMS — Researched Feature Roadmap

> Generated 2026-08-02.
> Sources: Wikipedia *Inventory management software* (functions: reorder
> point, product identification/tracking, barcode/RFID), Wikipedia
> *Integrated library system* (circulation, overdue notices, reservations,
> renewal, patron/item IDs) — cross-referenced against the current codebase.
>
> Stack: Python 3.13, customtkinter 5.2.2, SQLite, bcrypt, matplotlib,
> Pillow. Business logic in `service.py`, persistence in `database.py`,
> GUI in `project-lms.py`, CLI in `lms-cli.py`, pytest suite in `tests/`.

---

## Where the app stands today (baseline)

- Auth: bcrypt + RBAC (admin/user), rate-limited login, seeded default admin.
- Tool CRUD, borrow/return with ownership verification.
- Search/filter, category donut chart, modern single-window GUI.
- Service layer (`ToolService`/`AuthService`) + persistence seam + pytest suite.

---

## The taxonomy

Industry-standard inventory & loan systems converge on a small set of
capabilities. The app already covers the **core circulation** slice.
The roadmap below adds the next highest-value layers, ranked by
effort/value and grounded in the reference taxonomy.

---

## Priority 1 (HIGH value, LOW-MEDIUM effort) — recommended first

### 1. Due-date + overdue tracking & dashboard banner
**What:** When borrowing, record an expected return date (e.g. +7 days).
Dashboard highlights overdue items (red) and shows days overdue; a
sidebar/card shows "2 overdue items."
**Stack:** add `due_date` column (migration in `_migrate`), derive
`is_overdue` in `ToolService`, surface in GUI table + stat card.
**Effort:** Small. **Why:** The single most requested feature in loan
systems ("overdue notices" is a core ILS circulation task — src: ILS).

### 2. CSV / Excel report export
**What:** Admin exports current inventory and/or full transaction history
to CSV (stdlib `csv`) or `.xlsx` (add `openpyxl`). Include a report-viewer
window; add an "Export" button in the GUI sidebar and a `--export` flag in
the CLI.
**Stack:** `ToolService.export_inventory(path, fmt)` + `export_transactions`.
**Effort:** Small. **Why:** Reporting is a baseline inventory function
(src: IMS functions); cheap, high utility for a coursework deliverable.

### 3. Low-stock / reorder-point alerts
**What:** Each tool gets a `reorder_level`. When `quantity <= reorder_level`,
flag it "LOW STOCK" (yellow) in the table and count on a stat card.
**Stack:** add `reorder_level` column; migration; `ToolService.low_stock()`.
**Effort:** Small. **Why:** "Reorder point" is a named IMS function — this
is the textbook inventory feature.

---

## Priority 2 (MEDIUM value, MEDIUM effort)

### 4. Audit / activity log viewer
**What:** A read-only view of the `transactions` table (borrow/return events)
with filters by user/date. Admin-only. (Table already exists and is
populated.)
**Stack:** `ToolService.transaction_history(user_id=None)`; GUI viewer
window; CLI `history` command.
**Effort:** Small-Medium (the data is already there). **Why:** Traceability
— "circulation control" and monitoring (src: ILS); great for the report
write-up.

### 5. Tool photos / attachments
**What:** Attach an image to a tool (Pillow is installed). Thumbnail shown
in the table tooltip or a detail pane. Pick via file dialog;
store the path or copy into `assets/tools/`.
**Stack:** `tool_image` column (path) + GUI file picker + thumbnail render.
**Effort:** Medium. **Why:** "Product identification" (src: IMS) — makes
the app feel production-grade and aids recognition.

### 6. Reservations / waitlist for borrowed tools
**What:** If a tool is unavailable, a user can place a reservation; when it
is returned, the reserved user gets priority. New `reservations` table.
**Stack:** schema + `ToolService.reserve/claim`; small GUI dialog.
**Effort:** Medium. **Why:** "Reservation of titles" is a named ILS feature —
differentiates the project and is a fun demo.

### 7. Password change / account settings
**What:** Logged-in user can change their own password (verify old, set new,
bcrypt rehash). Admin can reset other users' passwords or promote users.
**Stack:** `AuthService.change_password`, `AuthService.admin_set_role`; GUI
settings dialog.
**Effort:** Medium. **Why:** Closes an obvious auth gap; strengthens the
security story already present.

---

## Priority 3 (NICE-TO-HAVE / LARGER)

### 8. QR / barcode generation & printing
**What:** Generate a per-tool QR code (lib `qrcode`) embedding the tool id,
preview in GUI, print/label at add-time. Barcode *scanning* would need a
scanner lib/camera — mark as stretch.
**Stack:** add `qrcode` + `pypng`; `ToolService.qr_for_tool(id)`.
**Effort:** Medium-Large (library + camera/scanning integration is the hard
part). **Why:** "Barcode" is the canonical IMS identification method
(src: IMS), and it's already in the README roadmap.

### 9. Database backup / restore
**What:** Buttons to snapshot the SQLite file (copy with timestamp to
`backups/`) and restore from a chosen backup. Admin-only.
**Stack:** `ToolService.backup()`, `restore()`; small dialogs. WAL mode means
backup via `sqlite3` online backup API is the correct approach.
**Effort:** Small-Medium. **Why:** Data safety; trivial given SQLite.

### 10. Statistics / analytics panel
**What:** Extend the single donut chart into a small analytics view: most
borrowed tools, borrows-per-category bar chart, borrows over time line.
**Stack:** matplotlib (already used) + new queries in `database.py`.
**Effort:** Medium. **Why:** Turns the pie into a story; impressive for the
report; reuses the charting already in place.

---

## Suggested sequencing

1. **Sprint A (P1):** Overdue tracking (#1) → CSV export (#2) → low-stock
   alerts (#3). All additive, low-risk, high demo value.
2. **Sprint B (P2):** Activity log (#4) → tool photos (#5) → settings/password
   (#7).
3. **Sprint C (P2/P3):** Reservations (#6) → backup/restore (#9) → analytics (#10).
4. **Later / stretch:** QR/barcode (#8) — biggest technical lift.

Each item is independent → can be shipped as its own commit with pytest
coverage added before the GUI/CLI wiring (TDD-friendly, matches the
existing `tests/` structure).

---

## Notes & risks

- All P1 items need only additive schema migrations (safe — `_migrate`
  already handles `ALTER TABLE ... ADD COLUMN`).
- Python 3.13 + GCC: `qrcode`/`openpyxl` are pure or wheeled — no build pain.
- Keep every new read/write behind `ToolService`/`AuthService` so RBAC and
  validation stay consistent with the current design.
- Do not fetch anything new from the web at runtime (offline-first design).
