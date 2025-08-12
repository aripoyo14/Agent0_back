<<<<<<< HEAD
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from app.db.base_class import Base
import uuid
=======
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.mysql import CHAR

from app.db.base_class import Base


JST = timezone(timedelta(hours=9))
>>>>>>> 67a68b0c9a05eb878fb7d3003455b13818397e09


class Company(Base):
    __tablename__ = "companies"

<<<<<<< HEAD
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sansan_company_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
=======
    id = Column(CHAR(36), primary_key=True)
    sansan_company_id = Column(String(255))
    name = Column(String(255), index=True)
>>>>>>> 67a68b0c9a05eb878fb7d3003455b13818397e09
    postal_code = Column(String(20))
    address = Column(Text)
    prefecture = Column(String(50))
    city = Column(String(100))
    street = Column(String(100))
    building = Column(String(100))
    tel = Column(String(30))
    fax = Column(String(30))
    url = Column(Text)
<<<<<<< HEAD
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
=======
    created_at = Column(DateTime, default=lambda: datetime.now(JST))
    updated_at = Column(DateTime, default=lambda: datetime.now(JST), onupdate=lambda: datetime.now(JST))
>>>>>>> 67a68b0c9a05eb878fb7d3003455b13818397e09


