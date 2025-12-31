"""
Alert Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AlertCreate(BaseModel):
    person_id: int = Field(..., ge=1)
    out_time: float = Field(..., ge=0.0)
    snapshot_path: Optional[str] = Field(None, max_length=500)
    email_sent: bool = Field(default=False)


class AlertResponse(BaseModel):
    id: int
    person_id: int
    out_time: float
    snapshot_path: Optional[str] = None
    email_sent: bool
    timestamp: datetime
    
    class Config:
        from_attributes = True


class AlertList(BaseModel):
    total: int
    page: int
    per_page: int
    alerts: List[AlertResponse]
