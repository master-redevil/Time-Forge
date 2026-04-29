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
    # Table to store individual usage sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT,
            start_date DATETIME,
            duration_seconds INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    # Table to store total device active time (not idle)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS DeviceActivity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date DATE UNIQUE NOT NULL,
            duration_seconds INTEGER DEFAULT 0
        )
    ''')
    
    # Migration: Ensure all columns exist (for older schemas)
    cursor.execute("PRAGMA table_info(Sessions)")
    columns = [row[1] for row in cursor.fetchall()]
    
    # If legacy column 'start_time' exists, it will cause IntegrityErrors.
    # Since sessions are reset on app start anyway, we can safely drop and recreate.
    if 'start_time' in columns:
        cursor.execute('DROP TABLE Sessions')
        # Re-run the creation
        cursor.execute('''
            CREATE TABLE Sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT,
                start_date DATETIME,
                duration_seconds INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        # Refresh column list for subsequent checks
        cursor.execute("PRAGMA table_info(Sessions)")
        columns = [row[1] for row in cursor.fetchall()]

    if 'app_name' not in columns:
        cursor.execute('ALTER TABLE Sessions ADD COLUMN app_name TEXT')
    if 'start_date' not in columns:
        cursor.execute('ALTER TABLE Sessions ADD COLUMN start_date DATETIME')
    if 'duration_seconds' not in columns:
        cursor.execute('ALTER TABLE Sessions ADD COLUMN duration_seconds INTEGER DEFAULT 0')
    if 'is_active' not in columns:
        cursor.execute('ALTER TABLE Sessions ADD COLUMN is_active BOOLEAN DEFAULT 1')

    # Reset any dangling active sessions from previous crashes
    cursor.execute('UPDATE Sessions SET is_active = 0 WHERE is_active = 1')
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
    app_name = app_name.lower()
    cursor.execute('DELETE FROM TrackedApps WHERE app_name = ?', (app_name,))
    # End any active sessions for this app
    cursor.execute('UPDATE Sessions SET is_active = 0 WHERE app_name = ? AND is_active = 1', (app_name,))
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

def start_session(app_name):
    conn = get_connection()
    cursor = conn.cursor()
    app_name = app_name.lower()
    now = datetime.datetime.now().isoformat()
    # End any existing active sessions for this app
    cursor.execute('UPDATE Sessions SET is_active = 0 WHERE app_name = ? AND is_active = 1', (app_name,))
    cursor.execute('INSERT INTO Sessions (app_name, start_date, duration_seconds, is_active) VALUES (?, ?, 0, 1)', (app_name, now))
    conn.commit()
    conn.close()

def update_session(app_name, duration_seconds):
    conn = get_connection()
    cursor = conn.cursor()
    app_name = app_name.lower()
    cursor.execute('SELECT id, duration_seconds FROM Sessions WHERE app_name = ? AND is_active = 1 ORDER BY id DESC LIMIT 1', (app_name,))
    row = cursor.fetchone()
    if row:
        new_duration = row[1] + duration_seconds
        cursor.execute('UPDATE Sessions SET duration_seconds = ? WHERE id = ?', (new_duration, row[0]))
    conn.commit()
    conn.close()

def end_session(app_name):
    conn = get_connection()
    cursor = conn.cursor()
    app_name = app_name.lower()
    cursor.execute('UPDATE Sessions SET is_active = 0 WHERE app_name = ? AND is_active = 1', (app_name,))
    conn.commit()
    conn.close()

def get_active_sessions():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT app_name, MAX(duration_seconds) FROM Sessions WHERE is_active = 1 GROUP BY app_name')
    data = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return data

def log_device_activity(duration_seconds):
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.date.today().isoformat()
    cursor.execute('''
        INSERT INTO DeviceActivity (log_date, duration_seconds) 
        VALUES (?, ?) 
        ON CONFLICT(log_date) DO UPDATE SET duration_seconds = duration_seconds + excluded.duration_seconds
    ''', (today, duration_seconds))
    conn.commit()
    conn.close()

def get_today_device_activity():
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.date.today().isoformat()
    cursor.execute('SELECT duration_seconds FROM DeviceActivity WHERE log_date = ?', (today,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0
