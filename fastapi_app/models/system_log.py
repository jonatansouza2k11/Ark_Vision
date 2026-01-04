"""
SystemLog Model
100% compatível com PostgreSQL
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from fastapi_app.core.database import Base


class SystemLog(Base):
    """Model de log do sistema"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False, index=True)
    message = Column(Text, nullable=False)
    module = Column(String(100), nullable=True)
    user_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    def __repr__(self):
        return f"<SystemLog(id={self.id}, level='{self.level}', timestamp={self.timestamp})>"
