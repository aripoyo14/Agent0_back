from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class VideoCreate(BaseModel):
    filename: str
    url: str

class VideoOut(BaseModel):
    id: UUID
    filename: str
    url: str
    uploaded_at: datetime

    class Config:
        from_attributes = True
