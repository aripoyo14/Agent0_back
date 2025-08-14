from __future__ import annotations
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from uuid import uuid4
from typing import Optional

from app.models.expert import Expert
from app.models.company import Company
from app.schemas.expert import ExpertCreate
from app.crud.company import get_or_create_company_by_name


def get_company_by_name(db: Session, company_name: str) -> Optional[Company]:
    return db.query(Company).filter(Company.name == company_name).first()


def get_expert_by_name_and_company(db: Session, last_name: str, first_name: str, company_id: Optional[str]) -> Optional[Expert]:
    q = db.query(Expert).filter(Expert.last_name == last_name, Expert.first_name == first_name)
    if company_id:
        q = q.filter(Expert.company_id == company_id)
    return q.first()


def create_expert(db: Session, expert_in: ExpertCreate, password_hash: str) -> Expert:
    """
    外部有識者を新規作成する。(アイデアソンでの新規ユーザー登録時を想定)
    会社名はcompaniesテーブルからidを取得
    会社名が存在しなければ、新規作成してidを取得
    """

    company = get_or_create_company_by_name(db, expert_in.company_name)

    expert = Expert(
        id=str(uuid4()),
        sansan_person_id=None,
        last_name=expert_in.last_name,
        first_name=expert_in.first_name,
        company_id=company.id,
        department=expert_in.department,
        email=expert_in.email,
        password_hash=password_hash,
    )

    db.add(expert)
    db.commit()
    db.refresh(expert)
    return expert

# メールアドレスでexpertを検索する関数
def get_expert_by_email(db: Session, email: str):
    return db.query(Expert).filter(Expert.email == email).first()