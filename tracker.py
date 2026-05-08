import time
import psutil
import ctypes
import logging
import random
from ctypes import wintypes
from PySide6.QtCore import QThread, Signal
import database

logger = logging.getLogger("TimeForge.Tracker")

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
    # Signal emitted when database is updated, passing the focused app name
    updated = Signal(str)
    idle_status_changed = Signal(bool)
    error_occurred = Signal(str)

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
        
        retry_delay = 1
        max_retry_delay = 60
        
        while self.running:
            try:
                now = time.time()
                
                # Refresh tracked apps and paths from DB every 10 seconds to save DB cycles
                if now - last_meta_refresh > 10:
                    tracked_apps = set(database.get_tracked_apps())
                    app_paths = database.get_app_paths()
                    last_meta_refresh = now
                
                if not tracked_apps:
                    time.sleep(self.poll_interval)
                    # Reset retry delay on successful wait (idle)
                    retry_delay = 1
                    continue
                
                # Throttle full process scanning to every 30 seconds
                if now - last_process_scan > 30:
                    running_apps = set()
                    for proc in psutil.process_iter(['name']):
                        try:
                            name = proc.info.get('name')
                            if name:
                                name_lower = name.lower()
                                running_apps.add(name_lower)
                                
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
                
                if focused_app:
                    running_apps.add(focused_app)

                if is_idle != self.last_idle_state:
                    self.idle_status_changed.emit(is_idle)
                    self.last_idle_state = is_idle

                if not is_idle:
                    database.log_device_activity(self.poll_interval)

                for app in tracked_apps:
                    if app in running_apps:
                        if app not in self.active_apps:
                            database.start_session(app)
                            self.active_apps.add(app)
                        
                        if app == focused_app and not is_idle:
                            database.log_usage(app, self.poll_interval)
                            database.update_session(app, self.poll_interval)
                    else:
                        if app in self.active_apps:
                            database.end_session(app)
                            self.active_apps.remove(app)
                
                self.updated.emit(focused_app or "")
                
                # Reset retry delay on successful iteration
                retry_delay = 1
                time.sleep(self.poll_interval)
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Tracker error: {error_msg}", exc_info=True)
                self.error_occurred.emit(error_msg)
                
                # Exponential backoff with jitter
                sleep_time = retry_delay + (random.random() * 0.1 * retry_delay)
                logger.info(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
                
                retry_delay = min(retry_delay * 2, max_retry_delay)

    def stop(self):
        self.running = False
        self.wait()
