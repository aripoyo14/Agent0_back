from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.expert import ExpertCreate, ExpertOut
from app.crud.expert import create_expert
from app.db.session import get_db
from app.core.security import hash_password


router = APIRouter(prefix="/experts", tags=["Experts"])


@router.post("/register", response_model=ExpertOut)
def register_expert(expert_in: ExpertCreate, db: Session = Depends(get_db)):
    password_hash = hash_password(expert_in.password)
    expert = create_expert(db=db, expert_in=expert_in, password_hash=password_hash)
    return expert


