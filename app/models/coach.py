from sqlalchemy import Column, String, Date, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.mysql import CHAR
from app.db.base_class import Base
from datetime import datetime
import uuid

class Coach(Base):
    __tablename__ = "coaches"

    coach_id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    usertype = Column(String(50), nullable=False)
    coachname = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    line_user_id = Column(String(255), unique=True, nullable=True)
    profile_picture_url = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    birthday = Column(Date, nullable=True)

    # SNS
    SNS_handle_instagram = Column(String(255), nullable=True)
    SNS_handle_X = Column(String(255), nullable=True)
    SNS_handle_youtube = Column(String(255), nullable=True)
    SNS_handle_facebook = Column(String(255), nullable=True)
    SNS_handle_tiktok = Column(String(255), nullable=True)

    # その他
    hourly_rate = Column(Integer, nullable=True)
    location_id = Column(CHAR(36), nullable=True)
    golf_exp = Column(Integer, nullable=True)
    certification = Column(String(100), nullable=True)
    setting_1 = Column(String(50), nullable=True)
    setting_2 = Column(String(50), nullable=True)
    setting_3 = Column(String(50), nullable=True)
    Lesson_rank = Column(String(50), nullable=True)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
