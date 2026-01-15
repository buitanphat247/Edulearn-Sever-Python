"""
Cloudflare R2 Configuration
"""
import os

R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_ENDPOINT = os.getenv('R2_ENDPOINT')
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME')

def is_r2_configured() -> bool:
    """Kiểm tra xem R2 đã được cấu hình chưa"""
    return all([
        R2_ACCESS_KEY_ID,
        R2_SECRET_ACCESS_KEY,
        R2_ENDPOINT,
        R2_BUCKET_NAME
    ])

