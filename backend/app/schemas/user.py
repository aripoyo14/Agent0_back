from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID

# ユーザー登録用スキーマ（POST /register で使う）
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    last_name: str
    first_name: str
    extension: Optional[str] = None
    direct_phone: Optional[str] = None
    department_id: int  
    position_id: int    

# ユーザー表示用（レスポンスなどで使用）
class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    last_name: str
    first_name: str
    extension: Optional[str] = None
    direct_phone: Optional[str] = None
    is_active: bool
    role: Literal['admin', 'staff']
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {
        # Pydantic v2 で ORM 変換を許可
        "from_attributes": True
    }
