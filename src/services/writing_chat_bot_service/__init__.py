from .writing_chat_bot_service import generate_dialogue, get_topics
from .writing_history_service import (
    create_writing_history,
    update_current_index,
    get_writing_history,
    get_user_writing_histories
)

__all__ = [
    'generate_dialogue',
    'get_topics',
    'create_writing_history',
    'update_current_index',
    'get_writing_history',
    'get_user_writing_histories'
]

