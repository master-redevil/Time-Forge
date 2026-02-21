# imports
from core.tracker import list_running_processes , active_process_name 
from database.database_manager import DatabaseManager
import time

tracked_processes = ["chrome.exe", "firefox.exe", "edge.exe", "opera.exe", "brave.exe", "vivaldi.exe", "safari.exe", "explorer.exe", "notepad.exe", "cmd.exe", "powershell.exe", "python.exe", "java.exe", "node.exe", "code.exe", "discord.exe", "spotify.exe", "slack.exe", "teams.exe", "zoom.exe", "skype.exe", "outlook.exe", "word.exe", "excel.exe", "powerpoint.exe"]

# Example usage:
apps = list_running_processes()

print(f"Current active process: {active_process_name}")
    
print("Running tracked applications:")
for app in apps:
    print(f"> Name: {app['Name']}, PID: {app['ProcessId']}")
    
    
def test_database_integrity():
    """Test if the database is working as expected"""
    try:
        db = DatabaseManager()
        db.add_app("test_app")
        db.remove_app("test_app")
        print("Database integrity test passed")
    except Exception as e:
        print(f"Database integrity test failed: {e}")