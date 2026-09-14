const fs = require("fs");
const path = require("path");
const { generateStudents } = require("../data/names");

function esc(value) {
  return String(value).replace(/'/g, "''");
}

const students = generateStudents();
const outDir = path.join(__dirname, "..", "mysql-init");

let resultSql = `CREATE DATABASE IF NOT EXISTS result_db;
USE result_db;

CREATE TABLE result (
  student_id INT,
  first_name VARCHAR(50),
  last_name VARCHAR(500),
  password VARCHAR(50),
  cgpa DECIMAL(3,2)
);

INSERT INTO result (student_id, first_name, last_name, password, cgpa) VALUES\n`;
resultSql +=
  students
    .map(
      (s) =>
        `  (${s.studentId}, '${esc(s.firstName)}', '${esc(s.lastName)}', '${esc(s.password)}', ${s.cgpa})`
    )
    .join(",\n") + ";\n";

fs.writeFileSync(path.join(outDir, "01-result-schema.sql"), resultSql);

let socialSql = `CREATE DATABASE IF NOT EXISTS social_db;
USE social_db;

CREATE TABLE user (
  username VARCHAR(100),
  password VARCHAR(50),
  first_name VARCHAR(50),
  last_name VARCHAR(50)
);

CREATE TABLE post (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(100),
  post TEXT
);

INSERT INTO user (username, password, first_name, last_name) VALUES\n`;
socialSql +=
  students
    .map((s) => {
      const username = `${s.firstName}_${s.lastName}`.toLowerCase();
      return `  ('${esc(username)}', '${esc(s.password)}', '${esc(s.firstName)}', '${esc(s.lastName)}')`;
    })
    .join(",\n") + ";\n";

fs.writeFileSync(path.join(outDir, "02-social-schema.sql"), socialSql);

console.log("Generated mysql-init/01-result-schema.sql and mysql-init/02-social-schema.sql");
