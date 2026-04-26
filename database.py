import sqlite3
import datetime
import os

DB_NAME = "usage.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    # Table to store which apps we are tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS TrackedApps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT UNIQUE NOT NULL
        )
    ''')
    try:
        cursor.execute('ALTER TABLE TrackedApps ADD COLUMN exe_path TEXT')
    except sqlite3.OperationalError:
        pass # Column might already exist
    # Table to store usage logs per day
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS UsageLogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT NOT NULL,
            log_date DATE NOT NULL,
            duration_seconds INTEGER DEFAULT 0,
            UNIQUE(app_name, log_date)
        )
    ''')
    conn.commit()
    conn.close()

def get_tracked_apps():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT app_name FROM TrackedApps')
    apps = [row[0] for row in cursor.fetchall()]
    conn.close()
    return apps

def add_tracked_app(app_name, exe_path=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if exe_path:
            cursor.execute('INSERT INTO TrackedApps (app_name, exe_path) VALUES (?, ?)', (app_name.lower(), exe_path))
        else:
            cursor.execute('INSERT INTO TrackedApps (app_name) VALUES (?)', (app_name.lower(),))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_app_path(app_name, exe_path):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE TrackedApps SET exe_path = ? WHERE app_name = ?', (exe_path, app_name.lower()))
    conn.commit()
    conn.close()

def get_app_paths():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT app_name, exe_path FROM TrackedApps WHERE exe_path IS NOT NULL')
    paths = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return paths

def remove_tracked_app(app_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM TrackedApps WHERE app_name = ?', (app_name.lower(),))
    # Option: do not delete from UsageLogs to keep history
    conn.commit()
    conn.close()

def log_usage(app_name, duration_seconds):
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.date.today().isoformat()
    app_name = app_name.lower()
    
    # Check if entry exists for today
    cursor.execute('SELECT id, duration_seconds FROM UsageLogs WHERE app_name = ? AND log_date = ?', (app_name, today))
    row = cursor.fetchone()
    
    if row:
        new_duration = row[1] + duration_seconds
        cursor.execute('UPDATE UsageLogs SET duration_seconds = ? WHERE id = ?', (new_duration, row[0]))
    else:
        cursor.execute('INSERT INTO UsageLogs (app_name, log_date, duration_seconds) VALUES (?, ?, ?)', (app_name, today, duration_seconds))
        
    conn.commit()
    conn.close()

def get_today_usage():
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.date.today().isoformat()
    cursor.execute('SELECT app_name, duration_seconds FROM UsageLogs WHERE log_date = ?', (today,))
    data = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return data
