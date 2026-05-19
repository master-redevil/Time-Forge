import time
import psutil
import ctypes
import logging
import random
from ctypes import wintypes
from collections import OrderedDict
from PySide6.QtCore import QThread, Signal
import database
from config import config

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

_pid_name_cache = {}

def _get_process_name(pid):
    """Resolve a PID to a lowercase process name, with caching."""
    if pid in _pid_name_cache:
        return _pid_name_cache[pid]
    try:
        proc = psutil.Process(pid)
        name = proc.name().lower()
        _pid_name_cache[pid] = name
        return name
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

def get_foreground_app():
    """Returns the name of the single foreground window's process."""
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    pid = wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return _get_process_name(pid.value)

# Win32 constants for window enumeration
_GW_OWNER = 4
_GWL_EXSTYLE = -20
_WS_EX_TOOLWINDOW = 0x00000080
_WS_EX_NOACTIVATE = 0x08000000
_MONITOR_DEFAULTTONULL = 0

_IsWindowVisible = ctypes.windll.user32.IsWindowVisible
_GetWindow = ctypes.windll.user32.GetWindow
_GetWindowLongW = ctypes.windll.user32.GetWindowLongW
_MonitorFromWindow = ctypes.windll.user32.MonitorFromWindow
_GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId

# Callback type for EnumWindows
_WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

def _is_real_window(hwnd):
    """Check if a window is a real, user-visible app window (not a tooltip/tool window)."""
    if not _IsWindowVisible(hwnd):
        return False
    # Skip tool windows (floating palettes, etc.)
    ex_style = _GetWindowLongW(hwnd, _GWL_EXSTYLE)
    if ex_style & _WS_EX_TOOLWINDOW:
        return False
    if ex_style & _WS_EX_NOACTIVATE:
        return False
    # Skip windows that are owned by another window (child popups)
    if _GetWindow(hwnd, _GW_OWNER):
        return False
    # Must have a non-empty title
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return False
    return True

def get_visible_apps_per_monitor():
    """Returns a set of process names that are the topmost real window on each monitor.
    
    EnumWindows returns windows in z-order (topmost first), so the first real
    window we find per monitor handle is the topmost on that display.
    """
    # OrderedDict preserves insertion order (z-order). Key = monitor handle, value = pid
    monitor_top = OrderedDict()
    
    def enum_callback(hwnd, _lparam):
        if not _is_real_window(hwnd):
            return True  # continue enumeration
        
        hmon = _MonitorFromWindow(hwnd, _MONITOR_DEFAULTTONULL)
        if hmon and hmon not in monitor_top:
            pid = wintypes.DWORD()
            _GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            monitor_top[hmon] = pid.value
        
        return True  # continue enumeration
    
    ctypes.windll.user32.EnumWindows(_WNDENUMPROC(enum_callback), 0)
    
    # Resolve PIDs to process names
    result = set()
    for pid in monitor_top.values():
        name = _get_process_name(pid)
        if name:
            result.add(name)
    return result

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
                
                # Throttle full process scanning
                scan_interval = config.get("scan_interval", 30)
                if now - last_process_scan > scan_interval:
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
                idle_threshold = config.get("idle_threshold", 60)
                is_idle = idle_time > idle_threshold
                focused_app = get_foreground_app()
                
                # Get all topmost apps across every monitor
                visible_apps = get_visible_apps_per_monitor()
                # Always include the foreground app as a safety net
                if focused_app:
                    visible_apps.add(focused_app)
                    running_apps.add(focused_app)
                running_apps.update(visible_apps)

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
                        
                        # Log usage for ANY app visible on a monitor, not just the single foreground
                        if app in visible_apps and not is_idle:
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
        # Clear the PID cache on stop to avoid stale entries on restart
        _pid_name_cache.clear()
