import os
import json
import logging

logger = logging.getLogger("TimeForge.Config")

class Config:
    DEFAULT_CONFIG = {
        "poll_interval": 1,
        "idle_threshold": 60,
        "scan_interval": 30,
        "hotkey": "Ctrl+Shift+T",
        "data_retention_days": 90,
        "database_name": "usage.db"
    }

    def __init__(self):
        self.config_dir = os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'TimeForge')
        self.config_path = os.path.join(self.config_dir, 'config.json')
        self.data = self.DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    user_data = json.load(f)
                    # Merge user data with defaults to ensure all keys exist
                    self.data.update(user_data)
                logger.info("Configuration loaded from disk.")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        else:
            self.save() # Create default config file

    def save(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.data, f, indent=4)
            logger.info("Configuration saved to disk.")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

# Singleton instance
config = Config()
