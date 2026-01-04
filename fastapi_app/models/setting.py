"""
Setting Model
100% compatível com PostgreSQL
"""

from sqlalchemy import Column, String, Text
from fastapi_app.core.database import Base


class Setting(Base):
    """Model de configuração - key/value store"""
    __tablename__ = "settings"
    
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<Setting(key='{self.key}', value='{self.value[:50]}...')>"
