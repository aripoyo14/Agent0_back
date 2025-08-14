from __future__ import annotations

from datetime import datetime, timezone, timedelta

from sqlalchemy import Column, String, Enum, Date, DateTime
from sqlalchemy.dialects.mysql import CHAR, DECIMAL

from app.db.base_class import Base


JST = timezone(timedelta(hours=9))


class Expert(Base):
    __tablename__ = "experts"

    id = Column(CHAR(36), primary_key=True)
    sansan_person_id = Column(String(100))
    last_name = Column(String(50), index=True, nullable=False)
    first_name = Column(String(50), index=True, nullable=False)
    company_id = Column(CHAR(36), index=True)
    department = Column(String(100))
    title = Column(String(100))
    email = Column(String(255))
    password_hash = Column(String(255))
    mobile = Column(String(20))
    contact_frequency = Column(String(11))
    last_contact_date = Column(Date)
    overall_relevance = Column(DECIMAL(3, 2))
    policy_relevance = Column(DECIMAL(3, 2))
    expertise_score = Column(DECIMAL(3, 2))
    memo = Column(String)
    sansan_sync_status = Column(Enum('pending', 'synced', 'error', name='sansan_sync_status'))
    sync_error_message = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(JST))
    updated_at = Column(DateTime, default=lambda: datetime.now(JST), onupdate=lambda: datetime.now(JST))
    role = Column(Enum('contributor', 'viewer', name='expert_role'), default='contributor')


