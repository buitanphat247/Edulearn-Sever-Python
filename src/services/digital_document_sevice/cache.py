import os
import json

CACHE_FILE = "latex_cache.json"
LATEX_CACHE = {}

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                global LATEX_CACHE
                LATEX_CACHE = json.load(f)
                return LATEX_CACHE
        except: return {}
    return {}

def save_cache(cache=None):
    if cache is None: cache = LATEX_CACHE
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except: pass

