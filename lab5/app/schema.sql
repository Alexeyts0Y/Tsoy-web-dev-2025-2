DROP TABLE IF EXISTS visit_logs;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS roles;

CREATE TABLE roles (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(25) NOT NULL,
    description TEXT
) ENGINE INNODB;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(25) UNIQUE NOT NULL,
    first_name VARCHAR(25) NOT NULL,
    last_name VARCHAR(25) NOT NULL,
    middle_name VARCHAR(25) DEFAULT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    role_id INTEGER,
    FOREIGN KEY (role_id) REFERENCES roles(id)
) ENGINE INNODB;

CREATE TABLE visit_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    path VARCHAR(100) NOT NULL,
    user_id INT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE INNODB;

INSERT INTO roles (id, name, description) VALUES (1, 'admin', 'Administrator with full rights');
INSERT INTO roles (id, name, description) VALUES (2, 'user', 'Regular user with limited rights');

INSERT INTO users (username, first_name, last_name, password_hash, role_id)
VALUES ('admin', 'Иван', 'Иванов', SHA2('qwerty', 256), 1); -- Admin user
INSERT INTO users (username, first_name, last_name, password_hash, role_id)
VALUES ('user1', 'Петр', 'Петров', SHA2('password123', 256), 2); -- Regular user
INSERT INTO users (username, first_name, last_name, password_hash, role_id)
VALUES ('user2', 'Анна', 'Сидорова', SHA2('securepass', 256), 2); -- Regular user