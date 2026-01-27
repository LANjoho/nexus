-- =========================================================
-- Clinical Room Management Database Schema
-- =========================================================

-- -----------------------------
-- Rooms (current state)
-- -----------------------------
CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL
);

-- -----------------------------
-- Room state change history
-- -----------------------------
CREATE TABLE IF NOT EXISTS room_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    old_status TEXT NOT NULL,
    new_status TEXT NOT NULL,
    source TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES rooms(id)
);
