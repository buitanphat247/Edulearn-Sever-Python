from flask import Blueprint, request, jsonify
from src.services.exam_generation_service.exam_service import ExamService

exam_controller = Blueprint('exam_execution', __name__)
_exam_service = ExamService()

@exam_controller.route('/attempt/start', methods=['POST'])
def start_attempt():
    """
    Start a new exam attempt
    ---
    tags:
      - Exam Attempt
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            rag_test_id:
              type: string
            class_id:
              type: integer
            student_id:
              type: integer
            mode:
              type: string
              enum: ['practice', 'official']
    responses:
      200:
        description: Attempt started successfully
      400:
        description: Invalid attempt or out of attempts
    """
    data = request.json
    try:
        result = _exam_service.start_attempt(
            rag_test_id=data['rag_test_id'],
            class_id=data['class_id'],
            student_id=data['student_id'],
            mode=data.get('mode', 'practice')
        )
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "details": "Check server logs"}), 500

@exam_controller.route('/attempt/submit', methods=['POST'])
def submit_attempt():
    """
    Submit an exam attempt
    ---
    tags:
      - Exam Attempt
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            attempt_id:
              type: string
            student_id:
              type: integer
            answers:
              type: object
    responses:
      200:
        description: Submission successful
    """
    data = request.json
    try:
        result = _exam_service.submit_attempt(
            attempt_id=data['attempt_id'],
            student_id=data['student_id'],
            answers=data['answers']
        )
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@exam_controller.route('/security/log', methods=['POST'])
def log_security_event():
    """
    Log a security violation/event
    ---
    tags:
      - Exam Security
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            attempt_id:
              type: string
            event_type:
              type: string
            details:
              type: string
    responses:
      200:
        description: Event logged
    """
    data = request.json
    try:
        result = _exam_service.log_security_event(
            attempt_id=data['attempt_id'],
            event_type=data['event_type'],
            details=data.get('details')
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@exam_controller.route('/test/<string:test_id>/attempts', methods=['GET'])
def get_test_attempts(test_id):
    """
    Get all attempts for a specific test
    ---
    tags:
      - Exam Attempt
    parameters:
      - name: test_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: List of attempts
    """
    try:
        result = _exam_service.get_test_attempts(test_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500
