"""
Authentication Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str = Field(default="bearer")


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None
