from flask import Blueprint, request, jsonify
from src.services.exam_generation_service.question_service import QuestionService

question_controller = Blueprint('exam_question', __name__)
_question_service = None

def get_question_service():
    global _question_service
    if _question_service is None:
        try:
            _question_service = QuestionService()
        except Exception as e:
            raise ValueError(f"Không thể khởi tạo QuestionService: {str(e)}")
    return _question_service

@question_controller.route('/create_test', methods=['POST'])
def create_test_endpoint():
    """
    Tạo đề thi AI (RAG) - Luồng tối giản
    ---
    tags:
      - AI Exam Generation
    summary: "Tạo đề thi nhanh từ File hoặc Mô tả"
    description: "Chỉ cần cung cấp file hoặc mô tả nội dung và số lượng câu hỏi. Đề thi sẽ được tạo ở trạng thái nháp (chưa xuất bản) để tùy chỉnh sau."
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        description: "File tài liệu (PDF, DOCX) để AI phân tích."
      - name: description
        in: formData
        type: string
        description: "Mô tả nội dung hoặc chủ đề muốn tạo đề (dùng nếu không có file)."
      - name: num_questions
        in: formData
        type: integer
        default: 10
        description: "Số lượng câu hỏi muốn tạo."
      - name: title
        in: formData
        type: string
        description: "Tiêu đề đề thi (Tùy chọn, mặc định sẽ tự tạo theo thời gian)."
      - name: class_id
        in: formData
        type: integer
        description: "ID lớp học (Tùy chọn)."
      - name: teacher_id
        in: formData
        type: integer
        required: true
        description: "ID giáo viên tạo đề (Dùng để phân quyền sở hữu)."
    responses:
      201:
        description: "Đề thi đã được tạo thành công ở dạng nháp."
    """
    try:
        data = request.form
        file = request.files.get('file')
        teacher_id = data.get('teacher_id')
        
        if not teacher_id:
            return jsonify({"status": "error", "message": "teacher_id is required"}), 400

        # ... (logic cũ)
        title = data.get('title')
        if not title:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            title = f"AI Exam - {now_str}"
            
        description = data.get('description', '')
        
        # Validation: Phải có ít nhất file hoặc mô tả
        if not file and not description:
            return jsonify({
                "status": "error", 
                "message": "Vui lòng cung cấp 'file' tài liệu hoặc 'description' nội dung để AI làm căn cứ."
            }), 400

        # 2. Các tham số cấu hình mặc định (Sẽ được chỉnh sửa sau trong advanced editor)
        try:
            num_questions = int(data.get('num_questions', '10'))
        except: num_questions = 10
            
        duration_minutes = int(data.get('duration_minutes', '45'))
        total_score = int(data.get('total_score', '10'))
        difficulty = data.get('difficulty', 'medium')
        mode = data.get('mode', 'llamaindex')
        max_attempts = int(data.get('max_attempts', '1'))

        try:
            class_id = int(data.get('class_id', '0')) if data.get('class_id') else None
        except: class_id = None

        service = get_question_service()
        result = service.create_test_from_file(
            file=file,
            title=title,
            description=description,
            duration_minutes=duration_minutes,
            total_score=total_score,
            num_questions=num_questions,
            difficulty=difficulty,
            mode=mode,
            class_id=class_id,
            max_attempts=max_attempts,
            teacher_id=teacher_id # Thêm teacher_id vào đây
        )

        return jsonify({"status": "success", "data": result}), 201

    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        print(f"Error in create_test: {e}")
        return jsonify({"status": "error", "message": f"Internal Error: {str(e)}"}), 500

@question_controller.route('/tests/class/<int:class_id>/teacher', methods=['GET'])
def get_teacher_tests_in_class(class_id):
    """
    [Teacher] Lấy tất cả đề thi trong lớp (bao gồm cả nháp)
    ---
    tags:
      - AI Exam Generation
    summary: "Lấy danh sách đề thi đầy đủ cho Giáo viên"
    description: "Trả về tất cả đề thi trong lớp, bao gồm cả các đề chưa xuất bản (is_published=false)."
    parameters:
      - name: class_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: "Danh sách đề thi"
    """
    try:
        service = get_question_service()
        tests = service.document_service.get_teacher_tests(class_id)
        return jsonify({"status": "success", "data": tests}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@question_controller.route('/tests/class/<int:class_id>/published', methods=['GET'])
def get_published_class_tests(class_id):
    """
    [Student] Lấy danh sách đề thi đã xuất bản cho học sinh
    ---
    tags:
      - AI Exam Generation
    summary: "Lấy danh sách đề thi đã xuất bản cho Học sinh"
    description: "Chỉ trả về các đề thi đã xuất bản (is_published=true) trong lớp cụ thể."
    parameters:
      - name: class_id
        in: path
        type: integer
        required: true
      - name: student_id
        in: query
        type: integer
        required: true
    responses:
      200:
        description: "Danh sách đề thi cho học sinh"
    """
    try:
        service = get_question_service()
        student_id = request.args.get('student_id', type=int)
        if not student_id:
            return jsonify({"status": "error", "message": "student_id is required"}), 400
            
        tests = service.document_service.get_published_tests_by_class(class_id, student_id)
        return jsonify({"status": "success", "data": tests}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@question_controller.route('/test/<string:test_id>', methods=['GET'])
def get_test_detail(test_id):
    """
    Get full details of a specific RAG Test
    ---
    tags:
      - AI Exam Generation
    summary: "Fetch test details and its questions"
    description: "Returns full metadata and the list of questions for a specific test. Requires student_id to verify if they are allowed to take the test."
    parameters:
      - name: test_id
        in: path
        type: string
        required: true
        description: "UUID of the Test"
      - name: student_id
        in: query
        type: integer
        required: false
        description: "Optional. ID of the student to verify access."
    responses:
      200:
        description: "Test details and questions retrieved successfully"
      403:
        description: "Permission Denied (e.g., student has no more attempts)"
      404:
        description: "Test not found"
    """
    try:
        service = get_question_service()
        student_id = request.args.get('student_id', type=int)
        test_details = service.document_service.get_test_details(test_id, student_id)
        if not test_details:
            return jsonify({"status": "error", "message": "Test not found"}), 404
        return jsonify({"status": "success", "data": test_details}), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 403
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@question_controller.route('/test/<string:test_id>', methods=['DELETE'])
def delete_test_endpoint(test_id):
    """
    Delete a specific RAG Test
    ---
    tags:
      - AI Exam Generation
    parameters:
      - name: test_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Success message
    """
    try:
        service = get_question_service()
        success = service.document_service.delete_test(test_id)
        if success:
            return jsonify({"status": "success", "message": "Test deleted successfully"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to delete test"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@question_controller.route('/tests/class/<int:class_id>', methods=['DELETE'])
def delete_class_tests_endpoint(class_id):
    """
    Delete ALL RAG Tests belonging to a specific class
    ---
    tags:
      - AI Exam Generation
    parameters:
      - name: class_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Done
    """
    try:
        service = get_question_service()
        success = service.document_service.delete_all_tests_by_class(class_id)
        if success:
            return jsonify({"status": "success", "message": f"Deleted all AI exams for class {class_id}"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to delete class tests"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@question_controller.route('/test/<string:test_id>', methods=['PUT'])
def update_test_endpoint(test_id):
    """
    Update Test metadata
    ---
    tags:
      - AI Exam Generation
    summary: "Update test title, description, and settings"
    parameters:
      - name: test_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            title: {type: string}
            description: {type: string}
            duration_minutes: {type: integer}
            max_attempts: {type: integer}
    responses:
      200:
        description: "Test updated successfully"
    """
    try:
        data = request.json
        service = get_question_service()
        success = service.document_service.update_test(test_id, data)
        if success:
            return jsonify({"status": "success", "message": "Test updated"}), 200
        return jsonify({"status": "error", "message": "Update failed"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@question_controller.route('/question/<string:question_id>', methods=['PUT'])
def update_question_endpoint(question_id):
    """
    Cập nhật nội dung câu hỏi
    ---
    tags:
      - AI Exam Generation
    summary: "Cập nhật nội dung và đáp án câu hỏi"
    description: "Cho phép chỉnh sửa text câu hỏi, 4 phương án lựa chọn, đáp án đúng và lời giải thích."
    parameters:
      - name: question_id
        in: path
        type: string
        required: true
        description: "ID của câu hỏi"
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            content: {type: string}
            answer_a: {type: string}
            answer_b: {type: string}
            answer_c: {type: string}
            answer_d: {type: string}
            correct_answer: {type: string}
            explanation: {type: string}
    responses:
      200:
        description: "Cập nhật thành công"
      400:
        description: "Cập nhật thất bại"
    """
    try:
        data = request.json
        service = get_question_service()
        success = service.document_service.update_question(question_id, data)
        if success:
            return jsonify({"status": "success", "message": "Question updated"}), 200
        return jsonify({"status": "error", "message": "Update failed"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@question_controller.route('/test/<string:test_id>/publish', methods=['POST'])
def publish_test_endpoint(test_id):
    """
    Xuất bản hoặc Hủy xuất bản đề thi
    ---
    tags:
      - AI Exam Generation
    summary: "Thay đổi trạng thái công khai của đề thi"
    parameters:
      - name: test_id
        in: path
        type: string
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            is_published:
              type: boolean
              default: true
              description: "True để xuất bản cho học sinh thấy, False để đưa về nháp."
    responses:
      200:
        description: "Trình thái xuất bản đã được cập nhật"
    """
    try:
        data = request.json or {}
        # Mặc định là True nếu không truyền gì (luồng "Xuất bản")
        is_published = data.get('is_published', True)
        
        service = get_question_service()
        success = service.document_service.update_test(test_id, {"is_published": is_published})
        
        if success:
            status_text = "đã xuất bản" if is_published else "đã đưa về nháp"
            return jsonify({
                "status": "success", 
                "message": f"Đề thi {status_text} thành công",
                "is_published": is_published
            }), 200
            
        return jsonify({"status": "error", "message": "Không thể cập nhật trạng thái xuất bản"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
