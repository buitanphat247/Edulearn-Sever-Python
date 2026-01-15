import json

def load_config():
    try:
        with open("config/config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}

APP_CONFIG = load_config()
MAX_WORKERS = 50

