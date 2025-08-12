from sqlalchemy.orm import Session
from typing import Optional
from uuid import uuid4

from app.models.company import Company


def get_company_by_name(db: Session, name: str) -> Optional[Company]:
    return db.query(Company).filter(Company.name == name).first()


def get_or_create_company_by_name(db: Session, name: str) -> Company:
    """会社名で検索し、なければ最小情報で新規作成して返す。
    - sansan_company_id は暫定ID（manual_<uuid>）を採番
    """
    company = get_company_by_name(db, name)
    if company:
        return company

    company = Company(
        id=str(uuid4()),
        sansan_company_id=f"manual_{uuid4().hex}",
        name=name,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


