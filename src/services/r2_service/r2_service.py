import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import Optional, Tuple, Dict, List

def get_r2_client():
    """Tạo và trả về R2 client sử dụng boto3"""
    access_key_id = os.getenv('R2_ACCESS_KEY_ID')
    secret_access_key = os.getenv('R2_SECRET_ACCESS_KEY')
    endpoint_url = os.getenv('R2_ENDPOINT')
    bucket_name = os.getenv('R2_BUCKET_NAME')
    
    if not all([access_key_id, secret_access_key, endpoint_url, bucket_name]):
        return None, None
    
    config = Config(
        signature_version='s3v4',
        s3={
            'addressing_style': 'path'
        }
    )
    
    s3_client = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        config=config
    )
    
    return s3_client, bucket_name

def upload_file_to_r2(local_file_path: str, r2_key: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Upload file lên Cloudflare R2
    
    Args:
        local_file_path: Đường dẫn file local cần upload
        r2_key: Key (path) trên R2 để lưu file
        
    Returns:
        Tuple[str, None]: (r2_key, None) nếu thành công
        Tuple[None, str]: (None, error_message) nếu lỗi
    """
    try:
        s3_client, bucket_name = get_r2_client()
        if not s3_client:
            return None, 'R2 configuration not found. Please check environment variables.'
        
        if not os.path.exists(local_file_path):
            return None, f'Local file not found: {local_file_path}'
        
        s3_client.upload_file(local_file_path, bucket_name, r2_key)
        
        return r2_key, None
        
    except ClientError as e:
        return None, f'R2 upload error: {str(e)}'
    except Exception as e:
        return None, f'Unexpected error: {str(e)}'

def download_file_from_r2(r2_key: str, local_file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Download file từ Cloudflare R2
    
    Args:
        r2_key: Key (path) của file trên R2
        local_file_path: Đường dẫn local để lưu file
        
    Returns:
        Tuple[str, None]: (local_file_path, None) nếu thành công
        Tuple[None, str]: (None, error_message) nếu lỗi
    """
    try:
        s3_client, bucket_name = get_r2_client()
        if not s3_client:
            return None, 'R2 configuration not found. Please check environment variables.'
        
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
        
        s3_client.download_file(bucket_name, r2_key, local_file_path)
        
        return local_file_path, None
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == '404':
            return None, f'File not found on R2: {r2_key}'
        return None, f'R2 download error: {str(e)}'
    except Exception as e:
        return None, f'Unexpected error: {str(e)}'

def delete_file_from_r2(r2_key: str) -> Tuple[bool, Optional[str]]:
    """
    Xóa file từ Cloudflare R2
    
    Args:
        r2_key: Key (path) của file trên R2 cần xóa
        
    Returns:
        Tuple[bool, None]: (True, None) nếu thành công
        Tuple[False, str]: (False, error_message) nếu lỗi
    """
    try:
        s3_client, bucket_name = get_r2_client()
        if not s3_client:
            return False, 'R2 configuration not found. Please check environment variables.'
        
        s3_client.delete_object(Bucket=bucket_name, Key=r2_key)
        
        return True, None
        
    except ClientError as e:
        return False, f'R2 delete error: {str(e)}'
    except Exception as e:
        return False, f'Unexpected error: {str(e)}'

def get_file_url_from_r2(r2_key: str, expires_in: int = 3600) -> Tuple[Optional[str], Optional[str]]:
    """
    Lấy presigned URL để truy cập file trên R2
    
    Args:
        r2_key: Key (path) của file trên R2
        expires_in: Thời gian hết hạn URL (giây), mặc định 1 giờ
        
    Returns:
        Tuple[str, None]: (url, None) nếu thành công
        Tuple[None, str]: (None, error_message) nếu lỗi
    """
    try:
        s3_client, bucket_name = get_r2_client()
        if not s3_client:
            return None, 'R2 configuration not found. Please check environment variables.'
        
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': r2_key},
            ExpiresIn=expires_in
        )
        
        return url, None
        
    except ClientError as e:
        return None, f'R2 URL generation error: {str(e)}'
    except Exception as e:
        return None, f'Unexpected error: {str(e)}'

def list_files_in_r2(prefix: str = '') -> Tuple[Optional[List[Dict]], Optional[str]]:
    """
    Liệt kê các file trên R2 với prefix
    
    Args:
        prefix: Prefix để filter files (ví dụ: 'output_data/')
        
    Returns:
        Tuple[List[Dict], None]: (list of files, None) nếu thành công
        Tuple[None, str]: (None, error_message) nếu lỗi
    """
    try:
        s3_client, bucket_name = get_r2_client()
        if not s3_client:
            return None, 'R2 configuration not found. Please check environment variables.'
        
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        
        files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat() if 'LastModified' in obj else None
                })
        
        return files, None
        
    except ClientError as e:
        return None, f'R2 list error: {str(e)}'
    except Exception as e:
        return None, f'Unexpected error: {str(e)}'

