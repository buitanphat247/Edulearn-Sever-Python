# Cloudflare R2 Configuration

## Cấu hình R2

Tạo file `.env` trong thư mục root của project với nội dung sau:

```env
# ==========================================
# CLOUDFLARE R2 CONFIGURATION
# ==========================================
R2_ACCESS_KEY_ID=a7684a3235bf1f8e3870d82c6dc5ef69
R2_SECRET_ACCESS_KEY=a8bf552923ce489626300dc18fe320b3aebba50d52f1439599ce43f955395833
R2_ENDPOINT=https://7970c4a57482708b85fec0d3b79dba4d.r2.cloudflarestorage.com
R2_BUCKET_NAME=edu-learning-storage

# ==========================================
# APPLICATION CONFIGURATION
# ==========================================
PORT=5000
DEBUG=false
```

## Cài đặt dependencies

```bash
pip install -r requirements.txt
```

## Sử dụng R2 Service

```python
from src.services.r2_service import (
    upload_file_to_r2,
    download_file_from_r2,
    delete_file_from_r2,
    get_file_url_from_r2,
    list_files_in_r2
)

# Upload file
r2_key, error = upload_file_to_r2('local/file.txt', 'remote/path/file.txt')
if error:
    print(f"Error: {error}")
else:
    print(f"Uploaded to: {r2_key}")

# Download file
local_path, error = download_file_from_r2('remote/path/file.txt', 'local/downloaded.txt')
if error:
    print(f"Error: {error}")
else:
    print(f"Downloaded to: {local_path}")

# Get presigned URL
url, error = get_file_url_from_r2('remote/path/file.txt', expires_in=3600)
if error:
    print(f"Error: {error}")
else:
    print(f"URL: {url}")

# List files
files, error = list_files_in_r2('prefix/')
if error:
    print(f"Error: {error}")
else:
    for file in files:
        print(f"File: {file['key']}, Size: {file['size']}")
```

