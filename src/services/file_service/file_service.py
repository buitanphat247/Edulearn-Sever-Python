import os
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import send_file

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'doc', 'docx'}
DATA_SET_FOLDER = 'data_set'
DATA_SET_1 = 'data_set_1'
DATA_SET_2 = 'data_set_2'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Kiểm tra xem file có phải là file Word không"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_files_from_folder(folder_path):
    """Lấy danh sách file từ thư mục"""
    files = []
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path) and allowed_file(filename):
                file_stat = os.stat(file_path)
                file_path_url = file_path.replace('\\', '/')
                files.append({
                    'filename': filename,
                    'file_path': file_path_url,
                    'file_size': file_stat.st_size,
                    'created_at': datetime.fromtimestamp(file_stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                    'modified_at': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
    return files


def upload_file_service(file):
    """Xử lý logic upload file
    
    Args:
        file: File object từ request
        
    Returns:
        dict: Thông tin file đã upload hoặc None nếu có lỗi
        str: Error message nếu có lỗi
    """
    if not file or file.filename == '':
        return None, 'No file selected'
    
    if not allowed_file(file.filename):
        return None, 'File type not allowed. Only .doc and .docx files are allowed'
    
    original_filename = secure_filename(file.filename)
    name, ext = os.path.splitext(original_filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
    filename = f"{name}_{timestamp}{ext}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    try:
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        file_path_url = file_path.replace('\\', '/')
        
        return {
            'filename': filename,
            'file_path': file_path_url,
            'file_size': file_size
        }, None
    except Exception as e:
        return None, f'Error saving file: {str(e)}'


def get_datasets_service():
    """Lấy danh sách file từ cả 2 dataset
    
    Returns:
        dict: Dictionary chứa files từ data_set_1, data_set_2 và total_files
        str: Error message nếu có lỗi
    """
    try:
        dataset1_path = os.path.join(DATA_SET_FOLDER, DATA_SET_1)
        dataset2_path = os.path.join(DATA_SET_FOLDER, DATA_SET_2)
        
        files_dataset1 = get_files_from_folder(dataset1_path)
        files_dataset2 = get_files_from_folder(dataset2_path)
        
        total_files = len(files_dataset1) + len(files_dataset2)
        
        return {
            'data_set_1': files_dataset1,
            'data_set_2': files_dataset2,
            'total_files': total_files
        }, None
    except Exception as e:
        return None, f'Error getting files: {str(e)}'


def download_file_service(filepath):
    """Xử lý logic download file từ data_set
    
    Args:
        filepath: Đường dẫn file (có thể có hoặc không có 'data_set/' ở đầu)
        
    Returns:
        str: Đường dẫn file đầy đủ để download
        str: Error message nếu có lỗi
    """
    if filepath.startswith('data_set/'):
        filepath = filepath.replace('data_set/', '', 1)
    
    path_parts = filepath.split('/')
    
    if len(path_parts) < 2:
        return None, 'Invalid file path. Format: data_set_1/filename.docx or data_set_2/filename.docx'
    
    folder = path_parts[0]
    filename = '/'.join(path_parts[1:])
    
    if folder not in [DATA_SET_1, DATA_SET_2]:
        return None, f'Invalid dataset folder. Only {DATA_SET_1} and {DATA_SET_2} are allowed'
    
    if not allowed_file(filename):
        return None, 'File type not allowed. Only .doc and .docx files are allowed'
    
    folder_path = os.path.join(DATA_SET_FOLDER, folder)
    file_path = os.path.join(folder_path, filename)
    
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return None, 'File not found'
    
    return file_path, None

