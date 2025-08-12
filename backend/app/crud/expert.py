from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.expert import Expert


def get_company_by_name(db: Session, company_name: str) -> Optional[Company]:
    return db.query(Company).filter(Company.name == company_name).first()


def get_expert_by_name_and_company(db: Session, last_name: str, first_name: str, company_id: Optional[str]) -> Optional[Expert]:
    q = db.query(Expert).filter(Expert.last_name == last_name, Expert.first_name == first_name)
    if company_id:
        q = q.filter(Expert.company_id == company_id)
    return q.first()


