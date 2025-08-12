from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from uuid import uuid4

from app.models.expert import Expert
from app.schemas.expert import ExpertCreate
from app.crud.company import get_or_create_company_by_name


def create_expert(db: Session, expert_in: ExpertCreate, password_hash: str) -> Expert:
    """
     - 外部有識者を新規作成する。(アイデアソンでの新規ユーザー登録時を想定)
     - 会社名はcomaniesテーブルからidを取得
     - 会社名が存在しなければ、新規作成してidを取得
    """
    
    # 会社名から company を解決。存在しなければ新規作成
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


