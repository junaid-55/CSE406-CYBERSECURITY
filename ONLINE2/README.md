# ONLINE 2 — Web Application Security (SQLi / XSS / CSRF)

Kept as a record of the CSE405 Online 2 work. It has two parts: the
graded assignment (A1) and a self-built practice lab I used to prepare.

Everything here is deliberately vulnerable and intended for **local,
authorized practice only**.

## `A1-Ethical-Hacking/` — the graded assignment

A provided Docker environment (a library-fines app and a marketplace app
backed by MySQL) that had to be attacked via SQL injection and a
stored-XSS → CSRF chain.

- `2105006.txt` — my submission: the actual injection payloads and steps
  (login bypass, `ORDER BY` column count, `UNION SELECT`,
  `information_schema` enumeration, data extraction, and the stored-XSS
  payload that forces a cross-site POST).
- `A1-spec.pdf` — the problem statement.
- `compose.yaml` — the lab's compose file, kept as a record of the
  environment (services and ports the attacks targeted).

**Removed:** `A1-images.tar` (~294 MB of provided Docker images — course
material, not my work) and `SHA256SUMS` (checksums for that tar). The
images were supplied by the course and can be re-provided.

## `PRACTICE/` — self-built SQLi + stored-XSS→CSRF lab

Two small Node.js/Express sites against MySQL (a result portal with a
SQL-injectable login, and a social site with no CSRF protection) that I
built to practise UNION-based SQL injection and a stored-XSS → CSRF chain
before the assignment. See `README.md` inside for how to run it.

- `writeup.md`, `sqli-union-methodology.md`,
  `stored-xss-to-csrf-methodology.md` — my methodology notes and writeup.
- App source, schemas (`mysql-init/00-init.sql`), seed generator, and
  Docker setup are kept.

**Removed:** `package-lock.json` (regenerate via `npm install`), the
generated seed schemas `mysql-init/01-*.sql` and `02-*.sql` (regenerate
with `npm run generate-seed`), and the embedded `.git` history (folded
into this repo). The generated seeds are intentionally not committed —
the CGPA values there are the data the exercise extracts.
