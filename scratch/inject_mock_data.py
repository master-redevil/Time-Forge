import database
import datetime
import random

def inject_mock_data():
    database.init_db()
    
    # Track some apps if not already tracked
    apps = ['chrome.exe', 'code.exe', 'spotify.exe', 'discord.exe']
    for app in apps:
        database.add_tracked_app(app)
    
    # Inject data for the last 10 days
    today = datetime.date.today()
    for i in range(1, 11):
        date = (today - datetime.timedelta(days=i)).isoformat()
        
        # Log usage
        for app in apps:
            duration = random.randint(1800, 7200) # 30m to 2h
            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO UsageLogs (app_name, log_date, duration_seconds) VALUES (?, ?, ?)', 
                           (app, date, duration))
            
            # Add some sessions for the timeline
            num_sessions = random.randint(2, 5)
            for _ in range(num_sessions):
                start_hour = random.randint(8, 20)
                start_min = random.randint(0, 59)
                start_dt = f"{date}T{start_hour:02}:{start_min:02}:00"
                sess_duration = random.randint(600, 3600)
                cursor.execute('INSERT INTO Sessions (app_name, start_date, duration_seconds, is_active) VALUES (?, ?, ?, ?)',
                               (app, start_dt, sess_duration, 0))
            
            conn.commit()
            conn.close()
            
        # Log device activity
        total_activity = random.randint(10000, 20000)
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO DeviceActivity (log_date, duration_seconds) VALUES (?, ?)', 
                       (date, total_activity))
        conn.commit()
        conn.close()

    print("Mock data injected successfully.")

if __name__ == "__main__":
    inject_mock_data()
