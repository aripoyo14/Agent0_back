from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional, Dict, Any
from app.models.meeting import Meeting, MeetingUser, MeetingExpert
from app.schemas.meeting import MeetingCreate, MeetingUpdate, MeetingEvaluationCreate, MeetingEvaluationUpdate
import uuid

class MeetingCRUD:
    """面談CRUD操作クラス"""
    
    def create(self, db: Session, meeting_data: MeetingCreate) -> Meeting:
        """面談を作成"""
        meeting = Meeting(
            id=str(uuid.uuid4()),
            meeting_date=meeting_data.meeting_date,
            title=meeting_data.title,
            summary=meeting_data.summary,
            organized_by_user_id=meeting_data.organized_by_user_id,
            evaluation=meeting_data.evaluation,
            stance=meeting_data.stance
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
        
        # 参加者を追加
        if meeting_data.participant_user_ids:
            for user_id in meeting_data.participant_user_ids:
                meeting_user = MeetingUser(
                    meeting_id=meeting.id,
                    user_id=user_id
                )
                db.add(meeting_user)
        
        if meeting_data.participant_expert_ids:
            for expert_id in meeting_data.participant_expert_ids:
                meeting_expert = MeetingExpert(
                    meeting_id=meeting.id,
                    expert_id=expert_id
                )
                db.add(meeting_expert)
        
        db.commit()
        return meeting
    
    def get(self, db: Session, meeting_id: str) -> Optional[Meeting]:
        """面談を取得"""
        return db.query(Meeting).filter(Meeting.id == meeting_id).first()
    
    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[Meeting]:
        """面談一覧を取得"""
        return db.query(Meeting).offset(skip).limit(limit).all()
    
    def update(self, db: Session, meeting_id: str, meeting_data: MeetingUpdate) -> Optional[Meeting]:
        """面談を更新"""
        meeting = self.get(db, meeting_id)
        if not meeting:
            return None
        
        update_data = meeting_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(meeting, field, value)
        
        db.commit()
        db.refresh(meeting)
        return meeting
    
    def delete(self, db: Session, meeting_id: str) -> bool:
        """面談を削除"""
        meeting = self.get(db, meeting_id)
        if not meeting:
            return False
        
        db.delete(meeting)
        db.commit()
        return True
    
    def update_minutes_url(self, db: Session, meeting_id: str, minutes_url: str) -> Optional[Meeting]:
        """議事録URLを更新"""
        meeting = self.get(db, meeting_id)
        if not meeting:
            return None
        
        meeting.minutes_url = minutes_url
        db.commit()
        db.refresh(meeting)
        return meeting

    def update_summary(self, db: Session, meeting_id: str, summary: str) -> Optional[Meeting]:
        """面談の要約を更新"""
        meeting = self.get(db, meeting_id)
        if not meeting:
            return None
        
        meeting.summary = summary
        db.commit()
        db.refresh(meeting)
        return meeting

class MeetingEvaluationCRUD:
    """面談評価CRUD操作クラス（既存カラム使用）"""
    
    def update_meeting_evaluation(self, db: Session, meeting_id: str, evaluation_data: MeetingEvaluationCreate) -> Optional[Meeting]:
        """面談評価を更新（既存カラム使用）"""
        meeting = meeting_crud.get(db, meeting_id)
        if not meeting:
            return None
        
        # 評価データを更新
        meeting.evaluation = evaluation_data.evaluation
        meeting.stance = evaluation_data.stance
        
        db.commit()
        db.refresh(meeting)
        return meeting
    
    def get_meeting_evaluation(self, db: Session, meeting_id: str) -> Optional[Meeting]:
        """面談の評価を取得（既存カラム使用）"""
        return meeting_crud.get(db, meeting_id)

# インスタンス化
meeting_crud = MeetingCRUD()
meeting_evaluation_crud = MeetingEvaluationCRUD()
