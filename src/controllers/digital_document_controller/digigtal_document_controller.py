from flask import Blueprint, jsonify, request, send_file
import os
import shutil
import sys
import json
import re
from datetime import datetime
from werkzeug.utils import secure_filename

from src.services.digital_document_sevice import cache
from src.services.digital_document_sevice import converter
from src.services.digital_document_sevice import ocr
from src.services.digital_document_sevice import tables
from src.services.digital_document_sevice import formatter
from src.services.digital_document_sevice import json_parser
from src.services.digital_document_sevice import post_process
from src.services.digital_document_sevice import html_generator
from src.services.digital_document_sevice import utils
from src.services.r2_service import upload_file_to_r2

digital_document_controller = Blueprint('digital_document_controller', __name__)

OUTPUT_BASE_FOLDER = 'output_data'

def extract_and_separate_pictures(questions_data):
    """
    Tách hình ảnh ra khỏi question/answer text và thêm vào trường picture riêng
    
    Args:
        questions_data: Dữ liệu câu hỏi (list of sections) - sẽ được modify in-place
        
    Returns:
        list: Danh sách tất cả các LaTeX code của hình ảnh (unique)
    """
    pictures = []
    picture_pattern = r'\\includegraphics(?:\[[^\]]*\])?\{[^}]+\}'
    
    if not questions_data:
        return pictures
    
    # Duyệt qua các section
    for section in questions_data:
        if not isinstance(section, dict) or 'questions' not in section:
            continue
            
        # Duyệt qua các câu hỏi
        for question in section.get('questions', []):
            # Xử lý question text
            question_text = question.get('question', '')
            if question_text:
                matches = re.findall(picture_pattern, question_text)
                if matches:
                    # Lấy hình ảnh đầu tiên (thường chỉ có 1 hình trong question)
                    question['picture'] = matches[0]
                    pictures.append(matches[0])
                    
                    # Xóa hình ảnh khỏi question text
                    for pic in matches:
                        # Xóa hình ảnh và các newline xung quanh
                        question_text = re.sub(r'\s*' + re.escape(pic) + r'\s*', ' ', question_text)
                    # Xóa các khoảng trắng và newline thừa
                    question_text = re.sub(r'\s+', ' ', question_text)  # Nhiều khoảng trắng thành 1
                    question_text = re.sub(r'\n\s*\n', '\n', question_text)  # Nhiều newline thành 1
                    question_text = question_text.strip()
                    question['question'] = question_text
            
            # Xử lý answers (nếu có hình ảnh trong answer)
            answers = question.get('answers', [])
            for answer in answers:
                answer_content = answer.get('content', '')
                if answer_content:
                    matches = re.findall(picture_pattern, answer_content)
                    if matches:
                        # Lấy hình ảnh đầu tiên
                        answer['picture'] = matches[0]
                        pictures.append(matches[0])
                        
                        # Xóa hình ảnh khỏi answer content
                        for pic in matches:
                            # Xóa hình ảnh và các newline xung quanh
                            answer_content = re.sub(r'\s*' + re.escape(pic) + r'\s*', ' ', answer_content)
                        # Xóa các khoảng trắng và newline thừa
                        answer_content = re.sub(r'\s+', ' ', answer_content)
                        answer_content = re.sub(r'\n\s*\n', '\n', answer_content)
                        answer_content = answer_content.strip()
                        answer['content'] = answer_content
    
    # Loại bỏ duplicates và giữ nguyên thứ tự
    seen = set()
    unique_pictures = []
    for pic in pictures:
        if pic not in seen:
            seen.add(pic)
            unique_pictures.append(pic)
    
    return unique_pictures

def extract_image_path_from_latex(latex_code):
    """
    Trích xuất đường dẫn file từ LaTeX includegraphics
    
    Args:
        latex_code: LaTeX code như "\\includegraphics[...]{media/image48.jpeg}"
        
    Returns:
        str: Đường dẫn file (ví dụ: "media/image48.jpeg") hoặc None
    """
    pattern = r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}'
    match = re.search(pattern, latex_code)
    if match:
        return match.group(1)
    return None

def upload_pictures_to_r2(questions_data, folder_path_out):
    """
    Upload các hình ảnh lên R2 và thay thế picture field bằng URL
    
    Args:
        questions_data: Dữ liệu câu hỏi (sẽ được modify in-place)
        folder_path_out: Thư mục output chứa media folder
        
    Returns:
        int: Số lượng hình ảnh đã upload thành công
    """
    uploaded_count = 0
    R2_PUBLIC_URL = "https://pub-3aaf3c9cd7694383ab5e47980be6dc67.r2.dev"
    
    if not questions_data:
        return uploaded_count
    
    # Duyệt qua các section
    for section in questions_data:
        if not isinstance(section, dict) or 'questions' not in section:
            continue
            
        # Duyệt qua các câu hỏi
        for question in section.get('questions', []):
            # Xử lý picture trong question
            if 'picture' in question and question['picture']:
                latex_code = question['picture']
                image_path = extract_image_path_from_latex(latex_code)
                
                if image_path:
                    # Tạo đường dẫn file local
                    local_file_path = os.path.join(folder_path_out, image_path)
                    
                    if os.path.exists(local_file_path) and os.path.isfile(local_file_path):
                        # Tạo tên file mới với timestamp
                        original_filename = os.path.basename(image_path)
                        name, ext = os.path.splitext(original_filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                        new_filename = f"{timestamp}{ext}"
                        
                        # Tạo R2 key: image-maths/{new_filename}
                        r2_key = f"image-maths/{new_filename}"
                        
                        # Upload lên R2
                        uploaded_key, error = upload_file_to_r2(local_file_path, r2_key)
                        
                        if not error and uploaded_key:
                            # Tạo URL từ public URL + path
                            image_path = f"/image-maths/{new_filename}"
                            full_url = f"{R2_PUBLIC_URL}{image_path}"
                            question['picture'] = full_url
                            uploaded_count += 1
                        else:
                            # Nếu upload thất bại, giữ nguyên LaTeX code
                            pass
            
            # Xử lý picture trong answers
            answers = question.get('answers', [])
            for answer in answers:
                if 'picture' in answer and answer['picture']:
                    latex_code = answer['picture']
                    image_path = extract_image_path_from_latex(latex_code)
                    
                    if image_path:
                        local_file_path = os.path.join(folder_path_out, image_path)
                        
                        if os.path.exists(local_file_path) and os.path.isfile(local_file_path):
                            # Tạo tên file mới với timestamp
                            original_filename = os.path.basename(image_path)
                            name, ext = os.path.splitext(original_filename)
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                            new_filename = f"{timestamp}{ext}"
                            
                            # Tạo R2 key: image-maths/{new_filename}
                            r2_key = f"image-maths/{new_filename}"
                            
                            # Upload lên R2
                            uploaded_key, error = upload_file_to_r2(local_file_path, r2_key)
                            
                            if not error and uploaded_key:
                                # Tạo URL từ public URL + path
                                image_path = f"/image-maths/{new_filename}"
                                full_url = f"{R2_PUBLIC_URL}{image_path}"
                                answer['picture'] = full_url
                                uploaded_count += 1
    
    return uploaded_count

def process_document(file_path_in, folder_path_out):
    """Xử lý tài liệu số hóa
    
    Args:
        file_path_in: Đường dẫn file Word đầu vào
        folder_path_out: Thư mục output
        
    Returns:
        dict: Kết quả xử lý với các đường dẫn file
        str: Error message nếu có lỗi
    """
    try:
        if not os.path.exists(file_path_in):
            return None, 'File not found'
        
        cache.load_cache()
        
        if cache.LATEX_CACHE:
            for k, v in cache.LATEX_CACHE.items():
                cache.LATEX_CACHE[k] = utils.clean_latex_response(v)
        
        if os.path.exists(folder_path_out):
            try:
                shutil.rmtree(folder_path_out)
            except:
                pass
        
        if not os.path.exists(folder_path_out):
            os.makedirs(folder_path_out)
        
        latex_content = converter.convert_docx_to_latex(file_path_in, folder_path_out)
        if not latex_content:
            return None, 'Failed to convert document to LaTeX'
        
        latex_content = ocr.process_latex_images(latex_content, folder_path_out)
        latex_content = tables.process_latex_tables(latex_content)
        formatted_content = formatter.format_latex_content(latex_content)
        
        parser = json_parser.LatexToJsonParser(folder_path_out)
        json_path = parser.run(formatted_content)
        
        json_file_path = os.path.join(folder_path_out, "questions.json")
        post_process.process_file(json_file_path)
        
        # Load QUESTIONS_DATA from questions.json
        questions_data = []
        json_file_path = os.path.join(folder_path_out, "questions.json")
        if os.path.exists(json_file_path):
            try:
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    questions_data = json.load(f)
            except Exception as e:
                pass
        
        # Load MATH_DATA from maths folder
        math_data = {}
        math_folder = os.path.join(folder_path_out, "maths")
        if os.path.exists(math_folder):
            try:
                for filename in os.listdir(math_folder):
                    file_path = os.path.join(math_folder, filename)
                    if os.path.isfile(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            math_data[filename] = f.read()
            except Exception as e:
                pass
        
        # Extract and separate pictures from questions_data
        pictures = extract_and_separate_pictures(questions_data)
        
        # Upload pictures to R2 and replace with URLs
        uploaded_count = upload_pictures_to_r2(questions_data, folder_path_out)
        
        # Save updated questions_data back to JSON file
        if os.path.exists(json_file_path):
            try:
                with open(json_file_path, 'w', encoding='utf-8') as f:
                    json.dump(questions_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                pass
        
        result = {
            'questions_data': questions_data,
            'math_data': math_data
        }
        
        # Add pictures field if images found
        if pictures:
            result['pictures'] = pictures
        
        return result, None
        
    except Exception as e:
        return None, f'Error processing document: {str(e)}'

@digital_document_controller.route('/process', methods=['POST'])
def process_document_upload():
    """Xử lý số hóa tài liệu Word
    ---
    tags:
      - Digital Document
    summary: Upload và số hóa tài liệu Word
    description: Nhận file Word, xử lý số hóa và trả về JSON và HTML viewer
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: file
        type: file
        required: true
        description: File Word cần số hóa (.doc hoặc .docx)
    responses:
      200:
        description: Xử lý thành công
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 200
            message:
              type: string
              example: Document processed successfully
            data:
              type: object
              properties:
                questions_data:
                  type: array
                  description: Dữ liệu câu hỏi từ questions.json
                  example: []
                math_data:
                  type: object
                  description: Dữ liệu toán học từ thư mục maths
                  example: {}
                pictures:
                  type: array
                  description: Danh sách LaTeX code của hình ảnh (nếu có)
                  items:
                    type: string
                  example: ['\\includegraphics[max width=\\linewidth,keepaspectratio]{media/image31.jpeg}']
      400:
        description: Lỗi validation
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 400
            message:
              type: string
              example: No file provided
            data:
              type: object
              nullable: true
              example: null
      500:
        description: Lỗi server
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 500
            message:
              type: string
              example: Error processing document
            data:
              type: object
              nullable: true
              example: null
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'status': 400,
                'message': 'No file provided',
                'data': None
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'status': 400,
                'message': 'No file selected',
                'data': None
            }), 400
        
        if not file.filename.lower().endswith(('.doc', '.docx')):
            return jsonify({
                'status': 400,
                'message': 'File type not allowed. Only .doc and .docx files are allowed',
                'data': None
            }), 400
        
        original_filename = secure_filename(file.filename)
        name, ext = os.path.splitext(original_filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        temp_filename = f"{name}_{timestamp}{ext}"
        
        temp_folder = os.path.join(OUTPUT_BASE_FOLDER, f"temp_{timestamp}")
        os.makedirs(temp_folder, exist_ok=True)
        
        temp_file_path = os.path.join(temp_folder, temp_filename)
        file.save(temp_file_path)
        
        output_folder = os.path.join(OUTPUT_BASE_FOLDER, timestamp)
        result, error = process_document(temp_file_path, output_folder)
        
        try:
            shutil.rmtree(temp_folder)
        except:
            pass
        
        if error:
            return jsonify({
                'status': 500,
                'message': error,
                'data': None
            }), 500
        
        return jsonify({
            'status': 200,
            'message': 'Document processed successfully',
            'data': result
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 500,
            'message': f'Error processing document: {str(e)}',
            'data': None
        }), 500

@digital_document_controller.route('/download/<path:filepath>', methods=['GET'])
def download_result_file(filepath):
    """Tải file kết quả từ output folder
    ---
    tags:
      - Digital Document
    summary: Tải file kết quả (JSON, HTML, LaTeX)
    description: Cho phép tải các file kết quả từ quá trình số hóa
    parameters:
      - in: path
        name: filepath
        type: string
        required: true
        description: "Đường dẫn file (ví dụ: 20241230143025/questions.json hoặc 20241230143025/viewer.html)"
    responses:
      200:
        description: File được tải về thành công
        schema:
          type: file
      404:
        description: File không tồn tại
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 404
            message:
              type: string
              example: File not found
            data:
              type: object
              nullable: true
              example: null
      500:
        description: Lỗi server
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 500
            message:
              type: string
              example: Error downloading file
            data:
              type: object
              nullable: true
              example: null
    """
    try:
        file_path = os.path.join(OUTPUT_BASE_FOLDER, filepath)
        
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return jsonify({
                'status': 404,
                'message': 'File not found',
                'data': None
            }), 404
        
        download_filename = os.path.basename(file_path)
        return send_file(
            file_path,
            as_attachment=True,
            download_name=download_filename
        )
        
    except Exception as e:
        return jsonify({
            'status': 500,
            'message': f'Error downloading file: {str(e)}',
            'data': None
        }), 500

