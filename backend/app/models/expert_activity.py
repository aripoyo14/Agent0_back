from __future__ import annotations

from datetime import datetime, timezone, timedelta

from sqlalchemy import Column, String, Date, DateTime, Text
from sqlalchemy.dialects.mysql import CHAR

from app.db.base_class import Base


JST = timezone(timedelta(hours=9))


class ExpertActivity(Base):
    __tablename__ = "expert_activities"

    id = Column(CHAR(36), primary_key=True)
    expert_id = Column(CHAR(36), index=True, nullable=False)
    event_date = Column(Date)
    event_url = Column(String(500))
    title = Column(String(255))
    description = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(JST))
    updated_at = Column(DateTime, default=lambda: datetime.now(JST), onupdate=lambda: datetime.now(JST))


