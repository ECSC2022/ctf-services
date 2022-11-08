CREATE TABLE IF NOT EXISTS links(
    id      INTEGER PRIMARY KEY,
    url     TEXT NOT NULL,
    uuid    TEXT NOT NULL UNIQUE,
    visited INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages(
    id      INTEGER PRIMARY KEY,
    link_id INTEGER NOT NULL,
    message TEXT,
    ts      TIMESTAMP,
    FOREIGN KEY(link_id) REFERENCES links(id)
);