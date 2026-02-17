import win32com.client
from win32 import win32gui
from win32 import win32process
import psutil

pid = win32process.GetWindowThreadProcessId(win32gui.GetForegroundWindow())[1]

active_process_name = psutil.Process(pid).name()


def list_running_processes():
    # Connect to the WMI service
    wmi = win32com.client.GetObject('winmgmts:')
    # Query for all instances of Win32_Process
    processes = wmi.InstancesOf('Win32_Process')
    tracked_apps = ["chrome.exe", "firefox.exe", "edge.exe", "opera.exe", "brave.exe", "vivaldi.exe", "safari.exe", "explorer.exe", "notepad.exe", "cmd.exe", "powershell.exe", "python.exe", "java.exe", "node.exe", "code.exe", "discord.exe", "spotify.exe", "slack.exe", "teams.exe", "zoom.exe", "skype.exe", "outlook.exe", "word.exe", "excel.exe", "powerpoint.exe"]
    running_apps = []
    for p in processes:
        # You can access properties like Name, ProcessId, etc.
        if p.Name in tracked_apps and p.ProcessId != pid and p.Name not in [app['Name'] for app in running_apps]:  # Exclude the current active process and already added apps
            running_apps.append({'Name': p.Name, 'ProcessId': p.ProcessId})
    return running_apps