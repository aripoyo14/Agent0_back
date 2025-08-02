from sqlalchemy.orm import Session
from app.db.base import Coach
from app.schemas.coach import CoachCreate
import uuid
from datetime import datetime
from typing import Optional

def create_coach(db: Session, coach_in: CoachCreate, password_hash: str) -> Coach:
    coach = Coach(
        coach_id=str(uuid.uuid4()),
        usertype=coach_in.usertype,
        coachname=coach_in.coachname,
        email=coach_in.email,
        birthday=coach_in.birthday,
        sex=coach_in.sex,
        SNS_handle_instagram=coach_in.SNS_handle_instagram,
        SNS_handle_X=coach_in.SNS_handle_X,
        SNS_handle_youtube=coach_in.SNS_handle_youtube,
        SNS_handle_facebook=coach_in.SNS_handle_facebook,
        SNS_handle_tiktok=coach_in.SNS_handle_tiktok,
        password_hash=password_hash,
        line_user_id=coach_in.line_user_id,
        profile_picture_url=coach_in.profile_picture_url,
        bio=coach_in.bio,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        hourly_rate=coach_in.hourly_rate,
        location_id=coach_in.location_id,
        golf_exp=coach_in.golf_exp,
        certification=coach_in.certification,
        setting_1=coach_in.setting_1,
        setting_2=coach_in.setting_2,
        setting_3=coach_in.setting_3,
        Lesson_rank=coach_in.Lesson_rank,
    )
    db.add(coach)
    db.commit()
    db.refresh(coach)
    return coach

def get_by_email(db: Session, email: str) -> Optional[Coach]:
    return db.query(Coach).filter(Coach.email == email).first()

