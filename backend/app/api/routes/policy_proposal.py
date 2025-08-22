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
from app.core.blob import upload_binary_to_blob, delete_blob
from app.core.dependencies import get_current_user
from uuid import UUID, uuid4
import os
from app.core.security.audit import AuditService, AuditEventType
from app.core.security.audit.decorators import audit_log, audit_log_sync
from app.models.user import User

# 🔒 権限チェック用のインポートを追加
from app.core.dependencies import require_permissions  # この行を追加
from app.core.security.rbac.permissions import Permission

import anyio  # 追加

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
@audit_log(
    event_type=AuditEventType.DATA_CREATE,
    resource="policy_proposal",
    action="create"
)
# @require_user_permissions(Permission.POLICY_CREATE)  # 🔒 この行をコメントアウト
async def post_policy_proposal_with_attachments(
    http_request: Request,
    title: str = Form(...),
    body: str = Form(...),
    proposal_status: str = Form("draft"),  # 🔒 status → proposal_statusにリネーム
    files: list[UploadFile] | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.POLICY_CREATE)),  #  依存関係で権限チェック
):

    """
    新規政策案の登録用エンドポイント
    - title: 政策案のタイトル
    - body: 政策案の本文
    - proposal_status: 政策案のステータス
    - files: 添付ファイル
    
    権限: POLICY_CREATE が必要
    """

    # 1) 政策案を作成
    try:
        published_by_user_id = UUID(str(current_user.id))
    except ValueError as e:
        # logger.error(f"無効なユーザーID形式: {current_user.id}, エラー: {e}") # loggerが定義されていないためコメントアウト
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なユーザーID形式です"
        )
    
    payload = ProposalCreate(
        title=title,
        body=body,
        published_by_user_id=published_by_user_id,  # 🔒 文字列をUUIDに変換
        status=proposal_status,  #  変数名を修正
    )
    
    # 2) attachments_outを関数冒頭で初期化
    attachments_out: list[AttachmentOut] = []
    uploaded_blobs = []  # クリーンアップ用（Blob名とURL）
    
    try:
        # まとめてやるなら begin ブロック
        with db.begin():
            # 1) 政策案を作成
            proposal = create_proposal(db=db, data=payload)
            
            # 2) 添付（任意・複数）
            if files:
                for f in files:
                    try:
                        extension = os.path.splitext(f.filename)[1]
                        blob_name = f"policy_attachments/{proposal.id}/{uuid4()}{extension}"
                        
                        # 🔄 非同期ファイル読み取り
                        file_bytes = await f.read()
                        
                        # 🔄 anyio.to_thread.run_syncで安全なスレッド実行
                        file_url = await anyio.to_thread.run_sync(
                            upload_binary_to_blob, 
                            file_bytes, 
                            blob_name
                        )
                        
                        # クリーンアップ用に記録
                        uploaded_blobs.append((blob_name, file_url))
                        
                        att = create_attachment(
                            db,
                            policy_proposal_id=str(proposal.id),
                            file_name=f.filename,
                            file_url=file_url,
                            file_type=f.content_type,
                            file_size=len(file_bytes) if file_bytes is not None else None,
                            uploaded_by_user_id=str(current_user.id),
                        )
                        attachments_out.append(att)
                        
                    except Exception as file_error:
                        # 個別ファイルのエラーをログに記録
                        # logger.error(f"ファイル {f.filename} の処理でエラー: {file_error}") # loggerが定義されていないためコメントアウト
                        
                        # 3) アップロードされたBlobファイルをクリーンアップ
                        if uploaded_blobs:
                            await _cleanup_uploaded_blobs(uploaded_blobs)
                        
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"ファイルアップロード中にエラーが発生しました: {file_error}"
                        )
            
            # 3) 返却用に proposal へアタッチメントを載せる
            proposal.attachments = attachments_out  # type: ignore[attr-defined]
            
        # ここで commit 済み
        return proposal
        
    except Exception as e:
        # 必要なら Blob の削除処理を呼ぶ
        if uploaded_blobs:
            await _cleanup_uploaded_blobs(uploaded_blobs)
        
        # logger.error(f"政策案作成でエラー: {e}") # loggerが定義されていないためコメントアウト
        raise HTTPException(
            status_code=500, 
            detail="政策案の作成に失敗しました"
        ) from e



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
@audit_log(
    event_type=AuditEventType.DATA_READ,
    resource="policy_proposal",
    action="list"
)
async def get_policy_proposals(
    http_request: Request,
    status: str | None = Query(None, description="draft / published / archived のいずれか"),
    q: str | None = Query(None, description="タイトル・本文の部分一致"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_permissions(Permission.POLICY_READ)),  # 🔒 認証のみ
    db: Session = Depends(get_db),
):
    """
    政策案の一覧を取得する。
    - status でのフィルタ
    - タイトル/本文の部分一致検索
    - created_at の降順で返却
    - 政策タグ情報も含めて返却
    
    🔒 権限: POLICY_READ が必要
    """
    # ユーザー情報を監査ログに含める
    rows = list_proposals(db=db, status_filter=status, q=q, offset=offset, limit=limit)
    return [ProposalOut.from_proposal_with_relations(proposal) for proposal in rows]


# 投稿履歴取得エンドポイント
@router.get("/my-submissions", response_model=dict)
@audit_log(
    event_type=AuditEventType.DATA_READ, 
    resource="policy_proposal", 
    action="list_user_submissions"
)
async def get_my_submissions(
    http_request: Request,
    offset: int = Query(0, ge=0, description="スキップ件数"),
    limit: int = Query(20, ge=1, le=100, description="取得件数"),
    current_user: User = Depends(require_permissions(Permission.POLICY_READ)),  # 🔒 権限チェックを依存関係として使用
    db: Session = Depends(get_db),
):
    """
    ログインユーザーが投稿した政策提案の履歴を取得する。
    
    🔒 権限: POLICY_READ が必要
    
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
        # current_userはUserオブジェクトなので、.get()ではなく直接アクセス
        user_id = str(current_user.id)
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
        for s in submissions_data:
            proposal = s["proposal"]
            comment_count = s["comment_count"]
            submissions.append(
                PolicySubmissionHistory.from_proposal_with_comment_count(
                    proposal=proposal, 
                    comment_count=comment_count
                )
            )
        
        return {"success": True, "data": submissions}
        
    except HTTPException:
        raise
    except Exception as e:
        # ポリシーに合わせて 500 を返す（成功フラグ付き200は避ける）
        raise HTTPException(
            status_code=500, 
            detail=f"投稿履歴の取得に失敗しました: {e}"
        )


# 政策案の詳細取得
@router.get("/{proposal_id}", response_model=ProposalOut)
@audit_log(
    event_type=AuditEventType.DATA_READ,
    resource="policy_proposal",
    action="read_detail"
)
async def get_policy_proposal_detail(  # asyncを追加
    http_request: Request,
    proposal_id: str, 
    current_user: User = Depends(require_permissions(Permission.POLICY_READ)),  # 🔒 権限チェックを依存関係として使用
    db: Session = Depends(get_db)
):
    """
    主キー（UUID文字列）を指定して政策案の詳細を取得する。
    政策タグ情報も含めて返却する。
    
    🔒 権限: POLICY_READ が必要
    """
    proposal = get_proposal(db=db, proposal_id=proposal_id)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy proposal not found")
    return ProposalOut.from_proposal_with_relations(proposal)


# 政策案のコメント一覧取得
@router.get("/{proposal_id}/comments", response_model=list[PolicyProposalCommentResponse])
@audit_log(
    event_type=AuditEventType.DATA_READ,
    resource="policy_proposal_comments",
    action="list"
)
async def get_policy_proposal_comments(  # asyncを追加
    http_request: Request,
    proposal_id: str,
    current_user: User = Depends(require_permissions(Permission.COMMENT_READ)),  # 🔒 権限チェックを依存関係として使用
    db: Session = Depends(get_db), 
    limit: int = 50, 
    offset: int = 0
):
    """
    特定の政策案IDに紐づくコメント一覧を取得する。
    
    🔒 権限: COMMENT_READ が必要
    
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


async def _cleanup_uploaded_blobs(uploaded_blobs: list[tuple[str, str]]):
    """アップロードされたBlobファイルのクリーンアップ"""
    for blob_name, file_url in uploaded_blobs:
        try:
            # anyio.to_thread.run_syncで安全なスレッド実行
            await anyio.to_thread.run_sync(
                delete_blob,  # 🔒 delete_blob_file → delete_blobに修正
                blob_name
            )
            print(f"✅ Blobファイルを削除: {blob_name}")
        except Exception as cleanup_error:
            print(f"❌ Blobファイル削除でエラー: {cleanup_error}")
            # クリーンアップの失敗はログに記録するが、メインエラーは発生させない