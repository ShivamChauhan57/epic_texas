CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    firstname TEXT,
    lastname TEXT,
    university TEXT,
    major TEXT,
    passwordHash TEXT
);

CREATE TABLE connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    connection_id INTEGER,
    request_status TEXT CHECK(request_status IN ('pending', 'accepted')),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (connection_id) REFERENCES users (id) ON DELETE CASCADE,
    UNIQUE (user_id, connection_id)
);

CREATE TABLE job_postings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    description TEXT,
    employer TEXT,
    location TEXT,
    salary INTEGER,
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    email_notifications_enabled BOOLEAN,
    sms_notifications_enabled BOOLEAN,
    targeted_advertising_enabled BOOLEAN,
    language TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);