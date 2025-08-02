from app.models.user import User  # まだ未作成でもOK
from app.models.coach import Coach
## from app.models.video import Video
from sqlalchemy import Column, Integer, String, Date, Text, TIMESTAMP
from .database import Base
import uuid
from datetime import datetime

class Coach(Base):
    __tablename__ = "coache"

    coach_id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))   # UUIDとして生成
    usertype = Column(String(50))
    coachname = Column(String(255))
    email = Column(String(255), unique=True)
    birthday = Column(Date)
    sex = Column(String(50))
    SNS_handle_instagram = Column(String(255))
    SNS_handle_X = Column(String(255))
    SNS_handle_youtube = Column(String(255))
    SNS_handle_facebook = Column(String(255))
    SNS_handle_tiktok = Column(String(255))
    password_hash = Column(String(255))
    line_user_id = Column(String(255), unique=True)
    profile_picture_url = Column(Text)
    bio = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)  # 作成日時
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新日時
    hourly_rate = Column(Integer)
    location_id = Column(String(36))  # UUIDとして文字列
    golf_exp = Column(Integer)
    certification = Column(String(100))
    setting_1 = Column(String(50))
    setting_2 = Column(String(50))
    setting_3 = Column(String(50))
    Lesson_rank = Column(String(50))

class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    birthday = Column(Date)
    line_user_id = Column(String(255), unique=True)
    profile_picture_url = Column(Text)
    bio = Column(Text)
    golf_score_ave = Column(Integer)
    golf_exp = Column(Integer)
    zip_code = Column(String(20))
    state = Column(String(100))
    address1 = Column(String(255))
    address2 = Column(String(255))
    sport_exp = Column(String(255))
    industry = Column(String(100))
    job_title = Column(String(100))
    position = Column(String(100))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)