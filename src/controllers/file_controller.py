from flask import Blueprint, jsonify, request, send_file
import os
from src.services.file_service import (
    upload_file_service,
    get_datasets_service,
    download_file_service
)

file_controller = Blueprint('file_controller', __name__)

@file_controller.route('/upload', methods=['POST'])
def upload_file():
    """Upload file Word
---
tags:
  - File
summary: Upload file Word (doc, docx)
description: Upload file Word lên server, chỉ chấp nhận file .doc và .docx
consumes:
  - multipart/form-data
parameters:
  - in: formData
    name: file
    type: file
    required: true
    description: File Word cần upload (.doc hoặc .docx)
responses:
  200:
    description: Upload thành công
    schema:
      type: object
      properties:
        message:
          type: string
          example: File uploaded successfully
        filename:
          type: string
          example: document.docx
        file_path:
          type: string
          example: uploads/document.docx
        file_size:
          type: integer
          example: 12345
  400:
    description: Lỗi validation
    schema:
      type: object
      properties:
        error:
          type: string
          example: No file provided hoặc File type not allowed
  500:
    description: Lỗi server
    schema:
      type: object
      properties:
        error:
          type: string
          example: Error uploading file
"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        result, error = upload_file_service(file)
        
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'message': 'File uploaded successfully',
            **result
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error uploading file: {str(e)}'}), 500

@file_controller.route('/datasets', methods=['GET'])
def get_datasets():
    """Lấy danh sách tất cả file trong các dataset
---
tags:
  - File
summary: Lấy danh sách file trong data_set_1 và data_set_2
description: Trả về danh sách tất cả file Word trong cả 2 dataset
responses:
  200:
    description: Thành công
    schema:
      type: object
      properties:
        data_set_1:
          type: array
          items:
            type: object
            properties:
              filename:
                type: string
                example: 2025_toan_hoc.docx
              file_path:
                type: string
                example: data_set/data_set_1/2025_toan_hoc.docx
              file_size:
                type: integer
                example: 12345
              created_at:
                type: string
                example: 2024-12-25 14:30:25
              modified_at:
                type: string
                example: 2024-12-25 14:30:25
        data_set_2:
          type: array
          items:
            type: object
            properties:
              filename:
                type: string
                example: toan_hoc.docx
              file_path:
                type: string
                example: data_set/data_set_2/toan_hoc.docx
              file_size:
                type: integer
                example: 12345
              created_at:
                type: string
                example: 2024-12-25 14:30:25
              modified_at:
                type: string
                example: 2024-12-25 14:30:25
        total_files:
          type: integer
          example: 17
  500:
    description: Lỗi server
    schema:
      type: object
      properties:
        error:
          type: string
          example: Error getting files
"""
    try:
        result, error = get_datasets_service()
        
        if error:
            return jsonify({'error': error}), 500
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': f'Error getting files: {str(e)}'}), 500

@file_controller.route('/download/<path:filepath>', methods=['GET'])
def download_file(filepath):
    """Tải file từ data_set
---
tags:
  - File
summary: Tải file từ data_set về máy
description: Cho phép người dùng tải file Word từ data_set_1 hoặc data_set_2 về máy
parameters:
  - in: path
    name: filepath
    type: string
    required: true
    description: "Đường dẫn file (ví dụ: data_set_1/2025_cong_nghe_nn.docx hoặc data_set_2/toan_hoc.docx). Có thể có hoặc không có 'data_set/' ở đầu"
responses:
  200:
    description: File được tải về thành công
    schema:
      type: file
  400:
    description: Đường dẫn file không hợp lệ
    schema:
      type: object
      properties:
        error:
          type: string
          example: Invalid file path
  404:
    description: File không tồn tại
    schema:
      type: object
      properties:
        error:
          type: string
          example: File not found
  500:
    description: Lỗi server
    schema:
      type: object
      properties:
        error:
          type: string
          example: Error downloading file
"""
    try:
        file_path, error = download_file_service(filepath)
        
        if error:
            status_code = 404 if 'not found' in error.lower() else 400
            return jsonify({'error': error}), status_code
        
        download_filename = os.path.basename(file_path)
        return send_file(
            file_path,
            as_attachment=True,
            download_name=download_filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
    except Exception as e:
        return jsonify({'error': f'Error downloading file: {str(e)}'}), 500

