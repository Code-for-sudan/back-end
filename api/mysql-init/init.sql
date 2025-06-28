-- This script initializes the MySQL database for the Sudamall project.
DROP DATABASE IF EXISTS sudamall_db;

DROP DATABASE IF EXISTS test_myproject;

CREATE DATABASE IF NOT EXISTS sudamall_db;

CREATE DATABASE IF NOT EXISTS test_myproject;

CREATE USER IF NOT EXISTS 'api'@'%' IDENTIFIED BY 'sudamall_password';

GRANT ALL PRIVILEGES ON sudamall_db.* TO 'api'@'%';

GRANT ALL PRIVILEGES ON test_myproject.* TO 'api'@'%';

FLUSH PRIVILEGES;
