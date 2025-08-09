# app/api/routes/policy_proposal.py
"""
 - 政策案APIルートを定義するモジュール。
 - 新規登録（POST）、一覧取得（GET）、詳細取得（GET）を提供する。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.schemas.policy_proposal.policy_proposal import ProposalCreate, ProposalOut
from app.crud.policy_proposal.policy_proposal import create_proposal
from app.db.session import SessionLocal

# FastAPIのルーターを初期化
router = APIRouter(prefix="/policy-proposals", tags=["PolicyProposals"])

# DBセッションをリクエストごとに生成・提供する関数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # リクエスト処理が終わると、自動的にセッションをクローズ


""" ------------------------
 政策案関連エンドポイント
------------------------ """

# 新規政策案の登録用エンドポイント
@router.post("/", response_model=ProposalOut)
def post_policy_proposal(payload: ProposalCreate, db: Session = Depends(get_db)):
    """
    政策案を新規登録する。
    - status が 'published' の場合は published_at を自動セット（JST）
    - タグ・添付は別APIで登録（このエンドポイントでは扱わない）
    """
    proposal = create_proposal(db=db, data=payload)
    return proposal


# 政策案の一覧取得（簡易検索・ページング付き）
# @router.get("/", response_model=list[ProposalOut])
# def get_policy_proposals(
#     status: str | None = Query(None, description="draft / published / archived のいずれか"),
#     q: str | None = Query(None, description="タイトル・本文の部分一致"),
#     offset: int = Query(0, ge=0),
#     limit: int = Query(20, ge=1, le=100),
#     db: Session = Depends(get_db),
# ):
#     """
#     政策案の一覧を取得する。
#     - status でのフィルタ
#     - タイトル/本文の部分一致検索
#     - created_at の降順で返却
#     """
#     rows = list_proposals(db=db, status_filter=status, q=q, offset=offset, limit=limit)
#     return rows


# # 政策案の詳細取得
# @router.get("/{proposal_id}", response_model=ProposalOut)
# def get_policy_proposal_detail(proposal_id: str, db: Session = Depends(get_db)):
#     """
#     主キー（UUID文字列）を指定して政策案の詳細を取得する。
#     """
#     proposal = get_proposal(db=db, proposal_id=proposal_id)
#     if not proposal:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy proposal not found")
#     return proposal