from flask import Flask
import os
from dotenv import load_dotenv
import sys
from flasgger import Swagger
from flask_cors import CORS

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Cấu hình CORS để tránh lỗi CORS
# Cho phép tất cả origins trong development, có thể config qua env cho production
cors_origins = os.getenv('CORS_ORIGINS', '*').split(',') if os.getenv('CORS_ORIGINS') else ['*']
CORS(app, 
     origins=cors_origins,
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'],
     supports_credentials=True)

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
        "title": "Flask API Documentation",
        "description": "API documentation với Swagger",
        "version": "1.0.0",
        "contact": {
            "name": "API Support"
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
# Import models để SQLAlchemy nhận diện (phải import trước khi init_db)
from src.models import AIWritingHistory

# Initialize Database - init_db sẽ tự set config và tự động tạo tables
# Không set config ở đây để tránh conflict với init_db
init_db(app)

register_routes(app)

if __name__ == '__main__':
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    print(f"Starting Flask server on port {PORT}, DEBUG={DEBUG}")
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
