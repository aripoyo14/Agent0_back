# app/api/routes/policy_proposal_comment.py
"""
 - 政策案コメントAPIルートを定義するモジュール。
 - コメント投稿（POST）を受け取り、バリデーション・DB登録処理を行う。
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.schemas.policy_proposal_comment import (
    PolicyProposalCommentCreate,
    PolicyProposalCommentResponse,
    PolicyWithComments
)
from app.crud.policy_proposal.policy_proposal_comment import (
    create_comment,
    get_comment_by_id,
    list_comments_by_policy_proposal_id,
    list_comments_for_policies_by_user
)
from app.db.session import SessionLocal


# FastAPIのルーターを初期化
router = APIRouter(prefix="/policy-proposal-comments", tags=["PolicyProposalComments"])

# DBセッションをリクエストごとに生成・提供する関数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


""" ------------------------
 コメント関連エンドポイント
------------------------ """

# 新規コメント投稿用のエンドポイント
@router.post("/", response_model=PolicyProposalCommentResponse)
def post_comment(comment_in: PolicyProposalCommentCreate, db: Session = Depends(get_db)):
    """
    政策案に対するコメントを新規投稿する。
    """
    comment = create_comment(db=db, comment_in=comment_in)
    return comment

# 単一コメント取得
@router.get("/{comment_id}", response_model=PolicyProposalCommentResponse)
def get_comment(comment_id: str, db: Session = Depends(get_db)):
    """
    単一コメントを取得する。
    """
    comment = get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment

# 特定の政策案IDに紐づくコメント一覧取得
@router.get("/by-proposal/{policy_proposal_id}", response_model=list[PolicyProposalCommentResponse])
def list_comments(policy_proposal_id: str, db: Session = Depends(get_db), limit: int = 50, offset: int = 0):
    """
    特定の政策案IDに紐づくコメント一覧を取得する。
    """
    return list_comments_by_policy_proposal_id(db, policy_proposal_id, limit=limit, offset=offset)

# 指定ユーザーが投稿した政策案に紐づくコメント一覧を取得
@router.get("/by-user/{user_id}", response_model=list[PolicyWithComments])
def list_comments_for_user_policies(
    user_id: str,
    db: Session = Depends(get_db),
    limit: int = 20,
    offset: int = 0
):
    """
    指定ユーザーが作成した政策案に投稿されたコメント一覧を取得する。
    政策案ごとにコメント本文も含めて返却。
    """
    results = list_comments_for_policies_by_user(db, user_id, limit=limit, offset=offset)
    if not results:
        raise HTTPException(status_code=404, detail="No policies or comments found for this user")
    return results