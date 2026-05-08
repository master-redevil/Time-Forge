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

_fg_cache = {"pid": None, "name": None}

def get_foreground_app():
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    pid = wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    
    # Simple PID cache to avoid expensive psutil object creation on every tick
    if pid.value == _fg_cache["pid"]:
        return _fg_cache["name"]
        
    try:
        proc = psutil.Process(pid.value)
        name = proc.name().lower()
        _fg_cache["pid"] = pid.value
        _fg_cache["name"] = name
        return name
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

class TrackerDaemon(QThread):
    # Signal emitted when database is updated, so the UI can refresh if open
    updated = Signal()
    idle_status_changed = Signal(bool)

    def __init__(self, poll_interval=1):
        super().__init__()
        self.poll_interval = poll_interval
        self.running = True
        self.active_apps = set()
        self.last_idle_state = None

    def run(self):
        last_process_scan = 0
        last_meta_refresh = 0
        running_apps = set()
        tracked_apps = set()
        app_paths = {}
        
        while self.running:
            now = time.time()
            
            # Refresh tracked apps and paths from DB every 10 seconds to save DB cycles
            if now - last_meta_refresh > 10:
                tracked_apps = set(database.get_tracked_apps())
                app_paths = database.get_app_paths()
                last_meta_refresh = now
            
            if not tracked_apps:
                time.sleep(self.poll_interval)
                continue
            
            # Throttle full process scanning to every 30 seconds
            # Background apps don't change state that often, and the focused app 
            # is tracked separately in the tick.
            if now - last_process_scan > 30:
                running_apps = set()
                # LAZY FETCH: only fetch names for the general scan
                for proc in psutil.process_iter(['name']):
                    try:
                        name = proc.info.get('name')
                        if name:
                            name_lower = name.lower()
                            running_apps.add(name_lower)
                            
                            # Only fetch expensive EXE path if app is tracked and we don't have it
                            if name_lower in tracked_apps and name_lower not in app_paths:
                                try:
                                    exe = proc.exe()
                                    if exe:
                                        database.update_app_path(name_lower, exe)
                                        app_paths[name_lower] = exe
                                except (psutil.AccessDenied, psutil.NoSuchProcess):
                                    pass
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
                last_process_scan = now

            idle_time = get_idle_time()
            is_idle = idle_time > 60
            focused_app = get_foreground_app()
            
            # Ensure the focused app is always considered 'running' to avoid 
            # session lag due to the 30s scan interval
            if focused_app:
                running_apps.add(focused_app)

            if is_idle != self.last_idle_state:
                self.idle_status_changed.emit(is_idle)
                self.last_idle_state = is_idle

            if not is_idle:
                database.log_device_activity(self.poll_interval)

            # Log usage only for the FOCUSED app if it's tracked
            updated_any = False
            
            # Manage sessions for all running tracked apps
            for app in tracked_apps:
                if app in running_apps:
                    if app not in self.active_apps:
                        database.start_session(app)
                        self.active_apps.add(app)
                    
                    # Only log usage/update session if it is the FOCUSED app and NOT IDLE
                    if app == focused_app and not is_idle:
                        database.log_usage(app, self.poll_interval)
                        database.update_session(app, self.poll_interval)
                        updated_any = True
                else:
                    if app in self.active_apps:
                        database.end_session(app)
                        self.active_apps.remove(app)
            
            if updated_any:
                self.updated.emit()
            
            time.sleep(self.poll_interval)

    def stop(self):
        self.running = False
        self.wait()
