# imports
from multiprocessing import process
from win32 import win32gui , win32process
import psutil

from core.tracker import list_running_processes , active_process_name 

tracked_processes = ["chrome.exe", "firefox.exe", "edge.exe", "opera.exe", "brave.exe", "vivaldi.exe", "safari.exe", "explorer.exe", "notepad.exe", "cmd.exe", "powershell.exe", "python.exe", "java.exe", "node.exe", "code.exe", "discord.exe", "spotify.exe", "slack.exe", "teams.exe", "zoom.exe", "skype.exe", "outlook.exe", "word.exe", "excel.exe", "powerpoint.exe"]

# Example usage:
apps = list_running_processes()

print(f"Current active process: {active_process_name}")
    
print("Running tracked applications:")
for app in apps:
    print(f"> Name: {app['Name']}, PID: {app['ProcessId']}")

