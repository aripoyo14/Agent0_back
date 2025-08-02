# app/crud/user.py
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
import uuid
from datetime import datetime
from typing import Optional
from app.core.security import verify_password

def create_user(db: Session, user_in: UserCreate, password_hash: str) -> User:
    user = User(
        user_id=str(uuid.uuid4()),
        username=user_in.username,
        email=user_in.email,
        password_hash=password_hash,
        birthday=user_in.birthday,
        line_user_id=user_in.line_user_id,
        profile_picture_url=user_in.profile_picture_url,
        bio=user_in.bio,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        golf_score_ave=user_in.golf_score_ave,
        golf_exp=user_in.golf_exp,
        zip_code=user_in.zip_code,
        state=user_in.state,
        address1=user_in.address1,
        address2=user_in.address2,
        sport_exp=user_in.sport_exp,
        industry=user_in.industry,
        job_title=user_in.job_title,
        position=user_in.position,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def get_by_email_and_verify_password(db: Session, email: str, password: str):
    user = get_by_email(db, email=email)
    if user and verify_password(password, user.password_hash):
        return user
    return None
