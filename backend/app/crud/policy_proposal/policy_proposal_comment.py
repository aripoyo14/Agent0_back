# app/crud/policy_proposal/policy_proposal_comment.py
"""
 - 政策案コメントに関するDB操作（CRUD）を定義するモジュール。
 - 主に SQLAlchemy を通じて PolicyProposalComment モデルとやり取りする。
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.policy_proposal.policy_proposal_comment import PolicyProposalComment
from app.models.policy_proposal.policy_proposal import PolicyProposal
from app.schemas.policy_proposal_comment import (
    PolicyProposalCommentCreate,
    PolicyWithComments
)
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from typing import Optional, List

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
        is_deleted=False,
        evaluation=comment_in.evaluation,
        stance=comment_in.stance
    )

    # 4. DBに保存
    db.add(comment)
    db.commit()
    db.refresh(comment)

    # 5. 登録済コメントを返却
    return comment

def create_reply(
    db: Session,
    *,
    parent_comment_id: str,
    author_type: str,
    author_id: str,
    comment_text: str,
) -> PolicyProposalComment:
    """
    既存コメントに対する返信を作成する。
    親コメントが論理削除されていても、スレッド履歴のため返信は許可する。
    """
    if author_type not in VALID_AUTHOR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"author_type は {VALID_AUTHOR_TYPES} のいずれかである必要があります。",
        )

    parent = (
        db.query(PolicyProposalComment)
        .filter(PolicyProposalComment.id == parent_comment_id)
        .first()
    )
    if parent is None:
        raise HTTPException(status_code=404, detail="Parent comment not found")

    reply = PolicyProposalComment(
        id=str(uuid4()),
        policy_proposal_id=str(parent.policy_proposal_id),
        author_type=author_type,
        author_id=str(author_id),
        comment_text=comment_text,
        parent_comment_id=str(parent_comment_id),
        posted_at=datetime.now(JST),
        like_count=0,
        is_deleted=False,
        evaluation=None,  # 返信には評価は含めない
        stance=None
    )

    db.add(reply)
    db.commit()
    db.refresh(reply)
    return reply

def get_comment_by_id(db: Session, comment_id: str) -> Optional[PolicyProposalComment]:
    """
    コメントID（UUID文字列）で単一取得。論理削除は除外。
    """
    return (
        db.query(PolicyProposalComment)
        .filter(
            PolicyProposalComment.id == comment_id,
            PolicyProposalComment.is_deleted == False,
        )
        .first()
    )

def list_comments_by_policy_proposal_id(
    db: Session,
    policy_proposal_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
) -> List[PolicyProposalComment]:
    """
    政策案ID（文字列）に紐づくコメント一覧を新しい順で取得。
    論理削除は除外。簡易ページング対応。
    """
    return (
        db.query(PolicyProposalComment)
        .filter(
            PolicyProposalComment.policy_proposal_id == policy_proposal_id,
            PolicyProposalComment.is_deleted == False,
        )
        .order_by(PolicyProposalComment.posted_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

# 追加機能：指定ユーザーが投稿した政策案に紐づくコメント一覧を取得
def list_comments_for_policies_by_user(
    db: Session,
    user_id: str,
    *,
    limit: int = 20,
    offset: int = 0
) -> List[PolicyWithComments]:
    """
    指定ユーザーが作成した政策案ごとに、
    そこに投稿されたコメント一覧を返す。
    """

    # 1. ユーザーが作成した政策案を取得（ページングあり）
    policies = (
        db.query(PolicyProposal)
        .filter(PolicyProposal.published_by_user_id == user_id)
        .order_by(PolicyProposal.published_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    results: List[PolicyWithComments] = []

    # 2. 各政策案に紐づくコメントを取得
    for policy in policies:
        comments = (
            db.query(PolicyProposalComment)
            .filter(
                PolicyProposalComment.policy_proposal_id == str(policy.id),
                PolicyProposalComment.is_deleted == False,
            )
            .order_by(PolicyProposalComment.posted_at.desc())
            .all()
        )

        # 3. 最新コメント日時の取得
        latest_commented_at = (
            db.query(func.max(PolicyProposalComment.posted_at))
            .filter(
                PolicyProposalComment.policy_proposal_id == str(policy.id),
                PolicyProposalComment.is_deleted == False,
            )
            .scalar()
        )

        # 4. スキーマ形式に変換して追加
        results.append(PolicyWithComments(
            policy_proposal_id=policy.id,
            title=policy.title,
            status=policy.status,
            published_at=policy.published_at,
            latest_commented_at=latest_commented_at,
            total_comments=len(comments),
            comments=comments
        ))

    return results


def update_comment_rating(
    db: Session,
    comment_id: str,
    evaluation: Optional[int] = None,
    stance: Optional[int] = None,
) -> Optional[PolicyProposalComment]:
    """
    コメントの評価を更新する。
    評価値の範囲チェックも行う。
    """
    # 評価値の範囲チェック
    if evaluation is not None and (evaluation < 1 or evaluation > 5):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="evaluation は 1-5 の範囲で指定してください。"
        )
    
    if stance is not None and (stance < 1 or stance > 5):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="stance は 1-5 の範囲で指定してください。"
        )
    
    # コメントの存在確認
    comment = get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # 評価を更新
    if evaluation is not None:
        comment.evaluation = evaluation
    if stance is not None:
        comment.stance = stance
    
    # 更新日時を設定 - 一時的にコメントアウト（DBマイグレーション後有効化）
    # comment.updated_at = datetime.now(JST)
    
    db.commit()
    db.refresh(comment)
    return comment