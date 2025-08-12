from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import date, datetime
from uuid import UUID


class ExpertCreate(BaseModel):
    last_name: str
    first_name: str
    company_name: str  # 入力値として受け取り、DBではcompany_idに解決
    department: str
    email: EmailStr
    password: str = Field(min_length=8)


class ExpertOut(BaseModel):
    id: UUID
    last_name: str
    first_name: str
    company_id: Optional[UUID] = None
    department: Optional[str] = None
    email: EmailStr
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


