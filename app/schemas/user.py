from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    usertype: str = "user" 
    birthday: Optional[date] = None
    line_user_id: Optional[str] = None
    profile_picture_url: Optional[str] = None
    bio: Optional[str] = None
    golf_score_ave: Optional[int] = None
    golf_exp: Optional[int] = None
    zip_code: Optional[str] = None
    state: Optional[str] = None
    address1: Optional[str] = None
    address2: Optional[str] = None
    sport_exp: Optional[str] = None
    industry: Optional[str] = None
    job_title: Optional[str] = None
    position: Optional[str] = None

class UserOut(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
