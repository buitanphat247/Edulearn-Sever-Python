from flask import Blueprint, jsonify, request
import os
import uuid
from src.services.writing_chat_bot_service import (
    generate_dialogue,
    get_topics,
    create_writing_history,
    update_current_index,
    get_writing_history,
    get_user_writing_histories
)

writing_chat_bot_controller = Blueprint('writing_chat_bot_controller', __name__)

@writing_chat_bot_controller.route('/generate', methods=['POST'])
def generate_writing_content():
    """
    Generate AI-powered dialogue for writing practice
    ---
    tags:
      - Writing AI Tutor
    summary: "Create Interactive Writing Exercise"
    description: "Initializes a writing tutoring session by generating a structured dialogue, story, or essay based on user configuration. Supports multiple languages (English/Vietnamese) and difficulty levels (1-5)."
    consumes:
      - application/json
    parameters:
      - in: body
        name: config
        required: true
        schema:
          type: object
          required:
            - user_id
            - language
            - topic
            - difficulty
            - contentType
            - learningPurpose
          properties:
            user_id:
              type: integer
              description: "ID of the student"
            language:
              type: string
              enum: ['English', 'Vietnamese']
              default: 'English'
            topic:
              type: string
              description: "Target topic for conversation"
            difficulty:
              type: integer
              description: "CEFR-like level (1=Beginner, 5=Advanced)"
              minimum: 1
              maximum: 5
            customTopic:
              type: boolean
              description: "Enable free-text topic prompt"
            customTopicText:
              type: string
            contentType:
              type: string
              enum: ['DIALOGUE', 'ESSAY', 'STORY']
            learningPurpose:
              type: string
              enum: ['COMMUNICATION', 'GRAMMAR', 'VOCABULARY']
    responses:
      200:
        description: "Exercise generated successfully"
        schema:
          type: object
          properties:
            id:
              type: string
              description: "Exercise UUID"
            englishSentences:
              type: array
              items:
                type: string
            totalSentences:
              type: integer
      400:
        description: "Invalid configuration payload"
      500:
        description: "AI Service error during generation"
    """
    try:
        # Lấy JSON từ request
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 400,
                'message': 'No JSON data provided',
                'data': None
            }), 400
        
        # Validate required fields
        required_fields = ['user_id', 'language', 'topic', 'difficulty', 'contentType', 'learningPurpose']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'status': 400,
                'message': f'Missing required fields: {", ".join(missing_fields)}',
                'data': None
            }), 400
        
        # Validate user_id
        user_id = data.get('user_id')
        if not isinstance(user_id, int) or user_id <= 0:
            return jsonify({
                'status': 400,
                'message': 'user_id must be a positive integer',
                'data': None
            }), 400
        
        # Gọi service để generate dialogue
        result = generate_dialogue(
            language=data.get('language', 'English'),
            topic=data.get('topic', ''),
            difficulty=data.get('difficulty', 2),
            custom_topic=data.get('customTopic', False),
            custom_topic_text=data.get('customTopicText', ''),
            content_type=data.get('contentType', 'DIALOGUE'),
            learning_purpose=data.get('learningPurpose', 'COMMUNICATION'),
            mode=data.get('mode', 'AI_GENERATED')
        )
        
        if result.get('error'):
            return jsonify({
                'status': 500,
                'message': result['error'],
                'data': None
            }), 500
        
        # Xác định tên field cho sentences dựa trên language
        language = data.get('language', 'English')
        is_vietnamese = language.lower() in ['vietnamese', 'vi', 'tiếng việt', 'tieng viet']
        # Lấy sentences song song từ result
        target_sentences = result.get('target_sentences', [])
        translation_sentences = result.get('translation_sentences', [])
        
        # Determine total from target lines
        total_sentences = len(target_sentences)
        
        # With the unified prompt format (Speaker: VN | EN):
        # target_sentences = Vietnamese (with Speaker)
        # translation_sentences = English (Meaning/Answer)
        
        vietnamese_sents = target_sentences
        english_sents = translation_sentences

        # Tạo response data (chưa có id, sẽ set sau khi lưu vào DB)
        response_data = {
            'language': language,
            'topic': data.get('topic', ''),
            'difficulty': data.get('difficulty', 2),
            'vietnameseSentences': vietnamese_sents,
            'englishSentences': english_sents,
            'totalSentences': total_sentences,
            'practiceType': None,
            'contentType': data.get('contentType', 'DIALOGUE'),
            'userPoints': 0.0
        }
        
        # Lưu vào database với transaction
        history, error = create_writing_history(user_id=user_id, data=response_data)
        
        if error:
            # Nếu lưu DB thất bại, vẫn trả về response nhưng không có id
            print(f"WARNING: Failed to save writing history: {error}")
            # Tạo UUID tạm thời nếu không lưu được vào DB
            response_data['id'] = str(uuid.uuid4())
            response_data['current_index'] = 0
        else:
            # Set id = history_id (ID từ database)
            response_data['id'] = history.id
            response_data['current_index'] = history.current_index
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({
            'status': 500,
            'message': f'Error generating dialogue: {str(e)}',
            'data': None
        }), 500


@writing_chat_bot_controller.route('/topics', methods=['GET'])
def get_topics_list():
    """
    Retrieve writing practice topics by category
    ---
    tags:
      - Writing AI Tutor
    summary: "Get Available Topics"
    description: "Returns a categorized list of practice topics (General, IELTS, Work). Useful for the initial student selection screen. Security: Read-only access."
    parameters:
      - in: query
        name: category
        type: string
        required: false
        description: "Filter by category (general, ielts, work)"
        enum: [general, ielts, work]
    responses:
      200:
        description: "Topics retrieved successfully"
        schema:
          type: object
          properties:
            status:
              type: string
              example: "success"
            data:
              type: object
    """
    try:
        category = request.args.get('category', None)
        result = get_topics(category)
        
        if result['status'] == 'error':
            return jsonify({
                'status': 400,
                'message': result['message'],
                'data': None
            }), 400
        
        response_data = {
            'status': 200,
            'message': 'Topics retrieved successfully'
        }
        
        if 'category' in result:
            response_data['category'] = result['category']
        
        response_data['data'] = result['data']
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({
            'status': 500,
            'message': f'Error retrieving topics: {str(e)}',
            'data': None
        }), 500


@writing_chat_bot_controller.route('/history/<int:history_id>/index', methods=['PUT'])
def update_history_index(history_id):
    """
    Update the current progress index of a writing session
    ---
    tags:
      - Writing AI Tutor
    summary: "Save Session Progress"
    description: "Saves the current sentence index for a specific practice session. Allows students to resume their practice later. Security: Validates session existence before update."
    parameters:
      - in: path
        name: history_id
        type: integer
        required: true
        description: "ID of the practice session"
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - current_index
          properties:
            current_index:
              type: integer
              description: "New progress index (0..N)"
    responses:
      200:
        description: "Progress updated successfully"
      404:
        description: "Practice session not found"
    """
    try:
        body = request.get_json()
        
        if not body:
            return jsonify({
                'status': 400,
                'message': 'No JSON data provided',
                'data': None
            }), 400
        
        current_index = body.get('current_index')
        
        if current_index is None:
            return jsonify({
                'status': 400,
                'message': 'Missing required field: current_index',
                'data': None
            }), 400
        
        if not isinstance(current_index, int) or current_index < 0:
            return jsonify({
                'status': 400,
                'message': 'current_index must be a non-negative integer',
                'data': None
            }), 400
        
        # Cập nhật index với transaction
        success, error = update_current_index(history_id, current_index)
        
        if error:
            if 'not found' in error.lower():
                return jsonify({
                    'status': 404,
                    'message': error,
                    'data': None
                }), 404
            else:
                return jsonify({
                    'status': 400,
                    'message': error,
                    'data': None
                }), 400
        
        return jsonify({
            'status': 200,
            'message': 'Index updated successfully',
            'data': {
                'history_id': history_id,
                'current_index': current_index
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 500,
            'message': f'Error updating index: {str(e)}',
            'data': None
        }), 500


@writing_chat_bot_controller.route('/history/<int:history_id>', methods=['GET'])
def get_history_by_id(history_id):
    """
    Retrieve writing practice session details
    ---
    tags:
      - Writing AI Tutor
    summary: "Get Session Details"
    description: "Returns the full content (sentences, topic, difficulty) and progress of a specific practice session."
    parameters:
      - in: path
        name: history_id
        type: integer
        required: true
        description: "ID of the practice session"
    responses:
      200:
        description: "Session details retrieved"
      404:
        description: "Session not found"
    """
    try:
        history, error = get_writing_history(history_id)
        
        if error:
            return jsonify({
                'status': 404,
                'message': error,
                'data': None
            }), 404
        
        return jsonify({
            'status': 200,
            'message': 'History retrieved successfully',
            'data': history.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 500,
            'message': f'Error retrieving history: {str(e)}',
            'data': None
        }), 500


@writing_chat_bot_controller.route('/history', methods=['GET'])
def get_user_histories():
    """
    Get user's writing practice history
    ---
    tags:
      - Writing AI Tutor
    summary: "List Practice History"
    description: "Returns a paginated list of all writing practice sessions for a specific user. Supports sorting and page limits."
    parameters:
      - in: query
        name: user_id
        type: integer
        required: true
      - in: query
        name: limit
        type: integer
        default: 10
      - in: query
        name: page
        type: integer
        default: 1
    responses:
      200:
        description: "History list retrieved"
      400:
        description: "Missing user_id"
    """
    try:
        user_id = request.args.get('user_id', type=int)
        
        if not user_id:
            return jsonify({
                'status': 400,
                'message': 'user_id is required',
                'data': None
            }), 400
        
        if user_id <= 0:
            return jsonify({
                'status': 400,
                'message': 'user_id must be a positive integer',
                'data': None
            }), 400
        
        limit = request.args.get('limit', 10, type=int)
        page = request.args.get('page', 1, type=int)
        order_by = request.args.get('order_by', 'created_at', type=str)
        order_desc = request.args.get('order_desc', 'true', type=str).lower() == 'true'
        
        # Validate limit và page
        if limit < 1 or limit > 100:
            limit = 10
        if page < 1:
            page = 1
        
        # Tính toán offset từ page
        offset = (page - 1) * limit
        
        histories, total, error = get_user_writing_histories(
            user_id=user_id,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_desc=order_desc
        )
        
        if error:
            return jsonify({
                'status': 500,
                'message': error,
                'data': None
            }), 500
        
        # Tính total_pages
        total_count = total if total is not None else 0
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
        
        return jsonify({
            'status': 200,
            'message': 'Histories retrieved successfully',
            'data': {
                'histories': [h.to_dict() for h in histories] if histories else [],
                'total': total_count,
                'limit': limit,
                'page': page,
                'total_pages': total_pages
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 500,
            'message': f'Error retrieving histories: {str(e)}',
            'data': None
        }), 500

