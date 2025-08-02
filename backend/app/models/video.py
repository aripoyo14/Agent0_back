from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.sql import func
from app.db.base_class import Base
import uuid

class Video(Base):
    __tablename__ = "videos"

    video_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)

    video_url = Column(Text, nullable=False)
    thumbnail_url = Column(Text, nullable=True)

    upload_date = Column(DateTime, default=func.now())
    club_type = Column(VARCHAR(50), nullable=True)
    swing_type = Column(VARCHAR(50), nullable=True)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
