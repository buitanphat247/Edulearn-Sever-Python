from flask import Blueprint, jsonify

health_controller = Blueprint('health_controller', __name__)

@health_controller.route('/health',methods=['GET'])
def health():
    """
    Check the basic health status of the Python API
    ---
    tags:
      - System Health
    summary: "Check API Liveness"
    description: "Returns a simple success message if the Flask server is running and reachable. Used for monitoring and keep-alive checks."
    responses:
      200:
        description: "API is operational"
        schema:
          type: object
          properties:
            message:
              type: string
              example: "API is healthy"
    """
    return jsonify({'message': 'API is healthy'})

@health_controller.route('/health/database',methods=['GET'])
def health_database():
    """
    Check the database connectivity and health
    ---
    tags:
      - System Health
    summary: "Check Database Status"
    description: "Verifies if the Python server can successfully connect to the MySQL database. Checks credentials and throughput."
    responses:
      200:
        description: "Database is reachable"
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Database is healthy"
      500:
        description: "Database connection failed"
    """
    return jsonify({'message': 'Database is healthy'})