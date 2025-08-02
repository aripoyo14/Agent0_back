# app/schemas/coach.py

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime


class CoachCreate(BaseModel):
    coachname: str
    email: EmailStr
    password: str
    usertype: str = "coach"
    birthday: Optional[date] = None
    sex: Optional[str] = None

    SNS_handle_instagram: Optional[str] = None
    SNS_handle_X: Optional[str] = None
    SNS_handle_youtube: Optional[str] = None
    SNS_handle_facebook: Optional[str] = None
    SNS_handle_tiktok: Optional[str] = None

    line_user_id: Optional[str] = None
    profile_picture_url: Optional[str] = None
    bio: Optional[str] = None
    hourly_rate: Optional[int] = None
    location_id: Optional[str] = None
    golf_exp: Optional[int] = None
    certification: Optional[str] = None
    setting_1: Optional[str] = None
    setting_2: Optional[str] = None
    setting_3: Optional[str] = None
    Lesson_rank: Optional[str] = None

class CoachResponse(BaseModel):
    coach_id: str
    coachname: str
    email: EmailStr
    created_at: str

# app/schemas/coach.py に追加

class CoachOut(BaseModel):
    coach_id: str
    coachname: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2以降は orm_mode → from_attributes
