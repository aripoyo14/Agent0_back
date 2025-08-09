# app/api/routes/policy_proposal_comment.py
"""
 - 政策案コメントAPIルートを定義するモジュール。
 - コメント投稿（POST）を受け取り、バリデーション・DB登録処理を行う。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.policy_proposal_comment import (
    PolicyProposalCommentCreate,
    PolicyProposalCommentResponse
)
from app.crud.policy_proposal.policy_proposal_comment import create_comment
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