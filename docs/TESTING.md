# Testing

## Running

```bash
python -m pytest tests/ -q
```

Expected: **43 tests pass**.

## Coverage

- **Database layer** (`tests/test_database.py`): auth round-trip, duplicate-user
  rejection, partial updates, deletion of ever-borrowed tools (child rows
  purged before parent), multi-quantity borrow/return status transitions,
  pagination, case-insensitive search, login rate limiting (including unknown
  usernames), ownership-checked borrow/return.
- **Service layer** (`tests/test_service.py`): RBAC matrix (admin vs non-admin ×
  add/update/delete/clear), input validation (condition enum, quantity sign,
  duplicate name, bad email, bad age), borrow-then-twice, return-others-tool.

## Fixtures

`tests/conftest.py` provides: `db`, `auth`, `tools`, `admin_user`,
`regular_user`.

## GUI Testing

The GUI is intentionally not under automated test — it requires an X server and
a running tk event loop. The service and DB layers cover the behavior the GUI
delegates to. For headless GUI smoke checks, run with `QT_QPA_PLATFORM=offscreen`
is not applicable (tk); use a virtual framebuffer (`xvfb-run`) if needed.
