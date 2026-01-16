from flask import Flask
import os
from dotenv import load_dotenv
import sys
from flasgger import Swagger
from flask_cors import CORS
from flask_socketio import SocketIO

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Cấu hình CORS để tránh lỗi CORS
cors_origins = os.getenv('CORS_ORIGINS', '*').split(',') if os.getenv('CORS_ORIGINS') else ['*']
CORS(app, 
     origins=cors_origins,
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'],
     supports_credentials=True)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins=cors_origins)

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "EduLearn AI Python Server API",
        "description": "Comprehensive AI services backend for EduLearn. Handles RAG-based Exam Generation, Intelligent Writing Tutoring, and High-fidelity Document Digitization. Documentation covers pipelines, security measures, and implementation guides.",
        "version": "1.0.1",
        "contact": {
            "name": "EduLearn Development Team",
            "email": "support@edulearn.example.com"
        }
    },
    "basePath": "/",
    "schemes": ["http", "https"],
    "consumes": ["application/json"],
    "produces": ["application/json"],
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

from src.controllers.router import register_routes
from src.config.database import init_db
from src.controllers.exam_generation.exam_socket_controller import register_socket_events

# Import models để SQLAlchemy nhận diện (phải import trước khi init_db)
from src.models import AIWritingHistory

# Initialize Database
init_db(app)

# Register routes
register_routes(app)

# Register Socket Events
register_socket_events(socketio)

if __name__ == '__main__':
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    print(f"Starting Flask server on port {PORT}, DEBUG={DEBUG}")
    
    # Run with SocketIO
    socketio.run(app, host='0.0.0.0', port=PORT, debug=DEBUG)
