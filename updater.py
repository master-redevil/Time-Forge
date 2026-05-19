import urllib.request
import json
import logging
from PySide6.QtCore import QThread, Signal
from config import APP_VERSION, GITHUB_REPO

logger = logging.getLogger("TimeForge.Updater")

class UpdateChecker(QThread):
    update_available = Signal(str, str) # version, url

    def run(self):
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(url, headers={'User-Agent': 'TimeForge-App'})
            
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                
                latest_version = data.get('tag_name', '').lstrip('v')
                release_url = data.get('html_url', '')
                
                if self.is_newer(latest_version, APP_VERSION):
                    logger.info(f"New update found: {latest_version}")
                    self.update_available.emit(latest_version, release_url)
                else:
                    logger.info("App is up to date.")
                    
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")

    def is_newer(self, latest, current):
        try:
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]
            
            for i in range(max(len(latest_parts), len(current_parts))):
                l = latest_parts[i] if i < len(latest_parts) else 0
                c = current_parts[i] if i < len(current_parts) else 0
                if l > c:
                    return True
                elif l < c:
                    return False
            return False
        except ValueError:
            return False
