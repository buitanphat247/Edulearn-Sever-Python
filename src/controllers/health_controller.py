from flask import Blueprint, jsonify

health_controller = Blueprint('health_controller', __name__)

@health_controller.route('/health',methods=['GET'])
def health():
    """
    Kiểm tra tình trạng health của API
    ---
    tags:
      - Health
    summary: Kiểm tra tình trạng health của API
    description: Trả về thông điệp health của API
    responses:
      200:
        description: Thành công
    """
    return jsonify({'message': 'API is healthy'})

@health_controller.route('/health/database',methods=['GET'])
def health_database():
    """
    Kiểm tra tình trạng health của database
    ---
    tags:
      - Health
    summary: Kiểm tra tình trạng health của database
    description: Trả về thông điệp health của database
    responses:
      200:
        description: Thành công
    """
    return jsonify({'message': 'Database is healthy'})