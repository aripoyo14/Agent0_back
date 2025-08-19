# app/api/routes/policy_proposal.py
"""
 - 政策案APIルートを定義するモジュール。
 - 新規登録（POST）、一覧取得（GET）、詳細取得（GET）を提供する。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Request, status
from sqlalchemy.orm import Session
from app.schemas.policy_proposal.policy_proposal import ProposalCreate, ProposalOut, AttachmentOut, PolicySubmissionHistory
from app.schemas.policy_proposal_comment import PolicyProposalCommentResponse
from app.crud.policy_proposal.policy_proposal import create_proposal, create_attachment, get_proposal, list_proposals, get_user_submissions
from app.models.policy_proposal.policy_proposal_attachments import PolicyProposalAttachment
from app.db.session import SessionLocal
from app.core.blob import upload_binary_to_blob
from app.core.dependencies import get_current_user
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
@router.get("/", response_model=list[ProposalOut])
def get_policy_proposals(
    status: str | None = Query(None, description="draft / published / archived のいずれか"),
    q: str | None = Query(None, description="タイトル・本文の部分一致"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    政策案の一覧を取得する。
    - status でのフィルタ
    - タイトル/本文の部分一致検索
    - created_at の降順で返却
    - 政策タグ情報も含めて返却
    """
    rows = list_proposals(db=db, status_filter=status, q=q, offset=offset, limit=limit)
    return [ProposalOut.from_proposal_with_relations(proposal) for proposal in rows]


# 投稿履歴取得エンドポイント
@router.get("/my-submissions", response_model=dict)
def get_my_submissions(
    offset: int = Query(0, ge=0, description="スキップ件数"),
    limit: int = Query(20, ge=1, le=100, description="取得件数"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    ログインユーザーが投稿した政策提案の履歴を取得する。
    
    ## 機能
    - ログインユーザーが投稿した政策提案の一覧を取得
    - 各投稿のコメント数も含めて返却
    - 投稿日時の降順でソート
    - ページング対応（limit/offset）
    
    ## パラメータ
    - `offset`: スキップ件数（デフォルト: 0）
    - `limit`: 取得件数（デフォルト: 20, 最大: 100）
    
    ## レスポンス
    ```json
    {
        "success": true,
        "data": [
            {
                "id": "uuid",
                "title": "タイトル",
                "content": "本文",
                "policy_themes": ["テーマ1", "テーマ2"],
                "submitted_at": "2024-01-01T00:00:00",
                "status": "submitted",
                "attached_files": [
                    {
                        "id": "uuid",
                        "file_name": "ファイル名.pdf",
                        "file_url": "https://..."
                    }
                ],
                "comment_count": 5
            }
        ]
    }
    ```
    
    ## 使用例
    ```
    GET /api/policy-proposals/my-submissions?limit=10&offset=0
    ```
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザーIDが取得できませんでした"
            )
        
        submissions_data = get_user_submissions(
            db=db,
            user_id=user_id,
            offset=offset,
            limit=limit
        )
        
        submissions = []
        for submission in submissions_data:
            proposal = submission["proposal"]
            comment_count = submission["comment_count"]
            submission_history = PolicySubmissionHistory.from_proposal_with_comment_count(
                proposal=proposal,
                comment_count=comment_count
            )
            submissions.append(submission_history)
        
        return {
            "success": True,
            "data": submissions
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"投稿履歴の取得に失敗しました: {str(e)}"
        }


# 政策案の詳細取得
@router.get("/{proposal_id}", response_model=ProposalOut)
def get_policy_proposal_detail(proposal_id: str, db: Session = Depends(get_db)):
    """
    主キー（UUID文字列）を指定して政策案の詳細を取得する。
    政策タグ情報も含めて返却する。
    """
    proposal = get_proposal(db=db, proposal_id=proposal_id)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy proposal not found")
    return ProposalOut.from_proposal_with_relations(proposal)


# 政策案のコメント一覧取得
@router.get("/{proposal_id}/comments", response_model=list[PolicyProposalCommentResponse])
def get_policy_proposal_comments(
    proposal_id: str, 
    db: Session = Depends(get_db), 
    limit: int = 50, 
    offset: int = 0
):
    """
    特定の政策案IDに紐づくコメント一覧を取得する。
    
    ## 機能
    - 指定された政策案に投稿されたコメント一覧を取得
    - 投稿日時の降順でソート
    - ページング対応（limit/offset）
    
    ## パラメータ
    - `proposal_id`: 政策案のUUID
    - `limit`: 取得件数（デフォルト: 50, 最大: 100）
    - `offset`: スキップ件数（デフォルト: 0）
    
    ## レスポンス
    - 論理削除されたコメントは除外
    - 空の場合は空配列を返却
    
    ## 使用例
    ```
    GET /api/policy-proposals/11111111-2222-3333-4444-555555555555/comments?limit=20&offset=0
    ```
    """
    from app.crud.policy_proposal.policy_proposal_comment import list_comments_by_policy_proposal_id
    return list_comments_by_policy_proposal_id(db, proposal_id, limit=limit, offset=offset)