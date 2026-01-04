"""
Alert Model
100% compatível com PostgreSQL
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.sql import func
from fastapi_app.core.database import Base


class Alert(Base):
    """Model de alerta"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    person_id = Column(Integer, nullable=False, index=True)
    out_time = Column(Float, nullable=False)
    snapshot_path = Column(String(500), nullable=True)
    email_sent = Column(Boolean, nullable=False, default=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    def __repr__(self):
        return f"<Alert(id={self.id}, person_id={self.person_id}, out_time={self.out_time}s)>"
