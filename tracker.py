import time
import psutil
import ctypes
from ctypes import wintypes
from PySide6.QtCore import QThread, Signal
import database

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.UINT),
        ('dwTime', wintypes.DWORD),
    ]

def get_idle_time():
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
    return 0.0

class TrackerDaemon(QThread):
    # Signal emitted when database is updated, so the UI can refresh if open
    updated = Signal()
    idle_status_changed = Signal(bool)

    def __init__(self, poll_interval=5):
        super().__init__()
        self.poll_interval = poll_interval
        self.running = True
        self.active_apps = set()
        self.last_idle_state = None

    def run(self):
        while self.running:
            tracked_apps = set(database.get_tracked_apps())
            if not tracked_apps:
                time.sleep(self.poll_interval)
                continue
                
            app_paths = database.get_app_paths()

            # Gather names of all currently running processes
            running_apps = set()
            for proc in psutil.process_iter(['name', 'exe']):
                try:
                    name = proc.info.get('name')
                    exe = proc.info.get('exe')
                    if name:
                        name_lower = name.lower()
                        running_apps.add(name_lower)
                        if name_lower in tracked_apps and exe and name_lower not in app_paths:
                            database.update_app_path(name_lower, exe)
                            app_paths[name_lower] = exe
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

            idle_time = get_idle_time()
            is_idle = idle_time > 60

            if is_idle != self.last_idle_state:
                self.idle_status_changed.emit(is_idle)
                self.last_idle_state = is_idle

            # Log usage for tracked apps that are currently running
            updated_any = False
            for app in tracked_apps:
                if app in running_apps:
                    if app not in self.active_apps:
                        # New session started
                        database.start_session(app)
                        self.active_apps.add(app)
                    
                    if not is_idle:
                        database.log_usage(app, self.poll_interval)
                        database.update_session(app, self.poll_interval)
                        updated_any = True
                else:
                    if app in self.active_apps:
                        # Session ended
                        database.end_session(app)
                        self.active_apps.remove(app)
            
            if updated_any:
                self.updated.emit()
            
            time.sleep(self.poll_interval)

    def stop(self):
        self.running = False
        self.wait()
