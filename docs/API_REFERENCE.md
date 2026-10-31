# API Reference

## `ToolService` (`service.py`)

Business rules for inventory, borrowing, and returning.

| Method | Signature | Returns |
|---|---|---|
| `add_tool` | `(name, category, condition, quantity, location, actor=None)` | `True` or `ServiceError` |
| `update_tool` | `(tool_id, actor, **fields)` | `True` or `ServiceError` |
| `delete_tool` | `(tool_id, actor=None)` | `True` or `ServiceError` |
| `list_tools` | `(page=1, page_size=20)` | list of rows |
| `search_tools` | `(keyword)` | list of rows |
| `borrow_tool` | `(tool_id, user_id, borrow_date=None)` | `True` or `ServiceError` |
| `return_tool` | `(tool_id, user_id, return_date=None)` | `True` or `ServiceError` |
| `my_borrowed_tools` | `(user_id)` | list of rows |
| `available_tools` | `()` | list of rows |
| `all_tools` | `()` | list of rows |
| `clear_inventory` | `(actor)` | result or `ServiceError` |

Validation constants: `VALID_CONDITIONS = ("Good", "Fair", "Poor")`.

## `AuthService` (`service.py`)

| Method | Signature | Returns |
|---|---|---|
| `register` | `(username, password, confirm, name, age, email)` | `True` or `ServiceError` |
| `login` | `(username, password)` | user row or `ServiceError` |

Constants: `MIN_PASSWORD_LEN = 6`, `MIN_USERNAME_LEN = 3`.

## `DatabaseManager` (`database.py`)

Persistence seam. Key groups:

- **Connection:** `connect`, `ensure_connection_open`, `close`
- **Schema:** `create_tables`, `_migrate`
- **Auth:** `insert_user`, `authenticate`, `username_exists`, `is_admin`,
  `is_locked_out`
- **Tools:** `add_tool`, `update_tool`, `delete_tool`, `fetch_tool_by_id`,
  `fetch_tools_paginated`, `search_tool`, `tool_name_exists`, `fetch_all_tools`,
  `fetch_borrowable_tools`
- **Borrow/return:** `borrow_tool`, `return_tool`, `fetch_borrowed_by_user`
- **Admin:** `clear_tables(actor)` (admin-gated)
- **Rate limiting:** attempt logging + lockout window helpers

`ServiceError` is the single user-facing error type; presentation code should
catch it and display `.args[0]`.
