# Security

## Authentication
- Passwords are stored as **bcrypt hashes** (`bcrypt.gensalt()`, default cost).
  Plaintext never touches disk.
- Login rate limiting: 5 failed attempts per username in a rolling 10-minute
  window. Even correct credentials are rejected while the window is active.
  Successful login drains the attempt log for that user.
- Unknown usernames are also rate-limited (no username enumeration via timing).

## Authorization (RBAC)
- Two roles: Admin and Regular User.
- RBAC is enforced at **both** the service layer (business rules) and the DB
  layer (`clear_tables` re-checks `is_admin`; its `actor` argument is
  mandatory, so omitting it can never skip the check).
- A caller that bypasses the service still hits the DB-layer gate.

## SQL Injection Defense
- All queries are parameterised.
- The only f-string-built fragment is the column-name list in `update_tool`,
  sourced from a hard-coded `allowed` set in the DB layer (defense-in-depth on
  top of service-layer RBAC).

## CLI SQL Console
- Admin-only and read-only.
- Statements must start with `SELECT`, `PRAGMA`, `EXPLAIN`, or `WITH`.
- Execution happens on a dedicated read-only SQLite connection
  (`mode=ro` + `PRAGMA query_only`), so destructive statements fail at the
  engine level instead of relying on keyword filtering.

## Default Credentials
- On first run the app seeds `admin` / `admin123` if no admin exists.
- **This is a classroom-demo convenience, not a security feature.** Change or
  delete the default account before any non-demo use. The CLI prints no
  warning; operators are expected to know this.

## Audit
- All writes stream to stdout and `logs/app.log` (rotating, 1 MB × 3) for an
  audit trail.
