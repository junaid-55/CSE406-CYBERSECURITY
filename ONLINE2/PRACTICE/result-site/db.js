const mysql = require("mysql2/promise");

const pool = mysql.createPool({
  host: process.env.MYSQL_HOST || "mysql",
  user: process.env.MYSQL_USER || "appuser",
  password: process.env.MYSQL_PASSWORD || "apppassword",
  database: "result_db",
  multipleStatements: true
});

module.exports = { pool };
