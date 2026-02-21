import sqlite3
from pathlib import Path
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_path="timeforge.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,   # allow background threads later
            isolation_level=None       # autocommit mode
        )
        self.conn.row_factory = sqlite3.Row
        self._configure()
        self._create_tables()

    # -----------------------------------
    # Configuration
    # -----------------------------------

    def _configure(self):
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")

    # -----------------------------------
    # Table Creation
    # -----------------------------------

    def _create_tables(self):
        try:
            self.conn.executescript("""
            DROP TABLE IF EXISTS usage_logs;
            DROP TABLE IF EXISTS tracked_apps;
            DROP TABLE IF EXISTS alerts;
            CREATE TABLE IF NOT EXISTS tracked_apps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_name TEXT UNIQUE NOT NULL,
                display_name TEXT,
                category TEXT CHECK(category IN ('productive','unproductive','neutral')) DEFAULT 'neutral',
                daily_limit_seconds INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                log_date TEXT NOT NULL,
                FOREIGN KEY(app_id) REFERENCES tracked_apps(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id INTEGER,
                alert_type TEXT,
                alert_time TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(app_id) REFERENCES tracked_apps(id)
            );
            """)
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")
            raise

    # -----------------------------------
    # App Management
    # -----------------------------------

    def add_app(self):
        try:
            process_name = input("Enter the process name (e.g., chrome.exe): ").strip().lower()
            if not process_name:
                raise ValueError("Process name cannot be empty")
            display_name = input("Enter a display name (optional): ").strip().lower() or process_name
            category = input("Enter a category (Productive, Unproductive, Neutral): ").strip().lower()
            if category not in ['productive', 'unproductive', 'neutral']:
                raise ValueError("Invalid category. Must be one of Productive, Unproductive, Neutral")
            set_daily_limit = input("Do you want to set a daily limit? (y/n): ").strip().lower()
            # Default daily limit to 0 to ensure the variable always exists
            daily_limit = 0
            if set_daily_limit == 'y':
                try:
                    daily_limit = int(input("Enter the daily limit (in seconds): "))
                    if daily_limit < 0:
                        raise ValueError("Daily limit cannot be negative")
                except ValueError:
                    print("Invalid input for daily limit. Defaulting to 0.")
                    daily_limit = 0
            self.conn.execute("""
                INSERT INTO tracked_apps (process_name, display_name, category, daily_limit_seconds)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(process_name) DO UPDATE SET
                    display_name=excluded.display_name,
                    category=excluded.category,
                    daily_limit_seconds=excluded.daily_limit_seconds,
                    is_active=1
            """, (process_name, display_name, category, daily_limit))
        except sqlite3.Error as e:
            print(f"Error adding app: {e}")
            raise

    def remove_app(self, process_name):
        self.conn.execute("""
            DELETE FROM tracked_apps WHERE process_name = ?
        """, (process_name,))

    def update_category(self, process_name, category):
        self.conn.execute("""
            UPDATE tracked_apps
            SET category = ?
            WHERE process_name = ?
        """, (category, process_name))

    def update_daily_limit(self, process_name, seconds):
        self.conn.execute("""
            UPDATE tracked_apps
            SET daily_limit_seconds = ?
            WHERE process_name = ?
        """, (seconds, process_name))

    def get_app(self, process_name):
        cur = self.conn.execute("""
            SELECT * FROM tracked_apps
            WHERE process_name = ?
        """, (process_name,))
        return cur.fetchone()

    def get_all_apps(self):
        return self.conn.execute("""
            SELECT * FROM tracked_apps
            WHERE is_active = 1
        """).fetchall()
        
    def list_tracked_apps(self):
        return self.conn.execute("""
            SELECT process_name, display_name, category, daily_limit_seconds
            FROM tracked_apps
            WHERE is_active = 1
        """).fetchall()

    # -----------------------------------
    # Usage Logging
    # -----------------------------------

    def log_usage(self, process_name, start_time, end_time):
        if start_time > end_time:
            raise ValueError("Start time cannot be after end time")        
        app = self.get_app(process_name)
        if not app:
            return

        duration = int((end_time - start_time).total_seconds())
        log_date = start_time.date().isoformat()

        self.conn.execute("""
            INSERT INTO usage_logs
            (app_id, start_time, end_time, duration_seconds, log_date)
            VALUES (?, ?, ?, ?, ?)
        """, (app['id'], start_time, end_time, duration, log_date))
