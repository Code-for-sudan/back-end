CREATE DATABASE IF NOT EXISTS sudamall_db;

CREATE DATABASE IF NOT EXISTS test_myproject;

CREATE USER IF NOT EXISTS 'api'@'%' IDENTIFIED BY 'sudamall_password';

GRANT ALL PRIVILEGES ON sudamall_db.* TO 'api'@'%';

GRANT ALL PRIVILEGES ON test_myproject.* TO 'api'@'%';

FLUSH PRIVILEGES;

