const express = require("express");
const crypto = require("crypto");
const { pool } = require("./db");

const app = express();
const PORT = 3001;

process.on("unhandledRejection", () => {
  console.log("An error occurred");
});

app.use(express.urlencoded({ extended: false }));

const sessions = new Map();

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function getCookie(req, name) {
  const header = req.headers.cookie;
  if (!header) return null;
  for (const part of header.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return rest.join("=");
  }
  return null;
}

function getSessionUser(req) {
  const sid = getCookie(req, "sid");
  if (!sid) return null;
  return sessions.get(sid) || null;
}

function loginPage(error) {
  return `<!DOCTYPE html>
<html>
<head><title>Login</title></head>
<body>
  <h1>Login</h1>
  ${error ? `<p>${escapeHtml(error)}</p>` : ""}
  <form method="POST" action="/login">
    <label>Username: <input type="text" name="username"></label><br>
    <label>Password: <input type="password" name="password"></label><br>
    <button type="submit">Log In</button>
  </form>
</body>
</html>`;
}

app.get("/login", (req, res) => {
  res.send(loginPage(null));
});

app.post("/login", async (req, res) => {
  try {
    const { username, password } = req.body;

    const [rows] = await pool.execute(
      "SELECT * FROM user WHERE username = ? AND password = ?",
      [username || "", password || ""]
    );
    const user = rows.length > 0 ? rows[0] : null;

    if (!user) {
      res.send(loginPage("Invalid username or password"));
      return;
    }

    const sid = crypto.randomUUID();
    sessions.set(sid, user.username);
    res.setHeader("Set-Cookie", `sid=${sid}; HttpOnly; Path=/`);
    res.redirect("/");
  } catch (err) {
    console.log("An error occurred");
    res.status(500).send(loginPage("Something went wrong, please try again"));
  }
});

app.get("/", async (req, res) => {
  const username = getSessionUser(req);
  if (!username) {
    res.redirect("/login");
    return;
  }

  try {
    const [posts] = await pool.query(
      `SELECT post.post AS post, user.first_name AS first_name, user.last_name AS last_name
       FROM post JOIN user ON post.username = user.username
       ORDER BY post.id DESC`
    );

    const postsHtml = posts
      .map(
        (p) =>
          `<p><b>${escapeHtml(p.first_name)} ${escapeHtml(p.last_name)}</b><br>${escapeHtml(p.post)}</p>`
      )
      .join("\n");

    res.send(`<!DOCTYPE html>
<html>
<head><title>Feed</title></head>
<body>
  <a href="/logout">Log Out</a>
  <form method="POST" action="/create">
    <input type="text" name="message">
    <button type="submit">Post</button>
  </form>
  ${postsHtml}
</body>
</html>`);
  } catch (err) {
    console.log("An error occurred");
    res.status(500).send("Something went wrong");
  }
});

app.get("/logout", (req, res) => {
  const sid = getCookie(req, "sid");
  if (sid) {
    sessions.delete(sid);
  }
  res.setHeader("Set-Cookie", "sid=; HttpOnly; Path=/; Max-Age=0");
  res.redirect("/login");
});

app.post("/create", async (req, res) => {
  const username = getSessionUser(req);
  if (!username) {
    res.redirect("/login");
    return;
  }

  try {
    const { message } = req.body;
    if (typeof message !== "string" || message.length === 0) {
      res.redirect("/");
      return;
    }

    await pool.execute("INSERT INTO post (username, post) VALUES (?, ?)", [username, message]);
    res.redirect("/");
  } catch (err) {
    console.log("An error occurred");
    res.status(500).send("Something went wrong");
  }
});

app.listen(PORT, () => {
  console.log(`Social site listening on port ${PORT}`);
});
