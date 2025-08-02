from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.coach import CoachCreate, CoachOut
from app.crud import coach as crud_coach
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.core.dependencies import get_current_coach

router = APIRouter(prefix="/coach", tags=["Coach"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/signup", response_model=CoachOut)
def register_coach(coach_in: CoachCreate, db: Session = Depends(get_db)):
    if crud_coach.get_by_email(db, email=coach_in.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = get_password_hash(coach_in.password)
    coach = crud_coach.create_coach(db, coach_in, hashed_pw)
    return coach

@router.get("/me", response_model=CoachOut)
def get_current_coach_info(current_coach: CoachOut = Depends(get_current_coach)):
    return current_coach
