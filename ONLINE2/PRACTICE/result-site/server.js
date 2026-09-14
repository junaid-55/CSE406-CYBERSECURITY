const express = require("express");
const { pool } = require("./db");

const app = express();
const PORT = 3000;

process.on("unhandledRejection", () => {
  console.log("An error occurred");
});

function renderPage(row) {
  const nameCell = row ? `${row.first_name} ${row.last_name}` : "";
  const cgpaCell = row ? row.cgpa : "";

  return `<!DOCTYPE html>
<html>
<head><title>Student Results</title></head>
<body>
  <h1>Student Result Portal</h1>
  <form method="GET" action="/" autocomplete="off">
    <label>Student ID: <input type="text" name="student_id" autocomplete="off" size="120"></label><br>
    <label>Password: <input type="text" name="password" autocomplete="off" size="120"></label><br>
    <button type="submit">View Result</button>
  </form>
  <table border="1">
    <tr><th>Name</th><th>CGPA</th></tr>
    <tr><td>${nameCell}</td><td>${cgpaCell}</td></tr>
  </table>
</body>
</html>`;
}

app.get("/", async (req, res) => {
  const { student_id, password } = req.query;

  if (student_id === undefined || password === undefined) {
    res.send(renderPage(null));
    return;
  }

  let row = null;
  try {
    const sql = `SELECT * FROM result WHERE student_id = '${student_id}' AND password = '${password}'`;
    const [results] = await pool.query(sql);
    const rows = Array.isArray(results[0]) ? results[0] : results;
    row = rows.length > 0 ? rows[0] : null;
  } catch (err) {
    console.log("An error occurred");
  }

  res.send(renderPage(row));
});

app.listen(PORT, () => {
  console.log(`Result site listening on port ${PORT}`);
});
