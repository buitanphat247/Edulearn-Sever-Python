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
    Create a Full Test (Exam) with scoring and metadata using AI
    ---
    tags:
      - AI Exam Generation
    summary: "Generate an AI-powered exam from a file or text description"
    description: "Accepts a document file (PDF/DOCX) or a text description to generate a full set of questions using RAG (Retrieval-Augmented Generation). Supports multiple AI modes."
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: false
        description: "Upload Document (PDF, DOCX). If provided, AI will analyze this file to generate questions."
      - name: title
        in: formData
        type: string
        required: true
        description: "Title of the Test (e.g., 'Final Exam: Python Basics')"
      - name: description
        in: formData
        type: string
        description: "Text description or instruction. Can be used instead of or alongside a file."
      - name: duration_minutes
        in: formData
        type: integer
        default: 45
        description: "Time limit for the test in minutes"
      - name: total_score
        in: formData
        type: integer
        default: 10
        description: "Maximum score for the entire test"
      - name: num_questions
        in: formData
        type: integer
        default: 10
        description: "Target number of questions to generate"
      - name: difficulty
        in: formData
        type: string
        enum: ['easy', 'medium', 'hard']
        default: 'medium'
      - name: mode
        in: formData
        type: string
        enum: ['llamaindex', 'offline', 'online']
        default: 'llamaindex'
        description: "Process Mode. 'llamaindex' uses advanced RAG, 'offline' uses local LLM, 'online' uses OpenAI."
      - name: class_id
        in: formData
        type: integer
        required: false
        description: "Optional. ID of the class to assign this test to."
    responses:
      201:
        description: "Test created successfully"
        schema:
          type: object
          properties:
            status:
              type: string
              example: "success"
            data:
              type: object
              properties:
                 test_id:
                   type: string
                   example: "550e8400-e29b-41d4-a716-446655440000"
                 questions:
                   type: array
                   items:
                     type: object
      400:
        description: "Validation Error (e.g., missing title, no file/description provided)"
      500:
        description: "Internal Server Error during AI generation"
    """
    try:
        # Check params
        file = None
        if 'file' in request.files and request.files['file'].filename != '':
             file = request.files['file']
             
        title = request.form.get('title')
        if not title:
            return jsonify({"status": "error", "message": "Title is required"}), 400
            
        description = request.form.get('description', '')
        
        # Validation: Either File or Description must be present
        if not file and not description:
             return jsonify({
                 "status": "error", 
                 "message": "Either 'file' or 'description' must be provided."
             }), 400

        try:
            duration_minutes = int(request.form.get('duration_minutes', '45'))
        except: duration_minutes = 45
        
        try:
            total_score = int(request.form.get('total_score', '10'))
        except: total_score = 10
        
        try:
            num_questions = int(request.form.get('num_questions', '10'))
        except: num_questions = 10
        
        difficulty = request.form.get('difficulty', 'medium')
        mode = request.form.get('mode', 'llamaindex')

        try:
            class_id = int(request.form.get('class_id', '0'))
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
            class_id=class_id
        )

        return jsonify({"status": "success", "data": result}), 201

    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        print(f"Error in create_test: {e}")
        return jsonify({"status": "error", "message": f"Internal Error: {str(e)}"}), 500

@question_controller.route('/tests/class/<int:class_id>', methods=['GET'])
def get_class_tests(class_id):
    """
    Get all RAG Tests for a specific class
    ---
    tags:
      - AI Exam Generation
    summary: "Fetch all tests available for a class"
    description: "Returns a list of tests generated for a specific class, including metadata and students' attempt counts if student_id is provided."
    parameters:
      - name: class_id
        in: path
        type: integer
        required: true
        description: "ID of the class"
      - name: student_id
        in: query
        type: integer
        required: false
        description: "Optional. ID of the student to check attempt status."
    responses:
      200:
        description: "List of tests retrieved successfully"
        schema:
          type: object
          properties:
            status:
              type: string
              example: "success"
            data:
              type: array
              items:
                type: object
    """
    try:
        service = get_question_service()
        student_id = request.args.get('student_id', type=int)
        tests = service.document_service.get_tests_by_class(class_id, student_id)
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
