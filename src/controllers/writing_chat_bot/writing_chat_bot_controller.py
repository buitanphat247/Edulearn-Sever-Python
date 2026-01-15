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
    """Tạo nội dung luyện writing (dialogue) bằng AI
    ---
    tags:
      - Writing Chat Bot
    summary: Tạo đoạn hội thoại luyện writing bằng AI
    description: Nhận JSON config và tạo đoạn hội thoại phù hợp cho luyện writing
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
              description: ID của người dùng (liên kết với bảng users)
              example: 1
            language:
              type: string
              description: Ngôn ngữ
              enum:
                - English
                - Vietnamese
              default: English
              example: English
            topic:
              type: string
              description: Chủ đề
              enum:
                - greetings
                - self_introduction
                - daily_conversation
                - weather_talk
                - family_friends
                - weekend_plans
                - shopping
                - restaurant
                - transportation
                - asking_directions
                - hotel_booking
                - doctor_visit
                - phone_calls
                - making_friends
                - invitations
                - hobbies_sports
                - entertainment
                - food_preferences
                - small_talk
                - travel_planning
                - airport_customs
                - emergencies
                - expressing_opinions
                - complaining_suggesting
                - cultural_differences
                - problem_solving
              default: phone_calls
              example: phone_calls
            difficulty:
              type: integer
              description: Độ khó
              enum:
                - 1
                - 2
                - 3
                - 4
                - 5
              minimum: 1
              maximum: 5
              default: 2
              example: 2
            customTopic:
              type: boolean
              description: Có dùng chủ đề tùy chỉnh không
              example: false
            customTopicText:
              type: string
              description: Chủ đề tùy chỉnh (nếu customTopic = true)
              example: ""
            contentType:
              type: string
              description: Loại nội dung
              enum:
                - DIALOGUE
                - ESSAY
                - STORY
              default: DIALOGUE
              example: DIALOGUE
            learningPurpose:
              type: string
              description: Mục đích học
              enum:
                - COMMUNICATION
                - GRAMMAR
                - VOCABULARY
              default: COMMUNICATION
              example: COMMUNICATION
            mode:
              type: string
              description: Chế độ
              enum:
                - AI_GENERATED
              default: AI_GENERATED
              example: AI_GENERATED
    responses:
      200:
        description: Tạo thành công
        schema:
          type: object
          properties:
            id:
              type: string
              description: UUID của exercise
              example: "45c76337-40ef-4349-9387-37b7b35e4059"
            language:
              type: string
              example: English
            topic:
              type: string
              example: phone_calls
            difficulty:
              type: integer
              example: 2
            vietnameseSentences:
              type: array
              description: Mảng các câu hội thoại (nếu language là Vietnamese)
              items:
                type: string
              example: ["Thuê bao: Xin chào, tôi gọi từ số 090...", "Lễ tân: Chào anh/chị, chị Hoa hiện không có ở bàn làm việc..."]
            englishSentences:
              type: array
              description: Mảng các câu hội thoại (nếu language là English)
              items:
                type: string
              example: ["A: Hello, is this ABC Company?", "B: Yes, this is Mai speaking. How can I help you?"]
            totalSentences:
              type: integer
              example: 11
            practiceType:
              type: string
              nullable: true
              example: null
            contentType:
              type: string
              example: DIALOGUE
            userPoints:
              type: number
              example: 0.0
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
              example: Missing required fields
            data:
              type: object
              nullable: true
              example: null
      500:
        description: Lỗi server hoặc AI service
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 500
            message:
              type: string
              example: Error generating dialogue
            data:
              type: object
              nullable: true
              example: null
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
    """Lấy danh sách topics theo category
    ---
    tags:
      - Writing Chat Bot
    summary: Lấy danh sách topics để luyện writing
    description: Trả về danh sách topics theo category (general, ielts, work) hoặc tất cả
    parameters:
      - in: query
        name: category
        type: string
        required: false
        description: Category name (general, ielts, work). Nếu không có thì trả về tất cả
        enum: [general, ielts, work]
        example: general
    responses:
      200:
        description: Lấy danh sách topics thành công
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            category:
              type: string
              example: general
            data:
              type: object
              description: Danh sách topics theo nhóm
              example:
                "🌱 Cơ bản":
                  - value: greetings
                    label: Chào hỏi và làm quen
                  - value: self_introduction
                    label: Giới thiệu bản thân
      400:
        description: Category không hợp lệ
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            message:
              type: string
              example: Invalid category
            data:
              type: object
              nullable: true
              example: null
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
    """Cập nhật current_index của writing history
    ---
    tags:
      - Writing Chat Bot
    summary: Cập nhật index hiện tại (đang làm tới câu nào)
    description: Cập nhật current_index để theo dõi tiến độ làm bài
    consumes:
      - application/json
    parameters:
      - in: path
        name: history_id
        type: integer
        required: true
        description: ID của writing history
        example: 1
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
              description: Index mới (sentence index hiện tại, bắt đầu từ 0)
              minimum: 0
              example: 5
    responses:
      200:
        description: Cập nhật thành công
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 200
            message:
              type: string
              example: Index updated successfully
            data:
              type: object
              properties:
                history_id:
                  type: integer
                  example: 1
                current_index:
                  type: integer
                  example: 5
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
              example: Index must be >= 0
            data:
              type: object
              nullable: true
              example: null
      404:
        description: History không tồn tại
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 404
            message:
              type: string
              example: Writing history not found
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
              example: Error updating index
            data:
              type: object
              nullable: true
              example: null
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
    """Lấy writing history theo ID
    ---
    tags:
      - Writing Chat Bot
    summary: Lấy thông tin writing history theo ID
    description: Trả về toàn bộ thông tin của một writing history
    parameters:
      - in: path
        name: history_id
        type: integer
        required: true
        description: ID của writing history
        example: 1
    responses:
      200:
        description: Lấy thành công
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 200
            message:
              type: string
              example: History retrieved successfully
            data:
              type: object
              properties:
                id:
                  type: integer
                  example: 1
                user_id:
                  type: integer
                  example: 1
                data:
                  type: object
                  description: JSON data từ AI (nội dung practice)
                current_index:
                  type: integer
                  example: 5
                created_at:
                  type: string
                  example: "2024-01-01T10:00:00"
                updated_at:
                  type: string
                  example: "2024-01-01T10:30:00"
      404:
        description: History không tồn tại
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 404
            message:
              type: string
              example: Writing history not found
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
              example: Error retrieving history
            data:
              type: object
              nullable: true
              example: null
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
    """Lấy danh sách writing histories của user
    ---
    tags:
      - Writing Chat Bot
    summary: Lấy danh sách writing histories của user
    description: Trả về danh sách lịch sử tạo nội dung writing của user với pagination
    parameters:
      - in: query
        name: user_id
        type: integer
        required: true
        description: ID của user
        example: 1
      - in: query
        name: limit
        type: integer
        required: false
        description: Số lượng items mỗi trang (mặc định 10)
        default: 10
        example: 10
      - in: query
        name: page
        type: integer
        required: false
        description: Số trang (bắt đầu từ 1)
        default: 1
        example: 1
      - in: query
        name: order_by
        type: string
        required: false
        description: Field để sort (created_at, updated_at)
        enum: [created_at, updated_at]
        default: created_at
        example: created_at
      - in: query
        name: order_desc
        type: boolean
        required: false
        description: True = DESC, False = ASC
        default: true
        example: true
    responses:
      200:
        description: Lấy thành công
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 200
            message:
              type: string
              example: Histories retrieved successfully
            data:
              type: object
              properties:
                histories:
                  type: array
                  items:
                    type: object
                total:
                  type: integer
                  example: 100
                limit:
                  type: integer
                  example: 10
                page:
                  type: integer
                  example: 1
                total_pages:
                  type: integer
                  example: 10
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
              example: user_id is required
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
              example: Error retrieving histories
            data:
              type: object
              nullable: true
              example: null
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

