"""
crud.py
-------
All CREATE, READ, UPDATE, DELETE operations for every table.

Tables covered:
    signals, alerts, reports, users, settings, whitelist,
    chat_history, audit_logs

Extra utilities:
    auto_create_alert      — creates alert only when confidence >= threshold
    get_alert_threshold    — reads threshold from settings table
    add_signals_batch      — bulk insert for high-speed SDR streams
    get_signals_paginated  — paginated query for large datasets
    get_signals_as_df      — returns signals as a pandas DataFrame (for Streamlit)
    get_signals_filtered   — returns signals filtered by label (for Dashboard)
"""

from datetime import datetime
import pandas as pd

from db_manager import get_connection, close_connection
from encrypted_fields import encrypt, decrypt, hash_password, check_password


# =====================================================================
# SIGNALS
# =====================================================================

def add_signal(label: str, confidence: float, frequency: float = None,
               snr: float = None, source: str = "SDR",
               inference_time_ms: int = None,
               model_version: str = None) -> int:
    """
    Inserts a new detected signal into the signals table.

    Args:
        label:             Classification result — 'Normal', 'Jamming', or 'Drone'.
        confidence:        Model confidence score between 0.0 and 1.0.
        frequency:         Detected frequency in MHz (optional).
        snr:               Signal-to-Noise Ratio in dB (optional).
        source:            Signal source identifier, default is 'SDR'.
        inference_time_ms: Model inference duration in milliseconds (optional).
        model_version:     AI model version string, e.g. 'v1.0' (optional).

    Returns:
        The id of the newly inserted row, or None on failure.

    Example:
        signal_id = add_signal("Jamming", 0.92, frequency=433.5,
                               snr=15.2, inference_time_ms=320, model_version="v1.0")
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO signals
                (timestamp, label, confidence, frequency, snr,
                 source, inference_time_ms, model_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), label, confidence, frequency, snr,
              source, inference_time_ms, model_version))
        conn.commit()
        signal_id = cursor.lastrowid
        print(f"[crud.py] Signal added — id={signal_id}, label={label}, confidence={confidence}")
        return signal_id
    except Exception as e:
        print(f"[crud.py] Error adding signal: {e}")
        conn.rollback()
        return None
    finally:
        close_connection(conn)


def add_signals_batch(signals_list: list) -> int:
    """
    Bulk-inserts multiple signals in a single transaction.
    Much faster than calling add_signal() in a loop for live SDR streams.

    Args:
        signals_list: List of dicts, each with keys:
            label (str), confidence (float),
            frequency (float, optional), snr (float, optional),
            source (str, optional), inference_time_ms (int, optional),
            model_version (str, optional)

    Returns:
        Number of successfully inserted rows.

    Example:
        add_signals_batch([
            {"label": "Jamming", "confidence": 0.91, "frequency": 433.5},
            {"label": "Normal",  "confidence": 0.98, "frequency": 88.0},
        ])
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        rows = [
            (
                now,
                s["label"],
                s["confidence"],
                s.get("frequency"),
                s.get("snr"),
                s.get("source", "SDR"),
                s.get("inference_time_ms"),
                s.get("model_version"),
            )
            for s in signals_list
        ]
        cursor.executemany("""
            INSERT INTO signals
                (timestamp, label, confidence, frequency, snr,
                 source, inference_time_ms, model_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
        count = cursor.rowcount
        print(f"[crud.py] Batch insert — {count} signals added.")
        return count
    except Exception as e:
        print(f"[crud.py] Error in batch insert: {e}")
        conn.rollback()
        return 0
    finally:
        close_connection(conn)


def get_all_signals() -> list:
    """
    Returns all signals ordered by most recent first.

    Example:
        for signal in get_all_signals():
            print(signal["label"], signal["confidence"])
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM signals ORDER BY timestamp DESC")
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[crud.py] Error fetching signals: {e}")
        return []
    finally:
        close_connection(conn)


def get_signals_paginated(limit: int = 100, offset: int = 0) -> list:
    """
    Returns a paginated slice of signals ordered by most recent first.
    Use this in the Streamlit dashboard to avoid loading thousands of rows at once.

    Args:
        limit:  Maximum number of rows to return. Default is 100.
        offset: Number of rows to skip from the start. Default is 0.

    Returns:
        List of signal dicts for the requested page.

    Example:
        page1 = get_signals_paginated(limit=50, offset=0)
        page2 = get_signals_paginated(limit=50, offset=50)
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM signals ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[crud.py] Error in paginated fetch: {e}")
        return []
    finally:
        close_connection(conn)


def get_signals_filtered(label: str = None, limit: int = 500) -> list:
    """
    Returns signals optionally filtered by label.
    Useful for showing only Jamming or Drone signals in the Dashboard.

    Args:
        label: If provided, filters to only rows matching this label.
               Pass None to return all labels.
        limit: Maximum number of rows to return. Default is 500.

    Returns:
        List of matching signal dicts.

    Example:
        jammings = get_signals_filtered(label="Jamming")
        all_sigs = get_signals_filtered()
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if label:
            cursor.execute(
                "SELECT * FROM signals WHERE label = ? ORDER BY timestamp DESC LIMIT ?",
                (label, limit))
        else:
            cursor.execute(
                "SELECT * FROM signals ORDER BY timestamp DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[crud.py] Error in filtered fetch: {e}")
        return []
    finally:
        close_connection(conn)


def get_signals_as_df(label: str = None, limit: int = 500) -> pd.DataFrame:
    """
    Returns signals as a pandas DataFrame — ready for Streamlit charts.

    Args:
        label: Optional label filter (e.g. 'Jamming'). None returns all.
        limit: Maximum number of rows. Default is 500.

    Returns:
        pandas DataFrame with all signal columns.

    Example:
        df = get_signals_as_df()
        st.line_chart(df.set_index("timestamp")["confidence"])
    """
    conn = get_connection()
    try:
        if label:
            query = "SELECT * FROM signals WHERE label = ? ORDER BY timestamp DESC LIMIT ?"
            df = pd.read_sql_query(query, conn, params=(label, limit))
        else:
            query = "SELECT * FROM signals ORDER BY timestamp DESC LIMIT ?"
            df = pd.read_sql_query(query, conn, params=(limit,))
        return df
    except Exception as e:
        print(f"[crud.py] Error fetching signals as DataFrame: {e}")
        return pd.DataFrame()
    finally:
        close_connection(conn)


def get_signal_by_id(signal_id: int) -> dict:
    """
    Returns a single signal by its id.

    Example:
        signal = get_signal_by_id(3)
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM signals WHERE id = ?", (signal_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"[crud.py] Error fetching signal by id: {e}")
        return None
    finally:
        close_connection(conn)


def get_signals_by_label(label: str) -> list:
    """
    Returns all signals matching the given label.

    Example:
        drones = get_signals_by_label("Drone")
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM signals WHERE label = ? ORDER BY timestamp DESC", (label,))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[crud.py] Error fetching signals by label: {e}")
        return []
    finally:
        close_connection(conn)


def update_signal_source(signal_id: int, new_source: str) -> bool:
    """
    Updates the source field of an existing signal.

    Example:
        update_signal_source(3, "Live SDR")
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE signals SET source = ? WHERE id = ?", (new_source, signal_id))
        conn.commit()
        print(f"[crud.py] Signal {signal_id} source updated to '{new_source}'")
        return True
    except Exception as e:
        print(f"[crud.py] Error updating signal source: {e}")
        conn.rollback()
        return False
    finally:
        close_connection(conn)


def delete_old_signals(before_date: str) -> int:
    """
    Deletes signals (and their linked alerts/reports via CASCADE) recorded
    before the given date string in YYYY-MM-DD format.

    Returns the number of deleted signal rows.

    Example:
        delete_old_signals("2025-01-01")
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM signals WHERE timestamp < ?", (before_date,))
        conn.commit()
        count = cursor.rowcount
        print(f"[crud.py] Deleted {count} signals before {before_date} (CASCADE applied).")
        return count
    except Exception as e:
        print(f"[crud.py] Error deleting old signals: {e}")
        conn.rollback()
        return 0
    finally:
        close_connection(conn)


# =====================================================================
# ALERTS
# =====================================================================

def get_alert_threshold() -> float:
    """
    Reads the alert confidence threshold from the settings table.
    Falls back to 0.75 if the setting is missing.

    Returns:
        Threshold as a float between 0.0 and 1.0.

    Example:
        threshold = get_alert_threshold()   # e.g. 0.75
    """
    value = get_setting("alert_threshold")
    return float(value) if value else 0.75


def auto_create_alert(signal_id: int, alert_type: str = "email",
                      location: str = "estimated from signal") -> int:
    """
    Automatically creates an alert for a signal — but only if:
      1. The signal exists.
      2. The signal label is NOT 'Normal'.
      3. The signal confidence >= alert_threshold from settings.
      4. The signal frequency is NOT whitelisted.

    Args:
        signal_id:  The id of the signal to evaluate.
        alert_type: Notification channel — 'email', 'whatsapp', or 'sound'.
        location:   Threat location description (will be encrypted).

    Returns:
        The new alert id if created, or None if conditions were not met.

    Example:
        alert_id = auto_create_alert(signal_id=5)
    """
    signal = get_signal_by_id(signal_id)
    if not signal:
        print(f"[crud.py] auto_create_alert — signal {signal_id} not found.")
        return None

    threshold = get_alert_threshold()

    if signal["label"] == "Normal":
        print(f"[crud.py] auto_create_alert — skipped (label is Normal).")
        return None

    if signal["confidence"] < threshold:
        print(f"[crud.py] auto_create_alert — skipped "
              f"(confidence {signal['confidence']} < threshold {threshold}).")
        return None

    if signal.get("frequency") and is_whitelisted(signal["frequency"]):
        print(f"[crud.py] auto_create_alert — skipped "
              f"(frequency {signal['frequency']} MHz is whitelisted).")
        return None

    return create_alert(signal_id, alert_type, location=location)


def create_alert(signal_id: int, alert_type: str,
                 location: str = "Unknown", status: str = "sent") -> int:
    """
    Inserts a new alert linked to a signal.
    The location field is required and automatically encrypted before storage.

    Args:
        signal_id:  The id of the related signal.
        alert_type: Notification channel — 'email', 'whatsapp', or 'sound'.
        location:   Threat location string (required, will be encrypted).
        status:     Delivery status — 'sent' or 'failed'. Default is 'sent'.

    Returns:
        The id of the newly inserted alert, or None on failure.

    Example:
        create_alert(signal_id=1, alert_type="email", location="Sector 7")
    """
    conn = get_connection()
    try:
        encrypted_location = encrypt(location)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alerts (signal_id, timestamp, alert_type, status, location)
            VALUES (?, ?, ?, ?, ?)
        """, (signal_id, datetime.now().isoformat(), alert_type, status, encrypted_location))
        conn.commit()
        alert_id = cursor.lastrowid
        print(f"[crud.py] Alert created — id={alert_id}, type={alert_type}")
        return alert_id
    except Exception as e:
        print(f"[crud.py] Error creating alert: {e}")
        conn.rollback()
        return None
    finally:
        close_connection(conn)


def get_all_alerts(decrypt_fields: bool = True) -> list:
    """
    Returns all alerts ordered by most recent first.
    Automatically decrypts location when decrypt_fields is True.

    Example:
        alerts = get_all_alerts()
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts ORDER BY timestamp DESC")
        result = []
        for row in cursor.fetchall():
            alert = dict(row)
            if decrypt_fields and alert.get("location"):
                alert["location"] = decrypt(alert["location"])
            result.append(alert)
        return result
    except Exception as e:
        print(f"[crud.py] Error fetching alerts: {e}")
        return []
    finally:
        close_connection(conn)


def get_alerts_by_date(date_str: str) -> list:
    """
    Returns all alerts from a specific date (format: YYYY-MM-DD).

    Example:
        get_alerts_by_date("2026-07-27")
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM alerts WHERE timestamp LIKE ? ORDER BY timestamp DESC",
            (f"{date_str}%",))
        result = []
        for row in cursor.fetchall():
            alert = dict(row)
            if alert.get("location"):
                alert["location"] = decrypt(alert["location"])
            result.append(alert)
        return result
    except Exception as e:
        print(f"[crud.py] Error fetching alerts by date: {e}")
        return []
    finally:
        close_connection(conn)


def update_alert_status(alert_id: int, new_status: str) -> bool:
    """
    Updates the delivery status of an alert ('sent' or 'failed').

    Example:
        update_alert_status(2, "failed")
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE alerts SET status = ? WHERE id = ?", (new_status, alert_id))
        conn.commit()
        print(f"[crud.py] Alert {alert_id} status updated to '{new_status}'")
        return True
    except Exception as e:
        print(f"[crud.py] Error updating alert status: {e}")
        conn.rollback()
        return False
    finally:
        close_connection(conn)


# =====================================================================
# REPORTS
# =====================================================================

def create_report(signal_id: int, content: str,
                  generated_by: str = "Ollama") -> int:
    """
    Inserts a new AI-generated report linked to a signal.
    The content field is automatically encrypted before storage.

    Args:
        signal_id:    The id of the related signal.
        content:      The AI Agent report text (will be encrypted).
        generated_by: Model name that generated the report. Default is 'Ollama'.

    Returns:
        The id of the newly inserted report, or None on failure.

    Example:
        create_report(signal_id=1, content="Jamming detected at 433MHz...")
    """
    conn = get_connection()
    try:
        encrypted_content = encrypt(content)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reports (signal_id, timestamp, content, generated_by)
            VALUES (?, ?, ?, ?)
        """, (signal_id, datetime.now().isoformat(), encrypted_content, generated_by))
        conn.commit()
        report_id = cursor.lastrowid
        print(f"[crud.py] Report created — id={report_id}")
        return report_id
    except Exception as e:
        print(f"[crud.py] Error creating report: {e}")
        conn.rollback()
        return None
    finally:
        close_connection(conn)


def get_all_reports(decrypt_fields: bool = True) -> list:
    """
    Returns all reports ordered by most recent first.
    Automatically decrypts content when decrypt_fields is True.

    Example:
        reports = get_all_reports()
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports ORDER BY timestamp DESC")
        result = []
        for row in cursor.fetchall():
            report = dict(row)
            if decrypt_fields and report.get("content"):
                report["content"] = decrypt(report["content"])
            result.append(report)
        return result
    except Exception as e:
        print(f"[crud.py] Error fetching reports: {e}")
        return []
    finally:
        close_connection(conn)


def get_report_by_signal(signal_id: int) -> dict:
    """
    Returns the report linked to a specific signal, with content decrypted.

    Example:
        report = get_report_by_signal(1)
        print(report["content"])
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE signal_id = ?", (signal_id,))
        row = cursor.fetchone()
        if row:
            report = dict(row)
            if report.get("content"):
                report["content"] = decrypt(report["content"])
            return report
        return None
    except Exception as e:
        print(f"[crud.py] Error fetching report by signal: {e}")
        return None
    finally:
        close_connection(conn)


# =====================================================================
# USERS
# =====================================================================

def create_user(username: str, password: str, role: str = "Operator") -> int:
    """
    Inserts a new user. The password is bcrypt-hashed before storage.

    Args:
        username: Unique username string.
        password: Plaintext password (will be hashed with bcrypt).
        role:     'Admin' or 'Operator'. Default is 'Operator'.

    Returns:
        The id of the newly created user, or None on failure.

    Example:
        create_user("goda", "securePass123", role="Admin")
    """
    conn = get_connection()
    try:
        hashed = hash_password(password)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, password, role, created_at)
            VALUES (?, ?, ?, ?)
        """, (username, hashed, role, datetime.now().isoformat()))
        conn.commit()
        user_id = cursor.lastrowid
        print(f"[crud.py] User created — id={user_id}, username={username}, role={role}")
        return user_id
    except Exception as e:
        print(f"[crud.py] Error creating user: {e}")
        conn.rollback()
        return None
    finally:
        close_connection(conn)


def get_all_users() -> list:
    """
    Returns all users. Passwords are intentionally excluded from the result.

    Example:
        for u in get_all_users():
            print(u["username"], u["role"])
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, role, created_at, last_login FROM users")
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[crud.py] Error fetching users: {e}")
        return []
    finally:
        close_connection(conn)


def verify_user(username: str, password: str) -> bool:
    """
    Verifies login credentials using bcrypt comparison.
    Updates last_login timestamp on success.

    Args:
        username: The username to look up.
        password: The plaintext password to verify.

    Returns:
        True if credentials are correct, False otherwise.

    Example:
        if verify_user("goda", "securePass123"):
            print("Access granted")
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, password FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if not row:
            return False
        if check_password(password, row["password"]):
            cursor.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now().isoformat(), row["id"]))
            conn.commit()
            print(f"[crud.py] User '{username}' verified successfully.")
            return True
        return False
    except Exception as e:
        print(f"[crud.py] Error verifying user: {e}")
        return False
    finally:
        close_connection(conn)


def update_user_role(username: str, new_role: str) -> bool:
    """
    Updates the role of an existing user.

    Example:
        update_user_role("aya", "Admin")
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET role = ? WHERE username = ?", (new_role, username))
        conn.commit()
        print(f"[crud.py] User '{username}' role updated to '{new_role}'")
        return True
    except Exception as e:
        print(f"[crud.py] Error updating user role: {e}")
        conn.rollback()
        return False
    finally:
        close_connection(conn)


def delete_user(username: str) -> bool:
    """
    Deletes a user by username.

    Example:
        delete_user("old_operator")
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        print(f"[crud.py] User '{username}' deleted.")
        return True
    except Exception as e:
        print(f"[crud.py] Error deleting user: {e}")
        conn.rollback()
        return False
    finally:
        close_connection(conn)


# =====================================================================
# SETTINGS
# =====================================================================

def get_setting(key: str) -> str:
    """
    Returns the value of a setting by its key, or None if not found.

    Example:
        gain = get_setting("gain")   # returns "40"
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else None
    except Exception as e:
        print(f"[crud.py] Error fetching setting: {e}")
        return None
    finally:
        close_connection(conn)


def get_all_settings() -> list:
    """
    Returns all settings as a list of dicts.

    Example:
        for s in get_all_settings():
            print(s["key"], "=", s["value"])
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM settings")
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[crud.py] Error fetching settings: {e}")
        return []
    finally:
        close_connection(conn)


def update_setting(key: str, new_value: str) -> bool:
    """
    Updates the value of an existing setting.

    Example:
        update_setting("gain", "45")
        update_setting("alert_threshold", "0.80")
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE settings SET value = ?, updated_at = ? WHERE key = ?",
            (new_value, datetime.now().isoformat(), key))
        conn.commit()
        print(f"[crud.py] Setting '{key}' updated to '{new_value}'")
        return True
    except Exception as e:
        print(f"[crud.py] Error updating setting: {e}")
        conn.rollback()
        return False
    finally:
        close_connection(conn)


def add_setting(key: str, value: str, description: str = "") -> bool:
    """
    Adds a new setting. Silently ignored if the key already exists.

    Example:
        add_setting("scan_interval", "5", "Seconds between each SDR scan")
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value, description, updated_at)
            VALUES (?, ?, ?, ?)
        """, (key, value, description, datetime.now().isoformat()))
        conn.commit()
        print(f"[crud.py] Setting '{key}' added.")
        return True
    except Exception as e:
        print(f"[crud.py] Error adding setting: {e}")
        conn.rollback()
        return False
    finally:
        close_connection(conn)


# =====================================================================
# WHITELIST
# =====================================================================

def add_to_whitelist(frequency: float, label: str = None,
                     added_by: str = "system") -> int:
    """
    Adds a frequency to the whitelist so it does not trigger alerts.

    Args:
        frequency: The allowed frequency in MHz.
        label:     Optional friendly name (e.g. 'FM Radio').
        added_by:  Username who added this entry. Default is 'system'.

    Returns:
        The id of the new whitelist entry, or None on failure.

    Example:
        add_to_whitelist(98.5, label="Nile FM", added_by="admin")
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO whitelist (frequency, label, added_by, added_at)
            VALUES (?, ?, ?, ?)
        """, (frequency, label, added_by, datetime.now().isoformat()))
        conn.commit()
        wl_id = cursor.lastrowid
        print(f"[crud.py] Frequency {frequency} MHz added to whitelist.")
        return wl_id
    except Exception as e:
        print(f"[crud.py] Error adding to whitelist: {e}")
        conn.rollback()
        return None
    finally:
        close_connection(conn)


def get_all_whitelist() -> list:
    """
    Returns all whitelisted frequencies ordered by frequency value.

    Example:
        for entry in get_all_whitelist():
            print(entry["frequency"], entry["label"])
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM whitelist ORDER BY frequency ASC")
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[crud.py] Error fetching whitelist: {e}")
        return []
    finally:
        close_connection(conn)


def is_whitelisted(frequency: float, tolerance: float = 0.1) -> bool:
    """
    Returns True if the given frequency is within tolerance of any whitelisted entry.

    Args:
        frequency:  The frequency to check in MHz.
        tolerance:  Acceptable deviation in MHz. Default is 0.1 MHz.

    Returns:
        True if whitelisted, False otherwise.

    Example:
        if is_whitelisted(88.1):
            print("Normal — no alert needed")
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM whitelist
            WHERE frequency BETWEEN ? AND ?
        """, (frequency - tolerance, frequency + tolerance))
        return cursor.fetchone() is not None
    except Exception as e:
        print(f"[crud.py] Error checking whitelist: {e}")
        return False
    finally:
        close_connection(conn)


def remove_from_whitelist(frequency: float) -> bool:
    """
    Removes a frequency from the whitelist.

    Example:
        remove_from_whitelist(98.5)
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM whitelist WHERE frequency = ?", (frequency,))
        conn.commit()
        print(f"[crud.py] Frequency {frequency} MHz removed from whitelist.")
        return True
    except Exception as e:
        print(f"[crud.py] Error removing from whitelist: {e}")
        conn.rollback()
        return False
    finally:
        close_connection(conn)


# =====================================================================
# CHAT HISTORY
# =====================================================================

def add_chat_message(session_id: str, user_query: str,
                     agent_response: str) -> int:
    """
    Saves a single AI Agent conversation turn to chat_history.

    Args:
        session_id:     Unique identifier for the conversation session.
        user_query:     The question the user typed.
        agent_response: The AI Agent's reply.

    Returns:
        The id of the new chat record, or None on failure.

    Example:
        add_chat_message("session_abc", "Is there jamming now?",
                         "Yes, jamming detected at 433 MHz with 92% confidence.")
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_history (session_id, user_query, agent_response, timestamp)
            VALUES (?, ?, ?, ?)
        """, (session_id, user_query, agent_response, datetime.now().isoformat()))
        conn.commit()
        chat_id = cursor.lastrowid
        print(f"[crud.py] Chat message saved — id={chat_id}")
        return chat_id
    except Exception as e:
        print(f"[crud.py] Error saving chat message: {e}")
        conn.rollback()
        return None
    finally:
        close_connection(conn)


def get_chat_history(session_id: str) -> list:
    """
    Returns all messages for a given session ordered by time.

    Example:
        history = get_chat_history("session_abc")
        for msg in history:
            print(msg["user_query"], "->", msg["agent_response"])
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM chat_history WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[crud.py] Error fetching chat history: {e}")
        return []
    finally:
        close_connection(conn)


# =====================================================================
# AUDIT LOGS
# =====================================================================

def log_action(action: str, details: str = None, user_id: int = None) -> int:
    """
    Writes an audit log entry for security tracking.

    Args:
        action:  Short action name — e.g. 'LOGIN', 'UPDATE_SETTING', 'DELETE_SIGNAL'.
        details: Optional extra context or description.
        user_id: The id of the user who performed the action (None for system events).

    Returns:
        The id of the new log entry, or None on failure.

    Example:
        log_action("LOGIN", details="User goda logged in", user_id=1)
        log_action("UPDATE_SETTING", details="gain changed from 40 to 45", user_id=1)
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, details, timestamp)
            VALUES (?, ?, ?, ?)
        """, (user_id, action, details, datetime.now().isoformat()))
        conn.commit()
        log_id = cursor.lastrowid
        print(f"[crud.py] Audit log — action={action}")
        return log_id
    except Exception as e:
        print(f"[crud.py] Error writing audit log: {e}")
        conn.rollback()
        return None
    finally:
        close_connection(conn)


def get_audit_logs(limit: int = 200) -> list:
    """
    Returns the most recent audit log entries.

    Args:
        limit: Maximum number of entries to return. Default is 200.

    Example:
        for entry in get_audit_logs():
            print(entry["action"], entry["timestamp"])
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[crud.py] Error fetching audit logs: {e}")
        return []
    finally:
        close_connection(conn)


# =====================================================================
# BULK DELETE  (all time-based tables)
# =====================================================================

def delete_old_records(before_date: str) -> dict:
    """
    Deletes all records older than the given date from signals, alerts, reports,
    and chat_history. alerts and reports linked to signals are removed via CASCADE.

    Args:
        before_date: Date string in YYYY-MM-DD format.

    Returns:
        Dict with deleted row counts per table.

    Example:
        delete_old_records("2025-01-01")
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM chat_history WHERE timestamp < ?", (before_date,))
        chat_deleted = cursor.rowcount

        # signals CASCADE deletes linked alerts and reports automatically
        cursor.execute("DELETE FROM signals WHERE timestamp < ?", (before_date,))
        signals_deleted = cursor.rowcount

        conn.commit()
        result = {
            "signals_deleted":     signals_deleted,
            "chat_history_deleted": chat_deleted,
        }
        print(f"[crud.py] Old records deleted: {result} (alerts & reports removed via CASCADE)")
        return result
    except Exception as e:
        print(f"[crud.py] Error deleting old records: {e}")
        conn.rollback()
        return {}
    finally:
        close_connection(conn)
