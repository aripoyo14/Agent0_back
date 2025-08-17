from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Date, Integer
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from datetime import datetime, timezone, timedelta
import uuid

# 日本標準時（JST）
JST = timezone(timedelta(hours=9))

class Meeting(Base):
    """
    - 面談（会議）の情報を格納するテーブル
    - 議事録のURLも含む
    """
    __tablename__ = "meetings"

    # 主キー：UUID
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 会議の日付
    meeting_date = Column(Date, nullable=False)

    # 会議のタイトル
    title = Column(String(255), nullable=False)

    # 会議の概要
    summary = Column(Text, nullable=True)

    # 議事録のURL（OneDrive経由またはアップロード）
    minutes_url = Column(Text, nullable=True)

    # 評価値（1-5）
    evaluation = Column(Integer, nullable=True, default=None)

    # スタンス値
    stance = Column(Integer, nullable=True, default=None)

    # 会議を主催したユーザーのID（外部キー）
    organized_by_user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)

    # 作成・更新日時（JST）
    created_at = Column(DateTime, default=lambda: datetime.now(JST))
    updated_at = Column(DateTime, default=lambda: datetime.now(JST), onupdate=lambda: datetime.now(JST))

    # リレーション
    organizer = relationship("User", back_populates="organized_meetings")
    meeting_users = relationship("MeetingUser", back_populates="meeting")
    meeting_experts = relationship("MeetingExpert", back_populates="meeting")


class MeetingUser(Base):
    """
    - 面談参加者（職員）の中間テーブル
    """
    __tablename__ = "meeting_users"

    # 会議ID（外部キー）
    meeting_id = Column(CHAR(36), ForeignKey("meetings.id"), nullable=False, primary_key=True)

    # 参加職員のユーザーID（外部キー）
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, primary_key=True)

    # 作成日時（JST）
    created_at = Column(DateTime, default=lambda: datetime.now(JST))

    # リレーション
    meeting = relationship("Meeting", back_populates="meeting_users")
    user = relationship("User", back_populates="meeting_participations")


class MeetingExpert(Base):
    """
    - 面談参加者（外部有識者）の中間テーブル
    """
    __tablename__ = "meeting_experts"

    # 会議ID（外部キー）
    meeting_id = Column(CHAR(36), ForeignKey("meetings.id"), nullable=False, primary_key=True)

    # 参加外部有識者のID（外部キー）
    expert_id = Column(CHAR(36), ForeignKey("experts.id"), nullable=False, primary_key=True)

    # 作成日時（JST）
    created_at = Column(DateTime, default=lambda: datetime.now(JST))

    # リレーション
    meeting = relationship("Meeting", back_populates="meeting_experts")
    expert = relationship("Expert", back_populates="meeting_participations")
