import time
import psutil
from PySide6.QtCore import QThread, Signal
import database

class TrackerDaemon(QThread):
    # Signal emitted when database is updated, so the UI can refresh if open
    updated = Signal()

    def __init__(self, poll_interval=5):
        super().__init__()
        self.poll_interval = poll_interval
        self.running = True

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

            # Log usage for tracked apps that are currently running
            updated_any = False
            for app in tracked_apps:
                if app in running_apps:
                    database.log_usage(app, self.poll_interval)
                    updated_any = True
            
            if updated_any:
                self.updated.emit()
            
            time.sleep(self.poll_interval)

    def stop(self):
        self.running = False
        self.wait()
