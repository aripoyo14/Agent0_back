# app/api/routes/policy_proposal.py
"""
 - 政策案APIルートを定義するモジュール。
 - 新規登録（POST）、一覧取得（GET）、詳細取得（GET）を提供する。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Request, status
from sqlalchemy.orm import Session
from app.schemas.policy_proposal.policy_proposal import ProposalCreate, ProposalOut, AttachmentOut
from app.crud.policy_proposal.policy_proposal import create_proposal, create_attachment
from app.models.policy_proposal.policy_proposal_attachments import PolicyProposalAttachment
from app.db.session import SessionLocal
from app.core.blob import upload_binary_to_blob
from uuid import UUID, uuid4
import os

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
def post_policy_proposal_with_attachments(
    title: str = Form(...),
    body: str = Form(...),
    published_by_user_id: str = Form(...),
    status: str = Form("draft"),
    files: list[UploadFile] | None = File(None),
    db: Session = Depends(get_db),
):

    """
    新規政策案の登録用エンドポイント
    - title: 政策案のタイトル
    - body: 政策案の本文
    - published_by_user_id: 政策案の公開者のユーザーID
    - status: 政策案のステータス
    - files: 添付ファイル
    """

    # 1) 政策案を作成
    payload = ProposalCreate(
        title=title,
        body=body,
        published_by_user_id=UUID(published_by_user_id),
        status=status,  # "draft" | "published" | "archived"
    )
    proposal = create_proposal(db=db, data=payload)

    # 2) 添付（任意・複数）
    if files:
        attachments_out: list[AttachmentOut] = []
        for f in files:
            extension = os.path.splitext(f.filename)[1]
            blob_name = f"policy_attachments/{proposal.id}/{uuid4()}{extension}"
            file_bytes = f.file.read()
            file_url = upload_binary_to_blob(file_bytes, blob_name)

            att = create_attachment(
                db,
                policy_proposal_id=str(proposal.id),
                file_name=f.filename,
                file_url=file_url,
                file_type=f.content_type,
                file_size=len(file_bytes) if file_bytes is not None else None,
                uploaded_by_user_id=str(payload.published_by_user_id),
            )
            # Pydantic化はレスポンス時に自動で行われるため、ここでは収集のみ
            attachments_out.append(att)  # type: ignore

        # 3) 返却用に proposal へアタッチメントを載せる
        # SQLAlchemy オブジェクトにリストを紐付けて返すと、from_attributesでシリアライズされる
        proposal.attachments = attachments_out  # type: ignore[attr-defined]

    return proposal



# 添付ファイルのアップロード（1件）
# @router.post("/{proposal_id}/attachments", response_model=AttachmentOut)
# def upload_attachment(
#     proposal_id: str,
#     file: UploadFile = File(...),
#     uploaded_by_user_id: str | None = None,
#     db: Session = Depends(get_db),
# ):
#     # Blob名はUUIDに拡張子を付けるなどして衝突回避
#     extension = os.path.splitext(file.filename)[1]
#     blob_name = f"policy_attachments/{proposal_id}/{uuid4()}{extension}"

#     # Azure Blobへアップロード
#     file_bytes = file.file.read()
#     file_url = upload_binary_to_blob(file_bytes, blob_name)

#     # DBへメタ情報を保存
#     attachment = create_attachment(
#         db,
#         policy_proposal_id=proposal_id,
#         file_name=file.filename,
#         file_url=file_url,
#         file_type=file.content_type,
#         file_size=len(file_bytes),
#         uploaded_by_user_id=uploaded_by_user_id,
#     )
#     return attachment





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