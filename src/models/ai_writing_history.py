from src.config.database import db
from datetime import datetime
from sqlalchemy import Index, BigInteger, Integer, DateTime, JSON


class AIWritingHistory(db.Model):
    """
    Model lưu lịch sử tạo nội dung writing bằng AI
    """
    __tablename__ = 'ai_writing_history'
    
    id = db.Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(BigInteger, nullable=False, comment='Người dùng tạo nội dung')
    data = db.Column(JSON, nullable=False, comment='Lưu NGUYÊN JSON AI trả về (nội dung practice)')
    current_index = db.Column(Integer, default=0, nullable=False, comment='Đang làm tới sentence thứ mấy (index hiện tại)')
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
    )
    
    # Relationship (nếu có User model)
    # user = relationship('User', backref='writing_histories', foreign_keys=[user_id])
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'data': self.data,
            'current_index': self.current_index,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<AIWritingHistory {self.id} - User {self.user_id} - Index {self.current_index}>'

