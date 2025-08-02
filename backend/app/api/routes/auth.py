from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.auth import LoginRequest, TokenResponse
from app.core.security import verify_password, create_access_token
from app.crud.coach import get_by_email as get_coach_by_email
from app.crud.user import get_by_email_and_verify_password
from app.db.session import SessionLocal
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["Auth"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Coachログイン
@router.post("/coach/login", response_model=TokenResponse)
def login_coach(login: LoginRequest, db: Session = Depends(get_db)):
    coach = get_coach_by_email(db, email=login.email)
    if not coach or not verify_password(login.password, coach.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token(
        data={"sub": coach.coach_id},  # "sub" = subject
        expires_delta=timedelta(minutes=30)
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ✅ Userログイン
@router.post("/user/login", response_model=TokenResponse)
def login_user(login: LoginRequest, db: Session = Depends(get_db)):
    user = get_by_email_and_verify_password(db, email=login.email, password=login.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(
        data={"sub": str(user.user_id)},
        expires_delta=timedelta(minutes=30)
    )
    return {"access_token": access_token, "token_type": "bearer"}
