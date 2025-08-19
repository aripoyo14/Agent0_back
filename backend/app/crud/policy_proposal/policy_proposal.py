# app/crud/policy_proposal/policy_proposal.py
"""
 - 政策案に関するDB操作（CRUDのうち作成・取得）を定義するモジュール。
 - 主に SQLAlchemy を通じて PolicyProposal モデルとデータベースをやり取りする。
"""

from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException, status
from datetime import datetime, timezone, timedelta

from app.models.policy_proposal.policy_proposal import PolicyProposal
from app.models.policy_proposal.policy_proposal_comment import PolicyProposalComment
from app.schemas.policy_proposal.policy_proposal import ProposalCreate
from app.models.policy_proposal.policy_proposal_attachments import PolicyProposalAttachment

# 日本時間（JST）のタイムゾーンを定義
JST = timezone(timedelta(hours=9))

# 新規の政策案を登録する関数
def create_proposal(db: Session, data: ProposalCreate) -> PolicyProposal:

    # 1. タイトルの重複チェック
    existing = db.query(PolicyProposal).filter(PolicyProposal.title == data.title).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="同じタイトルの政策案が既に存在します。"
        )

    # 2. PolicyProposalモデルのインスタンスを作成
    proposal = PolicyProposal(
        title=data.title,
        body=data.body,
        status=data.status,  # "draft" | "published" | "archived"
        published_by_user_id=str(data.published_by_user_id),  # CHAR(36) なので文字列化
        published_at=(datetime.now(JST) if data.status == "published" else None),
        created_at=datetime.now(JST),
        updated_at=datetime.now(JST),
    )

    # 3. DBに保存
    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    # 4. 登録した政策案オブジェクトを返す
    return proposal


def create_attachment(
    db: Session,
    *,
    policy_proposal_id: str,
    file_name: str,
    file_url: str,
    file_type: str | None,
    file_size: int | None,
    uploaded_by_user_id: str | None,
) -> PolicyProposalAttachment:
    attachment = PolicyProposalAttachment(
        policy_proposal_id=policy_proposal_id,
        file_name=file_name,
        file_url=file_url,
        file_type=file_type,
        file_size=file_size,
        uploaded_by_user_id=uploaded_by_user_id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def list_attachments_by_policy_proposal_id(
    db: Session,
    *,
    policy_proposal_id: str,
) -> list[PolicyProposalAttachment]:
    """指定した政策案に紐づく添付一覧を返す。"""
    rows = (
        db.query(PolicyProposalAttachment)
        .filter(PolicyProposalAttachment.policy_proposal_id == policy_proposal_id)
        .all()
    )
    return rows


def get_proposal(db: Session, proposal_id: str) -> Optional[PolicyProposal]:
    """
    主キー（UUID文字列）で政策案を1件取得する関数。
    見つからない場合は None を返す。
    政策タグ情報も含めて取得する。
    """
    return (
        db.query(PolicyProposal)
        .options(
            joinedload(PolicyProposal.attachments),
            joinedload(PolicyProposal.policy_tags)
        )
        .filter(PolicyProposal.id == proposal_id)
        .first()
    )


def list_proposals(
    db: Session,
    *,
    status_filter: Optional[str] = None,  # "draft" | "published" | "archived"
    q: Optional[str] = None,              # タイトル/本文の部分一致
    offset: int = 0,
    limit: int = 20,
) -> List[PolicyProposal]:
    """
    政策案の一覧を取得する関数（簡易検索付き）。
     - status でのフィルタ
     - タイトル/本文の部分一致検索
     - 新しい順（created_at DESC）
     - 政策タグ情報も含めて取得する
    """
    qs = db.query(PolicyProposal)

    if status_filter:
        qs = qs.filter(PolicyProposal.status == status_filter)

    if q:
        like = f"%{q}%"
        qs = qs.filter(
            (PolicyProposal.title.ilike(like)) |
            (PolicyProposal.body.ilike(like))
        )

    rows = (
        qs.options(
            joinedload(PolicyProposal.attachments),
            joinedload(PolicyProposal.policy_tags)
        )
        .order_by(PolicyProposal.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows


def get_user_submissions(
    db: Session,
    user_id: str,
    *,
    offset: int = 0,
    limit: int = 20,
) -> List[dict]:
    """
    ログインユーザーが投稿した政策提案の一覧を取得する関数。
    各投稿のコメント数も含めて返す。
    """
    proposals = (
        db.query(PolicyProposal)
        .options(
            joinedload(PolicyProposal.attachments),
            joinedload(PolicyProposal.policy_tags)
        )
        .filter(PolicyProposal.published_by_user_id == user_id)
        .order_by(PolicyProposal.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    results = []
    for proposal in proposals:
        comment_count = (
            db.query(func.count(PolicyProposalComment.id))
            .filter(
                PolicyProposalComment.policy_proposal_id == str(proposal.id),
                PolicyProposalComment.is_deleted == False
            )
            .scalar()
        ) or 0
        
        result = {
            "proposal": proposal,
            "comment_count": comment_count
        }
        results.append(result)
    return results