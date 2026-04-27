"""
models.py
---------
Defines all database table schemas, indexes, and default seed data.
Run this file once to initialize the full database structure.
"""

import sqlite3
from db_manager import get_connection, close_connection


# =====================================================================
# TABLE DEFINITIONS
# =====================================================================

CREATE_SIGNALS_TABLE = """
CREATE TABLE IF NOT EXISTS signals (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp         TEXT    NOT NULL,
    label             TEXT    NOT NULL,           -- Normal / Jamming / Drone
    confidence        REAL    NOT NULL,           -- Model confidence score (0.0 - 1.0)
    frequency         REAL,                       -- Frequency in MHz
    snr               REAL,                       -- Signal-to-Noise Ratio in dB
    source            TEXT    DEFAULT 'SDR',      -- Signal source identifier
    inference_time_ms INTEGER,                    -- Model inference time in milliseconds
    model_version     TEXT                        -- AI model version used for classification
);
"""

CREATE_ALERTS_TABLE = """
CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id   INTEGER NOT NULL,
    timestamp   TEXT    NOT NULL,
    alert_type  TEXT    NOT NULL,               -- email / whatsapp / sound
    status      TEXT    DEFAULT 'sent',          -- sent / failed
    location    TEXT    NOT NULL,                -- Threat location (always required, encrypted)
    FOREIGN KEY (signal_id) REFERENCES signals(id) ON DELETE CASCADE
);
"""

CREATE_REPORTS_TABLE = """
CREATE TABLE IF NOT EXISTS reports (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id    INTEGER NOT NULL,
    timestamp    TEXT    NOT NULL,
    content      TEXT    NOT NULL,              -- AI Agent report text (encrypted)
    generated_by TEXT    DEFAULT 'Ollama',
    FOREIGN KEY (signal_id) REFERENCES signals(id) ON DELETE CASCADE
);
"""

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL UNIQUE,
    password    TEXT    NOT NULL,               -- bcrypt hashed password
    role        TEXT    NOT NULL DEFAULT 'Operator',  -- Admin / Operator
    created_at  TEXT    NOT NULL,
    last_login  TEXT
);
"""

CREATE_SETTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS settings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    key         TEXT    NOT NULL UNIQUE,        -- Setting name (e.g. 'gain', 'alert_threshold')
    value       TEXT    NOT NULL,               -- Setting value as string
    description TEXT,                           -- Human-readable description
    updated_at  TEXT    NOT NULL
);
"""

CREATE_WHITELIST_TABLE = """
CREATE TABLE IF NOT EXISTS whitelist (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    frequency   REAL    NOT NULL UNIQUE,        -- Allowed frequency in MHz
    label       TEXT,                           -- Friendly name (e.g. 'FM Radio')
    added_by    TEXT,                           -- Username who added this entry
    added_at    TEXT    NOT NULL
);
"""

CREATE_CHAT_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS chat_history (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id     TEXT    NOT NULL,            -- Unique session identifier
    user_query     TEXT    NOT NULL,            -- The question the user asked the AI Agent
    agent_response TEXT    NOT NULL,            -- The AI Agent's response
    timestamp      TEXT    NOT NULL
);
"""

CREATE_AUDIT_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS audit_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,                        -- Who performed the action (nullable for system)
    action      TEXT    NOT NULL,               -- e.g. 'LOGIN', 'UPDATE_SETTING', 'DELETE_SIGNAL'
    details     TEXT,                           -- Extra context about the action
    timestamp   TEXT    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


# =====================================================================
# INDEXES  (speed up frequent lookups)
# =====================================================================

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_signals_label     ON signals(label);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_signal_id  ON alerts(signal_id);",
    "CREATE INDEX IF NOT EXISTS idx_reports_signal_id ON reports(signal_id);",
    "CREATE INDEX IF NOT EXISTS idx_audit_user_id     ON audit_logs(user_id);",
]


# =====================================================================
# DEFAULT SEED DATA
# =====================================================================

DEFAULT_SETTINGS = [
    ("gain",             "40",    "SDR receiver gain in dB (0–49)"),
    ("sample_rate",      "2.4e6", "SDR sample rate in samples/sec"),
    ("center_frequency", "433.0", "Default center frequency in MHz"),
    ("fft_size",         "1024",  "FFT window size for spectrogram generation"),
    ("alert_threshold",  "0.75",  "Minimum confidence score required to trigger an alert"),
    ("model_version",    "v1.0",  "Current AI model version"),
    ("scan_interval",    "5",     "Seconds between each SDR scan cycle"),
]

DEFAULT_WHITELIST = [
    (88.0,  "FM Radio Band Start"),
    (108.0, "FM Radio Band End"),
    (121.5, "Aviation Emergency"),
    (156.8, "Marine Channel 16"),
]


def _insert_defaults(conn: sqlite3.Connection) -> None:
    """Inserts default settings and whitelist entries — skips duplicates."""
    from datetime import datetime
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    for key, value, description in DEFAULT_SETTINGS:
        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value, description, updated_at)
            VALUES (?, ?, ?, ?)
        """, (key, value, description, now))

    for frequency, label in DEFAULT_WHITELIST:
        cursor.execute("""
            INSERT OR IGNORE INTO whitelist (frequency, label, added_by, added_at)
            VALUES (?, ?, ?, ?)
        """, (frequency, label, "system", now))


# =====================================================================
# MAIN INIT FUNCTION
# =====================================================================

def create_all_tables() -> None:
    """
    Creates all tables, indexes, and inserts default seed data.
    Safe to call multiple times — uses IF NOT EXISTS throughout.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Create tables
        cursor.execute(CREATE_SIGNALS_TABLE)
        cursor.execute(CREATE_ALERTS_TABLE)
        cursor.execute(CREATE_REPORTS_TABLE)
        cursor.execute(CREATE_USERS_TABLE)
        cursor.execute(CREATE_SETTINGS_TABLE)
        cursor.execute(CREATE_WHITELIST_TABLE)
        cursor.execute(CREATE_CHAT_HISTORY_TABLE)
        cursor.execute(CREATE_AUDIT_LOGS_TABLE)

        # Create indexes
        for index_sql in CREATE_INDEXES:
            cursor.execute(index_sql)

        # Insert defaults
        _insert_defaults(conn)
        conn.commit()
        print("[models.py] All tables, indexes, and defaults initialized successfully.")
    except Exception as e:
        print(f"[models.py] Error during initialization: {e}")
        conn.rollback()
    finally:
        close_connection(conn)


if __name__ == "__main__":
    create_all_tables()
