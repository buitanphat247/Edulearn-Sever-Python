"""
Script để tạo bảng AIwritingHistory trong database
Chạy script này sau khi đã config SQLALCHEMY_DATABASE_URI trong .env
"""
from flask import Flask
from src.config.database import init_db, db
from src.models.ai_writing_history import AIWritingHistory
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Initialize database
init_db(app)

with app.app_context():
    try:
        # Tạo tất cả tables
        db.create_all()
        print("✅ Tables created successfully!")
        print(f"✅ Table '{AIWritingHistory.__tablename__}' is ready")
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        import traceback
        traceback.print_exc()

