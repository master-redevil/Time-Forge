import sqlite3
import datetime
import os
import threading
from config import config

DB_DIR = os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'TimeForge')
DB_NAME = os.path.join(DB_DIR, config.get("database_name", "usage.db"))

def _migrate_existing_db():
    """Moves usage.db from the current directory to the app data directory if it exists."""
    legacy_path = "usage.db"
    if os.path.exists(legacy_path) and not os.path.exists(DB_NAME):
        os.makedirs(DB_DIR, exist_ok=True)
        try:
            import shutil
            shutil.move(legacy_path, DB_NAME)
            print(f"Migrated database from {legacy_path} to {DB_NAME}")
        except Exception as e:
            print(f"Failed to migrate database: {e}")

# Thread-local storage for database connections to avoid overhead
_local = threading.local()

def get_connection():
    # Return existing connection for this thread if available
    if hasattr(_local, "conn") and _local.conn is not None:
        return _local.conn
        
    # Create new connection for this thread
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    
    # Enable WAL (Write-Ahead Logging) for concurrent access and better performance
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-8000") # 8MB cache
    
    _local.conn = conn
    return conn

def init_db():
    _migrate_existing_db()
    os.makedirs(DB_DIR, exist_ok=True)
    
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

def cleanup_old_data():
    """Removes records older than the configured retention period."""
    retention_days = config.get("data_retention_days", 90)
    cutoff_date = (datetime.date.today() - datetime.timedelta(days=retention_days)).isoformat()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Delete from UsageLogs
        cursor.execute('DELETE FROM UsageLogs WHERE log_date < ?', (cutoff_date,))
        usage_deleted = cursor.rowcount
        
        # Delete from Sessions (start_date is isoformat but we can use date() function in SQL)
        cursor.execute('DELETE FROM Sessions WHERE date(start_date) < ?', (cutoff_date,))
        sessions_deleted = cursor.rowcount
        
        # Delete from DeviceActivity
        cursor.execute('DELETE FROM DeviceActivity WHERE log_date < ?', (cutoff_date,))
        activity_deleted = cursor.rowcount
        
        conn.commit()
        
        # Reclaim space
        cursor.execute('VACUUM')
        
        import logging
        logger = logging.getLogger("TimeForge.Database")
        logger.info(f"Cleanup completed. Deleted {usage_deleted} usage logs, {sessions_deleted} sessions, and {activity_deleted} activity records.")
        return True
    except Exception as e:
        import logging
        logger = logging.getLogger("TimeForge.Database")
        logger.error(f"Cleanup failed: {e}")
        return False

def get_db_size():
    """Returns the database file size in bytes."""
    if os.path.exists(DB_NAME):
        return os.path.getsize(DB_NAME)
    return 0

def get_tracked_apps():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT app_name FROM TrackedApps')
    apps = [row[0] for row in cursor.fetchall()]
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

def update_app_path(app_name, exe_path):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE TrackedApps SET exe_path = ? WHERE app_name = ?', (exe_path, app_name.lower()))
    conn.commit()

def get_app_paths():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT app_name, exe_path FROM TrackedApps WHERE exe_path IS NOT NULL')
    paths = {row[0]: row[1] for row in cursor.fetchall()}
    return paths

def remove_tracked_app(app_name):
    conn = get_connection()
    cursor = conn.cursor()
    app_name = app_name.lower()
    cursor.execute('DELETE FROM TrackedApps WHERE app_name = ?', (app_name,))
    # End any active sessions for this app
    cursor.execute('UPDATE Sessions SET is_active = 0 WHERE app_name = ? AND is_active = 1', (app_name,))
    conn.commit()

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

def get_today_usage():
    return get_usage_for_date(datetime.date.today().isoformat())

def get_usage_for_date(date_str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT app_name, duration_seconds FROM UsageLogs WHERE log_date = ?', (date_str,))
    data = {row[0]: row[1] for row in cursor.fetchall()}
    return data

def get_usage_history(days=7):
    conn = get_connection()
    cursor = conn.cursor()
    start_date = (datetime.date.today() - datetime.timedelta(days=days-1)).isoformat()
    cursor.execute('''
        SELECT log_date, SUM(duration_seconds) 
        FROM UsageLogs 
        WHERE log_date >= ? 
        GROUP BY log_date 
        ORDER BY log_date ASC
    ''', (start_date,))
    data = {row[0]: row[1] for row in cursor.fetchall()}
    return data

def get_app_usage_history(app_name, days=7):
    conn = get_connection()
    cursor = conn.cursor()
    start_date = (datetime.date.today() - datetime.timedelta(days=days-1)).isoformat()
    cursor.execute('''
        SELECT log_date, duration_seconds 
        FROM UsageLogs 
        WHERE app_name = ? AND log_date >= ? 
        ORDER BY log_date ASC
    ''', (app_name.lower(), start_date))
    data = {row[0]: row[1] for row in cursor.fetchall()}
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

def end_session(app_name):
    conn = get_connection()
    cursor = conn.cursor()
    app_name = app_name.lower()
    cursor.execute('UPDATE Sessions SET is_active = 0 WHERE app_name = ? AND is_active = 1', (app_name,))
    conn.commit()

def get_active_sessions():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT app_name, MAX(duration_seconds) FROM Sessions WHERE is_active = 1 GROUP BY app_name')
    data = {row[0]: row[1] for row in cursor.fetchall()}
    return data

def get_sessions_for_date(date_str):
    conn = get_connection()
    cursor = conn.cursor()
    # We look for sessions that started on this date
    # In a more advanced version, we'd look for sessions overlapping the date
    cursor.execute('''
        SELECT app_name, start_date, duration_seconds 
        FROM Sessions 
        WHERE date(start_date) = ? 
        ORDER BY start_date ASC
    ''', (date_str,))
    data = [{'app': row[0], 'start': row[1], 'duration': row[2]} for row in cursor.fetchall()]
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

def get_today_device_activity():
    return get_device_activity_for_date(datetime.date.today().isoformat())

def get_device_activity_for_date(date_str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT duration_seconds FROM DeviceActivity WHERE log_date = ?', (date_str,))
    row = cursor.fetchone()
    return row[0] if row else 0

def get_device_activity_history(days=7):
    conn = get_connection()
    cursor = conn.cursor()
    start_date = (datetime.date.today() - datetime.timedelta(days=days-1)).isoformat()
    cursor.execute('''
        SELECT log_date, duration_seconds 
        FROM DeviceActivity 
        WHERE log_date >= ? 
        ORDER BY log_date ASC
    ''', (start_date,))
    data = {row[0]: row[1] for row in cursor.fetchall()}
    return data

def get_sessions_range(start_date, end_date):
    """Returns all session records between two dates (inclusive)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT app_name, start_date, duration_seconds 
        FROM Sessions 
        WHERE date(start_date) >= ? AND date(start_date) <= ?
        ORDER BY start_date ASC
    ''', (start_date, end_date))
    data = [{'app': row[0], 'start': row[1], 'duration': row[2]} for row in cursor.fetchall()]
    return data

def get_usage_range(start_date, end_date):
    """Returns daily usage summaries per app between two dates (inclusive)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT log_date, app_name, duration_seconds 
        FROM UsageLogs 
        WHERE log_date >= ? AND log_date <= ?
        ORDER BY log_date ASC, duration_seconds DESC
    ''', (start_date, end_date))
    data = [{'date': row[0], 'app': row[1], 'duration': row[2]} for row in cursor.fetchall()]
    return data
