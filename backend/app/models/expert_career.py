from __future__ import annotations

from datetime import datetime, timezone, timedelta, date as date_type

from sqlalchemy import Column, String, Date, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.dialects.mysql import CHAR

from app.db.base_class import Base


JST = timezone(timedelta(hours=9))


class ExpertCareer(Base):
    __tablename__ = "expert_careers"

    id = Column(CHAR(36), primary_key=True)
    expert_id = Column(CHAR(36), ForeignKey("experts.id"), index=True, nullable=False)
    bizcard_id = Column(String(255))
    company_name = Column(String(255))
    department_name = Column(String(255))
    title = Column(String(255))
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_current = Column(Boolean, default=False)
    description = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(JST))
    updated_at = Column(DateTime, default=lambda: datetime.now(JST), onupdate=lambda: datetime.now(JST))


