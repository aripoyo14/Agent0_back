# app/models/policy_proposal/policy_proposal_attachment.py
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from datetime import datetime, timezone, timedelta
import uuid

# 日本標準時（JST）
JST = timezone(timedelta(hours=9))

class PolicyProposalAttachment(Base):
    """
    - 政策案に紐づく添付ファイル情報を格納するモデル。
    - 実ファイルの保存はAzure Blobを想定し、ここではメタ情報のみ保持。
    """

    __tablename__ = "policy_proposal_attachments"

    # 主キー：UUID
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 対象の政策案ID（外部キー、CASCADEはDB定義側で付与推奨）
    policy_proposal_id = Column(CHAR(36), ForeignKey("policy_proposals.id"), nullable=False, index=True)

    # 画面表示用のファイル名（例：報告書.pdf）
    file_name = Column(String(255), nullable=False)

    # ストレージ上の保存URL（署名付き/公開URLを想定）
    file_url = Column(String(512), nullable=False)

    # MIMEタイプ（例：application/pdf） 任意
    file_type = Column(String(50), nullable=True)

    # ファイルサイズ（バイト） 任意
    file_size = Column(Integer, nullable=True)

    # アップロード実行ユーザー（users.id） 任意
    uploaded_by_user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=True, index=True)

    # アップロード日時（JST）
    uploaded_at = Column(DateTime, default=lambda: datetime.now(JST))

    # 親へのリレーション（逆参照）
    proposal = relationship("PolicyProposal", back_populates="attachments")