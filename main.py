# imports
from multiprocessing import process
import nt
from win32 import win32gui , win32process
import psutil

# get the current active process
pid = win32process.GetWindowThreadProcessId(win32gui.GetForegroundWindow())[1]
background_processes = []
tracked_processes = ["chrome.exe", "firefox.exe", "edge.exe", "opera.exe", "brave.exe", "vivaldi.exe", "safari.exe", "explorer.exe", "notepad.exe", "cmd.exe", "powershell.exe", "python.exe", "java.exe", "node.exe", "code.exe", "discord.exe", "spotify.exe", "slack.exe", "teams.exe", "zoom.exe", "skype.exe", "outlook.exe", "word.exe", "excel.exe", "powerpoint.exe"]
for proc in psutil.process_iter():
    if proc.pid != pid and proc.name() in tracked_processes and proc.name() not in background_processes:
        background_processes.append(proc.name())
        

print(f"Current active process: {psutil.Process(pid).name()}")
print(f"Background Processes: {background_processes}")
