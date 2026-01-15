from src.config.database import db
from src.models.ai_writing_history import AIWritingHistory
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError


def create_writing_history(user_id: int, data: Dict) -> Tuple[Optional[AIWritingHistory], Optional[str]]:
    """
    Tạo mới writing history với transaction
    
    Args:
        user_id: ID của user
        data: JSON data từ AI response (toàn bộ response_data)
    
    Returns:
        Tuple[AIWritingHistory, None] nếu thành công
        Tuple[None, error_message] nếu lỗi
    """
    try:
        # Bắt đầu transaction
        with db.session.begin():
            history = AIWritingHistory(
                user_id=user_id,
                data=data,
                current_index=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(history)
            db.session.flush()  # Flush để lấy ID
            
            return history, None
            
    except SQLAlchemyError as e:
        db.session.rollback()
        return None, f'Database error: {str(e)}'
    except Exception as e:
        db.session.rollback()
        return None, f'Unexpected error: {str(e)}'


def update_current_index(history_id: int, new_index: int) -> Tuple[bool, Optional[str]]:
    """
    Cập nhật current_index của writing history với transaction
    
    Args:
        history_id: ID của history record
        new_index: Index mới (sentence index hiện tại)
    
    Returns:
        Tuple[True, None] nếu thành công
        Tuple[False, error_message] nếu lỗi
    """
    try:
        with db.session.begin():
            history = db.session.query(AIWritingHistory).filter_by(id=history_id).first()
            
            if not history:
                return False, 'Writing history not found'
            
            # Validate index không âm
            if new_index < 0:
                return False, 'Index must be >= 0'
            
            # Validate index không vượt quá total sentences
            total_sentences = len(history.data.get('vietnameseSentences', [])) or len(history.data.get('englishSentences', []))
            if new_index > total_sentences:
                return False, f'Index {new_index} exceeds total sentences {total_sentences}'
            
            history.current_index = new_index
            history.updated_at = datetime.utcnow()
            
            db.session.flush()
            
            return True, None
            
    except SQLAlchemyError as e:
        db.session.rollback()
        return False, f'Database error: {str(e)}'
    except Exception as e:
        db.session.rollback()
        return False, f'Unexpected error: {str(e)}'


def get_writing_history(history_id: int) -> Tuple[Optional[AIWritingHistory], Optional[str]]:
    """
    Lấy writing history theo ID
    
    Args:
        history_id: ID của history record
    
    Returns:
        Tuple[AIWritingHistory, None] nếu thành công
        Tuple[None, error_message] nếu lỗi
    """
    try:
        history = db.session.query(AIWritingHistory).filter_by(id=history_id).first()
        
        if not history:
            return None, 'Writing history not found'
        
        return history, None
        
    except Exception as e:
        return None, f'Error retrieving history: {str(e)}'


def get_user_writing_histories(
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    order_by: str = 'created_at',
    order_desc: bool = True
) -> Tuple[Optional[List[AIWritingHistory]], Optional[int], Optional[str]]:
    """
    Lấy danh sách writing histories của user
    
    Args:
        user_id: ID của user
        limit: Số lượng records tối đa
        offset: Offset cho pagination
        order_by: Field để sort (created_at, updated_at)
        order_desc: True = DESC, False = ASC
    
    Returns:
        Tuple[List[AIWritingHistory], total_count, None] nếu thành công
        Tuple[None, None, error_message] nếu lỗi
    """
    try:
        query = db.session.query(AIWritingHistory).filter_by(user_id=user_id)
        
        # Get total count
        total_count = query.count()
        
        # Order by
        if order_by == 'created_at':
            order_column = AIWritingHistory.created_at
        elif order_by == 'updated_at':
            order_column = AIWritingHistory.updated_at
        else:
            order_column = AIWritingHistory.created_at
        
        if order_desc:
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())
        
        # Pagination
        histories = query.limit(limit).offset(offset).all()
        
        return histories, total_count, None
        
    except Exception as e:
        return None, None, f'Error retrieving histories: {str(e)}'

