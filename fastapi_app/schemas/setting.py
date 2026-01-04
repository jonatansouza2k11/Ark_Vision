"""
Setting Schemas
"""

from pydantic import BaseModel, Field
from typing import Dict, Optional


class SettingUpdate(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    value: str


class SettingBulkUpdate(BaseModel):
    settings: Dict[str, str]


class SettingResponse(BaseModel):
    key: str
    value: Optional[str] = None
    
    class Config:
        from_attributes = True
