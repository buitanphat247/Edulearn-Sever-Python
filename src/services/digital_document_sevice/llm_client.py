from openai import OpenAI
from .config import APP_CONFIG
import os

try:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    
    client = OpenAI(api_key=api_key)
    AI_AVAILABLE = True
    print(f">> [INFO] Connected to OpenAI API (Key: ...{api_key[-4:]})")
except ImportError:
    client = None
    AI_AVAILABLE = False
    print("!! [CRITICAL] 'openai' library not installed.")
except Exception as e:
    client = None
    AI_AVAILABLE = False
    print(f"!! [CRITICAL] OpenAI Connection Failed: {e}")

