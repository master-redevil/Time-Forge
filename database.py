import sqlite3
import datetime
import os
import threading
from functools import wraps
from config import config

DB_DIR = os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'TimeForge')
DB_NAME = os.path.join(DB_DIR, config.get("database_name", "usage.db"))


db_lock = threading.RLock()

def with_db_lock(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with db_lock:
            return func(*args, **kwargs)
    return wrapper

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

@with_db_lock
def init_db():
    _migrate_existing_db()
    os.makedirs(DB_DIR, exist_ok=True)
    
    conn = get_connection()
    apply_migrations(conn)

def apply_migrations(conn):
    cursor = conn.cursor()
    
    # 1. Create SchemaVersion table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS SchemaVersion (
            version INTEGER PRIMARY KEY
        )
    ''')
    cursor.execute('SELECT version FROM SchemaVersion')
    row = cursor.fetchone()
    
    if row is None:
        # Infer version based on existing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='TrackedApps'")
        if cursor.fetchone():
            # DB exists. Let's check schema features to infer version.
            cursor.execute("PRAGMA table_info(TrackedApps)")
            tracked_cols = [c[1] for c in cursor.fetchall()]
            
            cursor.execute("PRAGMA table_info(Sessions)")
            session_cols = [c[1] for c in cursor.fetchall()]
            
            if 'exe_path' in tracked_cols and 'start_date' in session_cols and 'start_time' not in session_cols:
                current_version = 2
            else:
                current_version = 1
        else:
            # Brand new DB
            current_version = 0
            
        cursor.execute("INSERT INTO SchemaVersion (version) VALUES (?)", (current_version,))
    else:
        current_version = row[0]

    # Run migrations sequentially
    if current_version < 1:
        # v1: Initial schema
        cursor.execute('''
            CREATE TABLE TrackedApps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT UNIQUE NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE UsageLogs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                log_date DATE NOT NULL,
                duration_seconds INTEGER DEFAULT 0,
                UNIQUE(app_name, log_date)
            )
        ''')
        cursor.execute('''
            CREATE TABLE Sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT,
                start_date DATETIME,
                duration_seconds INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        cursor.execute('''
            CREATE TABLE DeviceActivity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_date DATE UNIQUE NOT NULL,
                duration_seconds INTEGER DEFAULT 0
            )
        ''')
        cursor.execute("UPDATE SchemaVersion SET version = 1")
        conn.commit()
        current_version = 1

    if current_version < 2:
        # v2: Add exe_path to TrackedApps and ensure Sessions schema is correct
        try:
            cursor.execute('ALTER TABLE TrackedApps ADD COLUMN exe_path TEXT')
        except sqlite3.OperationalError:
            pass # Ignore if already exists

        # Handle Sessions migration safely (avoiding DROP TABLE without backup)
        cursor.execute("PRAGMA table_info(Sessions)")
        columns = [c[1] for c in cursor.fetchall()]
        
        needs_session_migration = False
        if 'start_time' in columns or 'app_name' not in columns or 'start_date' not in columns:
            needs_session_migration = True

        if needs_session_migration:
            try:
                cursor.execute("ALTER TABLE Sessions RENAME TO Sessions_backup_v1")
            except sqlite3.OperationalError:
                # Fallback if backup table already exists
                cursor.execute("DROP TABLE IF EXISTS Sessions_backup_v1")
                cursor.execute("ALTER TABLE Sessions RENAME TO Sessions_backup_v1")

            cursor.execute('''
                CREATE TABLE Sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_name TEXT,
                    start_date DATETIME,
                    duration_seconds INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')

        # Reset any dangling active sessions from previous crashes
        cursor.execute('UPDATE Sessions SET is_active = 0 WHERE is_active = 1')
        
        cursor.execute("UPDATE SchemaVersion SET version = 2")
        conn.commit()
        current_version = 2

@with_db_lock
def rollback_migration(target_version):
    """Rolls back the database to a target schema version."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='SchemaVersion'")
    if not cursor.fetchone():
        return False
        
    cursor.execute('SELECT version FROM SchemaVersion')
    row = cursor.fetchone()
    if not row:
        return False
        
    current_version = row[0]
    
    if target_version >= current_version:
        return False # Nothing to roll back
        
    if current_version == 2 and target_version == 1:
        # Rollback v2 to v1
        # 1. Restore Sessions from backup if it exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Sessions_backup_v1'")
        if cursor.fetchone():
            cursor.execute("DROP TABLE Sessions")
            cursor.execute("ALTER TABLE Sessions_backup_v1 RENAME TO Sessions")
            
        cursor.execute("UPDATE SchemaVersion SET version = 1")
        conn.commit()
        
    return True

@with_db_lock
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

@with_db_lock
def get_tracked_apps():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT app_name FROM TrackedApps')
    apps = [row[0] for row in cursor.fetchall()]
    return apps

@with_db_lock
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

@with_db_lock
def update_app_path(app_name, exe_path):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE TrackedApps SET exe_path = ? WHERE app_name = ?', (exe_path, app_name.lower()))
    conn.commit()

@with_db_lock
def get_app_paths():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT app_name, exe_path FROM TrackedApps WHERE exe_path IS NOT NULL')
    paths = {row[0]: row[1] for row in cursor.fetchall()}
    return paths

@with_db_lock
def remove_tracked_app(app_name):
    conn = get_connection()
    cursor = conn.cursor()
    app_name = app_name.lower()
    cursor.execute('DELETE FROM TrackedApps WHERE app_name = ?', (app_name,))
    # End any active sessions for this app
    cursor.execute('UPDATE Sessions SET is_active = 0 WHERE app_name = ? AND is_active = 1', (app_name,))
    conn.commit()

@with_db_lock
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

@with_db_lock
def get_today_usage():
    return get_usage_for_date(datetime.date.today().isoformat())

@with_db_lock
def get_usage_for_date(date_str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT app_name, duration_seconds FROM UsageLogs WHERE log_date = ?', (date_str,))
    data = {row[0]: row[1] for row in cursor.fetchall()}
    return data

@with_db_lock
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

@with_db_lock
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

@with_db_lock
def start_session(app_name):
    conn = get_connection()
    cursor = conn.cursor()
    app_name = app_name.lower()
    now = datetime.datetime.now().isoformat()
    # End any existing active sessions for this app
    cursor.execute('UPDATE Sessions SET is_active = 0 WHERE app_name = ? AND is_active = 1', (app_name,))
    cursor.execute('INSERT INTO Sessions (app_name, start_date, duration_seconds, is_active) VALUES (?, ?, 0, 1)', (app_name, now))
    conn.commit()

@with_db_lock
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

@with_db_lock
def end_session(app_name):
    conn = get_connection()
    cursor = conn.cursor()
    app_name = app_name.lower()
    cursor.execute('UPDATE Sessions SET is_active = 0 WHERE app_name = ? AND is_active = 1', (app_name,))
    conn.commit()

@with_db_lock
def get_active_sessions():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT app_name, MAX(duration_seconds) FROM Sessions WHERE is_active = 1 GROUP BY app_name')
    data = {row[0]: row[1] for row in cursor.fetchall()}
    return data

@with_db_lock
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

@with_db_lock
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

@with_db_lock
def get_today_device_activity():
    return get_device_activity_for_date(datetime.date.today().isoformat())

@with_db_lock
def get_device_activity_for_date(date_str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT duration_seconds FROM DeviceActivity WHERE log_date = ?', (date_str,))
    row = cursor.fetchone()
    return row[0] if row else 0

@with_db_lock
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

@with_db_lock
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

@with_db_lock
def clear_all_data():
    """Deletes ALL data: usage logs, sessions, device activity, and tracked apps. Only preserves schema."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM UsageLogs')
        cursor.execute('DELETE FROM Sessions')
        cursor.execute('DELETE FROM DeviceActivity')
        cursor.execute('DELETE FROM TrackedApps')
        conn.commit()
        cursor.execute('VACUUM')
        return True
    except Exception as e:
        import logging
        logging.getLogger("TimeForge.Database").error(f"Clear all data failed: {e}")
        return False

@with_db_lock
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
