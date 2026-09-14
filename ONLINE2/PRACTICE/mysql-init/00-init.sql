CREATE USER IF NOT EXISTS 'appuser'@'%' IDENTIFIED BY 'apppassword';
GRANT ALL PRIVILEGES ON result_db.* TO 'appuser'@'%';
GRANT ALL PRIVILEGES ON social_db.* TO 'appuser'@'%';
FLUSH PRIVILEGES;
