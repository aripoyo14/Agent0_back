# app/api/routes/user.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserOut
from app.crud import user as crud_user
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.core.dependencies import get_current_user
from app.db.base import User

router = APIRouter(prefix="/users", tags=["Users"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/signup", response_model=UserOut)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    if crud_user.get_by_email(db, email=user_in.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = get_password_hash(user_in.password)
    user = crud_user.create_user(db, user_in, hashed_pw)
    return user

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user