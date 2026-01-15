from flask import Blueprint, request, jsonify
from src.services.exam_generation_service.exam_service import ExamService

exam_controller = Blueprint('exam_execution', __name__)
_exam_service = ExamService()

@exam_controller.route('/attempt/start', methods=['POST'])
def start_attempt():
    """
    Start a new exam attempt for a student
    ---
    tags:
      - Exam Attempt
    summary: "Initialize an exam session"
    description: "Begins a new attempt for a specific test. Checks if the student has remaining attempts and initializes timing/security tracking."
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - rag_test_id
            - class_id
            - student_id
          properties:
            rag_test_id:
              type: string
              description: "UUID of the Test to attempt"
            class_id:
              type: integer
              description: "ID of the class"
            student_id:
              type: integer
              description: "ID of the student"
            mode:
              type: string
              enum: ['practice', 'official']
              default: 'practice'
              description: "Mode of the exam"
    responses:
      200:
        description: "Attempt started successfully"
        schema:
          type: object
          properties:
            status:
              type: string
              example: "success"
            attempt_id:
              type: string
              example: "a8b7c6..."
      400:
        description: "Invalid attempt (e.g., student has no more attempts for official mode)"
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
    Submit and grade an exam attempt
    ---
    tags:
      - Exam Attempt
    summary: "Finalize and grade the exam"
    description: "Accepts student answers, grades them against the generated answer key, and records the final score/result."
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - attempt_id
            - student_id
            - answers
          properties:
            attempt_id:
              type: string
              description: "UUID of the active attempt"
            student_id:
              type: integer
            answers:
              type: object
              description: "A map of question_id: selected_option_key"
              example: {"q1": "A", "q2": "C"}
    responses:
      200:
        description: "Submission successful with grading result"
        schema:
          type: object
          properties:
            status:
              type: string
              example: "success"
            score:
              type: number
              example: 8.5
            total_questions:
              type: integer
              example: 10
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
    Log a security violation or proctoring event
    ---
    tags:
      - Exam Security
    summary: "Record anti-cheat violations"
    description: "Used by the frontend to report events like fullscreen exit, tab switching, or suspected cheating behavior."
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - attempt_id
            - event_type
          properties:
            attempt_id:
              type: string
            event_type:
              type: string
              enum: ['TAB_SWITCH', 'FULLSCREEN_EXIT', 'FOCUS_LOST', 'DEVTOOLS_OPENED']
            details:
              type: string
              default: ""
    responses:
      200:
        description: "Security event recorded successfully"
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
