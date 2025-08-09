# app/crud/policy_proposal/policy_proposal_comment.py
"""
 - 政策案コメントに関するDB操作（CRUD）を定義するモジュール。
 - 主に SQLAlchemy を通じて PolicyProposalComment モデルとやり取りする。
"""

from sqlalchemy.orm import Session
from app.models.policy_proposal.policy_proposal_comment import PolicyProposalComment
from app.schemas.policy_proposal_comment import PolicyProposalCommentCreate
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status

# 日本標準時（JST）
JST = timezone(timedelta(hours=9))

# 有効な投稿者タイプ一覧
VALID_AUTHOR_TYPES = ["admin", "staff", "contributor", "viewer"]

def create_comment(db: Session, comment_in: PolicyProposalCommentCreate) -> PolicyProposalComment:
    """
    新規コメントをDBに登録する処理。
    """

    # 1. 投稿者タイプのバリデーション
    if comment_in.author_type not in VALID_AUTHOR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"author_type は {VALID_AUTHOR_TYPES} のいずれかである必要があります。"
        )

    # 2. 閲覧専用ユーザー（viewer）は投稿禁止
    if comment_in.author_type == "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="閲覧専用ユーザー（viewer）はコメントを投稿できません。"
        )

    # 3. PolicyProposalComment モデルのインスタンスを作成
    comment = PolicyProposalComment(
        id=str(uuid4()),
        policy_proposal_id=str(comment_in.policy_proposal_id),
        author_type=comment_in.author_type,
        author_id=str(comment_in.author_id),
        comment_text=comment_in.comment_text,
        parent_comment_id=str(comment_in.parent_comment_id) if comment_in.parent_comment_id else None,
        posted_at=datetime.now(JST),
        like_count=0,
        is_deleted=False
    )

    # 4. DBに保存
    db.add(comment)
    db.commit()
    db.refresh(comment)

    # 5. 登録済コメントを返却
    return comment