from sqlalchemy import Column, String, Text, Date, DateTime, Integer
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.sql import func
from app.db.base_class import Base
import uuid

class User(Base):
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    usertype = Column(VARCHAR(50), nullable=False, default="user")
    username = Column(VARCHAR(255), nullable=False)
    email = Column(VARCHAR(255), nullable=False, unique=True)
    password_hash = Column(VARCHAR(255), nullable=False)
    line_user_id = Column(VARCHAR(255), unique=True, nullable=True)

    profile_picture_url = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    birthday = Column(Date, nullable=True)
    golf_score_ave = Column(Integer, nullable=True)
    golf_exp = Column(Integer, nullable=True)

    zip_code = Column(VARCHAR(10), nullable=True)
    state = Column(VARCHAR(50), nullable=True)
    address1 = Column(VARCHAR(255), nullable=True)
    address2 = Column(VARCHAR(255), nullable=True)

    sport_exp = Column(VARCHAR(100), nullable=True)
    industry = Column(VARCHAR(100), nullable=True)
    job_title = Column(VARCHAR(100), nullable=True)
    position = Column(VARCHAR(100), nullable=True)
