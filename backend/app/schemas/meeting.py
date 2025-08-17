from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from fastapi import UploadFile

class MeetingCreate(BaseModel):
    """面談作成用スキーマ"""
    meeting_date: date
    title: str = Field(..., min_length=1, max_length=255)
    summary: Optional[str] = None
    organized_by_user_id: str
    participant_user_ids: Optional[List[str]] = None
    participant_expert_ids: Optional[List[str]] = None
    evaluation: Optional[int] = Field(None, ge=1, le=5, description="評価値（1-5）")
    stance: Optional[int] = Field(None, description="スタンス値")

class MeetingUpdate(BaseModel):
    """面談更新用スキーマ"""
    meeting_date: Optional[date] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    summary: Optional[str] = None
    minutes_url: Optional[str] = None
    evaluation: Optional[int] = Field(None, ge=1, le=5, description="評価値（1-5）")
    stance: Optional[int] = Field(None, description="スタンス値")

class MeetingResponse(BaseModel):
    """面談レスポンス用スキーマ"""
    id: str
    meeting_date: date
    title: str
    summary: Optional[str] = None
    minutes_url: Optional[str] = None
    evaluation: Optional[int] = None
    stance: Optional[int] = None
    organized_by_user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MinutesUploadRequest(BaseModel):
    """議事録アップロード用スキーマ"""
    meeting_id: str
    expert_id: Optional[str] = None
    tag_ids: Optional[List[int]] = None

class MinutesUploadResponse(BaseModel):
    """議事録アップロードレスポンス用スキーマ"""
    success: bool
    meeting_id: str
    minutes_url: str
    message: str
    vectorization_result: Optional[dict] = None

# 評価関連スキーマ
class MeetingEvaluationCreate(BaseModel):
    """面談評価作成用スキーマ（既存カラム使用）"""
    evaluation: int = Field(..., ge=1, le=5, description="評価値（1-5）")
    stance: Optional[int] = Field(None, description="スタンス値")

class MeetingEvaluationUpdate(BaseModel):
    """面談評価更新用スキーマ（既存カラム使用）"""
    evaluation: Optional[int] = Field(None, ge=1, le=5, description="評価値（1-5）")
    stance: Optional[int] = Field(None, description="スタンス値")

class MeetingEvaluationResponse(BaseModel):
    """面談評価レスポンス用スキーマ（既存カラム使用）"""
    id: str
    meeting_date: date
    title: str
    evaluation: int
    stance: Optional[int] = None
    updated_at: datetime

    class Config:
        from_attributes = True


