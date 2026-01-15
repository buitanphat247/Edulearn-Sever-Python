from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()

def init_db(app):
    """
    Initialize the database with the Flask app.
    """
    try:
        # Load config from env
        database_uri = os.getenv('SQLALCHEMY_DATABASE_URI')
        
        # In Flask-SQLAlchemy 3.0+, we explicitly verify the URI before init
        if not database_uri:
            print("WARNING: SQLALCHEMY_DATABASE_URI is missing. Database features will be disabled.")
            # Vẫn init db nhưng với một URI tạm để tránh lỗi KeyError
            # Sử dụng SQLite in-memory database làm fallback
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
            app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            print("DEBUG: Using fallback SQLite in-memory database")
        else:
            # Auto-convert mysqlconnector to pymysql if mysqlconnector is not available
            if 'mysql+mysqlconnector://' in database_uri:
                try:
                    import mysql.connector  # type: ignore
                    # mysqlconnector is available, use as is
                    print("DEBUG: Using mysqlconnector driver")
                except ImportError:
                    # mysqlconnector not available, convert to pymysql
                    database_uri = database_uri.replace('mysql+mysqlconnector://', 'mysql+pymysql://')
                    print("DEBUG: mysqlconnector not available, auto-converted to pymysql")
                    try:
                        import pymysql  # type: ignore
                        # Verify pymysql is importable (used for type checking)
                        _ = pymysql.__version__  # type: ignore
                        print("DEBUG: pymysql is available")
                    except ImportError:
                        print("ERROR: Neither mysqlconnector nor pymysql is available!")
                        raise ImportError("Please install either mysql-connector-python or pymysql")
            
            # Set config on the app BEFORE init_app
            app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
            app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', 'False').lower() == 'true'
            print(f"DEBUG: init_db setting URI: {database_uri[:50]}...")  # Ẩn password

        # Initialize the extension - LUÔN gọi để tránh KeyError
        db.init_app(app)
        
        # In Flask-SQLAlchemy 3.x, engines are lazy loaded. 
        # Force engine creation ngay sau khi init để đảm bảo engine được tạo
        with app.app_context():
            # Trigger engine creation bằng cách execute một query đơn giản
            # Điều này sẽ force SQLAlchemy tạo engine
            try:
                # Cách 1: Thử truy cập engine trực tiếp
                try:
                    engine = db.engine
                    if engine is not None:
                        print(f"DEBUG: Engine successfully created via db.engine: {type(engine).__name__}")
                    else:
                        raise Exception("Engine is None")
                except (KeyError, AttributeError) as e:
                    # Cách 2: Nếu KeyError, thử dùng get_engine()
                    print(f"DEBUG: db.engine failed ({e}), trying get_engine()...")
                    try:
                        engine = db.get_engine(app, bind=None)
                        if engine is None:
                            raise Exception("get_engine() returned None")
                        print(f"DEBUG: Engine created via get_engine(): {type(engine).__name__}")
                    except Exception as e2:
                        # Cách 3: Force create bằng cách execute một query đơn giản
                        print(f"DEBUG: get_engine() failed ({e2}), trying to force create by executing query...")
                        from sqlalchemy import text
                        try:
                            # Thử execute một query để force engine creation
                            with db.session.begin():
                                db.session.execute(text("SELECT 1"))
                            engine = db.engine
                            print(f"DEBUG: Engine created via query execution: {type(engine).__name__}")
                        except Exception as e3:
                            print(f"DEBUG: All methods failed. Last error: {e3}")
                            raise e3
                
                # Verify extension state
                sa_ext = app.extensions.get('sqlalchemy')
                if sa_ext:
                    if hasattr(sa_ext, 'engines'):
                        engines_keys = list(sa_ext.engines.keys())
                        print(f"DEBUG: Engines keys: {engines_keys}")
                    else:
                        print(f"DEBUG: SQLAlchemy extension found but no 'engines' attribute")
                else:
                    print(f"DEBUG: WARNING: SQLAlchemy extension not found in app.extensions")
                
                # Tự động tạo tất cả tables nếu chưa tồn tại
                try:
                    db.create_all()
                    print("DEBUG: All database tables created/verified successfully")
                except Exception as create_error:
                    print(f"DEBUG: Warning - Could not create tables automatically: {create_error}")
                    # Không raise exception, chỉ log warning
                    # Tables có thể đã tồn tại hoặc có vấn đề về permissions
                
            except Exception as e:
                print(f"DEBUG: Failed to create engine: {e}")
                import traceback
                traceback.print_exc()
                # Không raise exception ở đây để app vẫn có thể chạy
                # Health check sẽ báo lỗi rõ ràng
            
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        import traceback
        traceback.print_exc()
