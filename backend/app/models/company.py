from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from app.db.base_class import Base
import uuid


class Company(Base):
    __tablename__ = "companies"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sansan_company_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    postal_code = Column(String(20))
    address = Column(Text)
    prefecture = Column(String(50))
    city = Column(String(100))
    street = Column(String(100))
    building = Column(String(100))
    tel = Column(String(30))
    fax = Column(String(30))
    url = Column(Text)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


