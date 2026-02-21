# from datetime import datetime

# from core.tracker import list_running_processes, active_process_name
# from database.database_manager import DatabaseManager

# db = DatabaseManager()

#!/usr/bin/env python3
from datetime import datetime
from database.database_manager import DatabaseManager

db = DatabaseManager()

def print_apps():
    apps = db.get_all_apps()
    if not apps:
        print("No tracked apps.")
        return
    print("Tracked applications:")
    for app in apps:
        print(
            f"> Name: {app['process_name']}, Display Name: {app['display_name']}, "
            f"Category: {app['category']}, Daily Limit: {app['daily_limit_seconds']} seconds"
        )

def print_logs(limit=10):
    rows = db.conn.execute("""
        SELECT l.id, a.process_name AS app_name, a.display_name, l.start_time, l.end_time, l.duration_seconds, l.log_date
        FROM usage_logs l
        JOIN tracked_apps a ON l.app_id = a.id
        ORDER BY l.start_time DESC
        LIMIT ?
    """, (limit,)).fetchall()
    print("Recent logs:")
    if not rows:
        print("  (no logs yet)")
        return
    for r in rows:
        print(f"  {r['log_date']} | {r['app_name']} ({r['display_name']}) - {r['duration_seconds']}s | {r['start_time']} -> {r['end_time']}")

def cli_loop():
    print("Time Forge CLI. Type 'help' for commands.")
    while True:
        try:
            cmd = input("timeforge> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not cmd:
            continue
        parts = cmd.split()
        command = parts[0].lower()
        if command in ("exit","quit"):
            print("Exiting Time Forge CLI.")
            break
        if command == "help":
            print("Commands: add | list | logs | lognow <process> | help | exit")
            continue
        if command == "add":
            db.add_app()
        elif command in ("list","ls"):
            print_apps()
        elif command == "logs":
            print_logs(20)
        elif command == "lognow":
            if len(parts) >= 2:
                proc = parts[1]
                now = datetime.now()
                db.log_usage(proc, now, now)
            else:
                print("Usage: lognow <process_name>")
        elif command == "list":
            apps = db.list_tracked_apps()
            if not apps:
                print("No tracked apps.")
            else:
                print("Tracked applications:")
                for app in apps:
                    print(f"  {app['process_name']} ({app['display_name']}) - Category: {app['category']}, Daily Limit: {app['daily_limit_seconds']} seconds")
        else:
            print("Unknown command. Type 'help' for options.")
        print_logs(5)

if __name__ == "__main__":
    print("Launching Time Forge CLI...")
    print_apps()
    cli_loop()

