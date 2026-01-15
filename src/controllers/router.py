from .health_controller import health_controller
from .file_controller import file_controller
from .digital_document_controller.digigtal_document_controller import digital_document_controller
from .writing_chat_bot.writing_chat_bot_controller import writing_chat_bot_controller
from .health_check.health_check_controller import health_check_controller
from .exam_generation.question_controller import question_controller
from .exam_generation.exam_controller import exam_controller

def register_routes(app):
    app.register_blueprint(health_controller, url_prefix="/health") # Old health check
    app.register_blueprint(health_check_controller, url_prefix="/system") # New system checks with DB
    app.register_blueprint(file_controller, url_prefix="/file")
    app.register_blueprint(digital_document_controller, url_prefix="/digital-document")
    app.register_blueprint(writing_chat_bot_controller, url_prefix="/writing-chat-bot")
    app.register_blueprint(question_controller, url_prefix="/ai-exam")
    app.register_blueprint(exam_controller, url_prefix="/api/exams")
    