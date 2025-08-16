from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from app.models.meeting import Meeting, MeetingUser, MeetingExpert
from app.schemas.meeting import MeetingCreate, MeetingUpdate
import uuid

class MeetingCRUD:
    """面談のCRUD操作"""

    def create_meeting(self, db: Session, meeting_data: MeetingCreate) -> Meeting:
        """面談を作成"""
        meeting = Meeting(
            meeting_date=meeting_data.meeting_date,
            title=meeting_data.title,
            summary=meeting_data.summary,
            organized_by_user_id=meeting_data.organized_by_user_id
        )
        db.add(meeting)
        db.flush()  # IDを取得するためにflush

        # 参加者（職員）を追加
        if meeting_data.participant_user_ids:
            for user_id in meeting_data.participant_user_ids:
                meeting_user = MeetingUser(
                    meeting_id=meeting.id,
                    user_id=user_id
                )
                db.add(meeting_user)

        # 参加者（外部有識者）を追加
        if meeting_data.participant_expert_ids:
            for expert_id in meeting_data.participant_expert_ids:
                meeting_expert = MeetingExpert(
                    meeting_id=meeting.id,
                    expert_id=expert_id
                )
                db.add(meeting_expert)

        db.commit()
        db.refresh(meeting)
        return meeting

    def get_meeting(self, db: Session, meeting_id: str) -> Optional[Meeting]:
        """面談を取得"""
        return db.query(Meeting).filter(Meeting.id == meeting_id).first()

    def get_meetings_by_organizer(self, db: Session, user_id: str) -> List[Meeting]:
        """主催者別の面談一覧を取得"""
        return db.query(Meeting).filter(Meeting.organized_by_user_id == user_id).all()

    def update_meeting(self, db: Session, meeting_id: str, meeting_data: MeetingUpdate) -> Optional[Meeting]:
        """面談を更新"""
        meeting = self.get_meeting(db, meeting_id)
        if not meeting:
            return None

        update_data = meeting_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(meeting, field, value)

        db.commit()
        db.refresh(meeting)
        return meeting

    def update_minutes_url(self, db: Session, meeting_id: str, minutes_url: str) -> Optional[Meeting]:
        """議事録URLを更新"""
        meeting = self.get_meeting(db, meeting_id)
        if not meeting:
            return None

        meeting.minutes_url = minutes_url
        db.commit()
        db.refresh(meeting)
        return meeting

    def delete_meeting(self, db: Session, meeting_id: str) -> bool:
        """面談を削除"""
        meeting = self.get_meeting(db, meeting_id)
        if not meeting:
            return False

        db.delete(meeting)
        db.commit()
        return True

    def get_meeting_participants(self, db: Session, meeting_id: str):
        """面談参加者を取得"""
        meeting_users = db.query(MeetingUser).filter(MeetingUser.meeting_id == meeting_id).all()
        meeting_experts = db.query(MeetingExpert).filter(MeetingExpert.meeting_id == meeting_id).all()
        
        return {
            "users": meeting_users,
            "experts": meeting_experts
        }

meeting_crud = MeetingCRUD()
