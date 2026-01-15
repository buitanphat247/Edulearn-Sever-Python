from flask import Blueprint, jsonify
from src.config.database import db
from sqlalchemy import text
import traceback

health_check_controller = Blueprint('health_check_controller', __name__)

@health_check_controller.route('/db-test', methods=['GET'])
def check_db_connection():
    """Kiểm tra trạng thái kết nối Database (MySQL)
    ---
    tags:
      - System
    summary: Kiểm tra kết nối tới MySQL Database
    responses:
      200:
        description: Kết nối thành công
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 200
            message:
              type: string
              example: "Database connection successful!"
            db_version:
              type: string
              example: "8.0.30"
      500:
        description: Lỗi kết nối
        schema:
          type: object
          properties:
            status:
              type: integer
              example: 500
            message:
              type: string
              example: "Database connection failed"
            error:
              type: string
    """
    try:
        from flask import current_app
        
        # DEBUG: Check what config is actually loaded
        loaded_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI')
        
        # Kiểm tra xem database đã được khởi tạo chưa
        sa_ext = current_app.extensions.get('sqlalchemy')
        if not sa_ext:
            return jsonify({
                'status': 503,
                'message': 'Database not initialized. SQLALCHEMY_DATABASE_URI may be missing.',
                'error': 'SQLAlchemy extension not found in app.extensions',
                'debug_config_uri': str(loaded_uri)
            }), 503
        
        # Kiểm tra xem có URI không (hoặc là fallback URI)
        if not loaded_uri or loaded_uri == 'sqlite:///:memory:':
            return jsonify({
                'status': 503,
                'message': 'Database URI not configured',
                'error': 'SQLALCHEMY_DATABASE_URI is missing in environment variables. Using fallback in-memory database.',
                'debug_config_uri': loaded_uri,
                'note': 'Please set SQLALCHEMY_DATABASE_URI in your .env file'
            }), 503
        
        # Debugging the Flask-SQLAlchemy state
        db_state = "Found"
        engines_keys = list(sa_ext.engines.keys()) if hasattr(sa_ext, 'engines') else "No engines attr"
        
        debug_info = {
             "uri": loaded_uri[:50] + "..." if loaded_uri and len(loaded_uri) > 50 else loaded_uri,  # Ẩn password
             "sa_extension": db_state,
             "engine_keys": str(engines_keys),
             "db_id_in_controller": id(db)
        }
        print(f"DEBUG Controller: {debug_info}")

        # Sử dụng connection trực tiếp từ engine thay vì session để test kết nối chắc chắn hơn
        # Kiểm tra xem engine có tồn tại không
        # Trong Flask-SQLAlchemy 3.x, engines được lazy load, cần force create
        engine = None
        engine_error = None
        
        # Thử nhiều cách để lấy engine
        try:
            # Cách 1: Truy cập trực tiếp
            engine = db.engine
            print(f"DEBUG: Engine retrieved via db.engine")
        except (KeyError, AttributeError) as e:
            engine_error = str(e)
            print(f"DEBUG: db.engine failed: {e}")
            try:
                # Cách 2: Dùng get_engine()
                engine = db.get_engine(current_app, bind=None)
                print(f"DEBUG: Engine retrieved via get_engine()")
            except Exception as e2:
                engine_error = f"{e}, get_engine() failed: {str(e2)}"
                print(f"DEBUG: get_engine() also failed: {e2}")
                try:
                    # Cách 3: Force create bằng cách execute query
                    # text đã được import ở đầu file, không cần import lại
                    with db.session.begin():
                        db.session.execute(text("SELECT 1"))
                    engine = db.engine
                    print(f"DEBUG: Engine created via query execution")
                except Exception as e3:
                    engine_error = f"{engine_error}, query execution failed: {str(e3)}"
                    print(f"DEBUG: All methods failed: {e3}")
        
        # Verify engine
        if engine is None:
            return jsonify({
                'status': 503,
                'message': 'Database engine not created',
                'error': f'All methods to get engine failed: {engine_error}',
                'debug_config_uri': str(loaded_uri),
                'wa_engines_keys': str(engines_keys),
                'note': 'Please check: 1) mysql-connector-python is installed, 2) SQLALCHEMY_DATABASE_URI format is correct, 3) Database server is running'
            }), 503
        
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT VERSION()"))
            version = result.scalar()
        
        return jsonify({
            'status': 200,
            'message': 'Database connection successful!',
            'db_version': version,
            'debug_info': debug_info
        }), 200
        
    except Exception as e:
        from flask import current_app
        error_details = traceback.format_exc()
        loaded_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI') # Debug info in error
        
        # Debugging fail state
        sa_ext = current_app.extensions.get('sqlalchemy')
        engines_keys = list(sa_ext.engines.keys()) if sa_ext and hasattr(sa_ext, 'engines') else "No engines attr"
        
        print(f"DB Error Traceback: {error_details}") 
        return jsonify({
            'status': 500,
            'message': 'Database connection failed',
            'error': str(e),
            'debug_config_uri': str(loaded_uri), 
            'wa_engines_keys': str(engines_keys),
            'traceback': error_details
        }), 500
