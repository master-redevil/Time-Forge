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

            # Gather names of all currently running processes
            running_apps = set()
            for proc in psutil.process_iter(['name']):
                try:
                    name = proc.info['name']
                    if name:
                        running_apps.add(name.lower())
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
