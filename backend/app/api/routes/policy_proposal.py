# app/api/routes/policy_proposal.py
"""
 - 政策案APIルートを定義するモジュール。
 - 新規登録（POST）、一覧取得（GET）、詳細取得（GET）を提供する。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Request, status
from sqlalchemy.orm import Session
import logging
from app.schemas.policy_proposal.policy_proposal import ProposalCreate, ProposalOut, AttachmentOut, PolicySubmissionHistory
from app.schemas.policy_proposal_comment import PolicyProposalCommentResponse
from app.crud.policy_proposal.policy_proposal import (
    create_proposal, 
    create_attachment, 
    get_proposal, 
    list_proposals, 
    get_user_submissions,
    get_proposals_by_policy_tag,  # 新規追加
    get_proposals_by_policy_tags   # 新規追加
)
from app.models.policy_proposal.policy_proposal_attachments import PolicyProposalAttachment
from app.db.session import SessionLocal
from app.core.blob import upload_binary_to_blob, delete_blob
from app.core.dependencies import get_current_user, get_current_user_authenticated  # get_current_user_authenticatedを追加
from uuid import UUID, uuid4
import os
from app.core.security.audit import AuditService, AuditEventType
from app.core.security.audit.decorators import audit_log, audit_log_sync
from app.models.user import User
from app.models.expert import Expert  # Expertモデルを追加
from typing import List, Optional
from sqlalchemy.orm import joinedload
from app.models.policy_proposal.policy_proposal import PolicyProposal
from app.models.policy_tag import PolicyTag

# ロガーの設定
logger = logging.getLogger(__name__)

# 🔒 権限チェック用のインポートを追加
from app.core.dependencies import require_permissions  # この行を追加
from app.core.security.rbac.permissions import Permission

import anyio  # 追加

# ユーザー状態注入用の依存関係を追加
from app.api.routes.search_network_map import inject_user_state

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
async def create_policy_proposal(
    data: ProposalCreate,
    _: None = Depends(inject_user_state),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.POLICY_CREATE)),
):
    """
    政策案を新規作成
    """
    payload = ProposalCreate(
        title=data.title,
        body=data.body,
        status=data.status,
        published_by_user_id=UUID(str(current_user.id)),
        policy_tag_ids=data.policy_tag_ids  # 新規追加
    )

    proposal = create_proposal(db, payload)
    db.commit()
    return proposal


# 添付ファイル付き政策案作成エンドポイント
@router.post("/with-attachments", response_model=ProposalOut)
@audit_log(
    event_type=AuditEventType.DATA_CREATE,
    resource="policy_proposal",
    action="create_with_attachments"
)
async def create_policy_proposal_with_attachments(
    title: str = Form(...),
    body: str = Form(...),
    status: str = Form("published"),  # draftからpublishedに変更
    policy_tag_ids: str = Form(None),  # JSON文字列として受け取り
    files: list[UploadFile] = File(None),
    _: None = Depends(inject_user_state),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.POLICY_CREATE)),
):
    """
    添付ファイル付きで政策案を新規作成
    
    ## 機能
    - 政策提案の基本情報（タイトル、本文、ステータス）
    - 政策テーマ（タグ）の選択
    - 複数ファイルのアップロード
    - Blobストレージへのファイル保存
    - データベースへの添付ファイル情報保存
    
    ## リクエスト形式
    Content-Type: multipart/form-data
    
    - title: 政策提案タイトル
    - body: 政策提案の詳細内容
    - status: draft/published/archived
    - policy_tag_ids: [1,3,5] (JSON文字列)
    - files: 複数のファイル
    """
    try:
        # policy_tag_idsのパース
        tag_ids = None
        if policy_tag_ids:
            import json
            tag_ids = json.loads(policy_tag_ids)
        
        # 政策提案の作成
        payload = ProposalCreate(
            title=title,
            body=body,
            status=status,
            published_by_user_id=UUID(str(current_user.id)),
            policy_tag_ids=tag_ids
        )
        
        proposal = create_proposal(db, payload)
        
        # 添付ファイルの処理
        uploaded_attachments = []
        if files:
            for file in files:
                # ファイルサイズチェック（5MB制限）
                if file.size > 5 * 1024 * 1024:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"ファイルサイズが5MBを超えています: {file.filename}"
                    )
                
                # ファイル形式チェック
                allowed_types = ['application/pdf', 'application/msword', 
                               'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
                if file.content_type not in allowed_types:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"対応していないファイル形式です: {file.filename}"
                    )
                
                # ファイルをBlobストレージにアップロード
                blob_name = f"policy_proposals/{proposal.id}/{file.filename}"
                file_content = await file.read()
                file_url = upload_binary_to_blob(file_content, blob_name)
                
                # 添付ファイル情報をDBに保存
                attachment = create_attachment(
                    db=db,
                    policy_proposal_id=str(proposal.id),
                    file_name=file.filename,
                    file_url=file_url,
                    file_type=file.content_type,
                    file_size=file.size,
                    uploaded_by_user_id=str(current_user.id)
                )
                uploaded_attachments.append(attachment)
        
        db.commit()
        return proposal
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"政策提案作成エラー: {e}")
        raise HTTPException(
            status_code=500,
            detail="政策提案の作成に失敗しました"
        )





# 政策案の一覧取得（簡易検索・ページング付き）
@router.get("/", response_model=list[ProposalOut])
@audit_log(
    event_type=AuditEventType.SEARCH_POLICY_PROPOSALS,
    resource="policy_proposal",
    action="list"
)
async def get_policy_proposals(
    http_request: Request,
    status: str | None = Query(None, description="draft / published / archived のいずれか"),
    q: str | None = Query(None, description="タイトル・本文の部分一致"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    auth_data: dict = Depends(get_current_user_authenticated),  # 依存関係として取得
    db: Session = Depends(get_db),
):
    """
    政策案の一覧を取得する。
    - status でのフィルタ
    - タイトル/本文の部分一致検索
    - created_at の降順で返却
    - 政策タグ情報も含めて返却
    
    🔒 認証: ログインが必要（UserまたはExpert）
    """
    # 認証情報を取得（UserまたはExpert）
    from app.core.security.rbac import RBACService
    from app.core.security.rbac.permissions import Permission
    from app.models.user import User
    from app.models.expert import Expert
    
    # トークンから認証情報を取得
    user_id = auth_data.get("user_id")
    user_type = auth_data.get("user_type")
    
    if not user_id or not user_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証情報が取得できませんでした"
        )
    
    # ユーザータイプに応じて権限チェック
    if user_type == "expert":
        # Expertの場合はExpertテーブルから取得して権限チェック
        expert = db.query(Expert).filter(Expert.id == user_id).first()
        if not expert:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="有識者が見つかりません"
            )
        
        # Expertの権限をチェック
        if not RBACService.check_expert_permission(expert, Permission.POLICY_READ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="政策案の閲覧権限がありません"
            )
    else:
        # Userの場合はUserテーブルから取得して権限チェック
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザーが見つかりません"
            )
        
        # Userの権限をチェック
        if not RBACService.check_user_permission(user, Permission.POLICY_READ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="政策案の閲覧権限がありません"
            )
    
    # ユーザー情報を監査ログに含める
    try:
        rows = list_proposals(db=db, status_filter=status, q=q, offset=offset, limit=limit)
        return [ProposalOut.from_proposal_with_relations(proposal) for proposal in rows]
    except Exception as e:
        logger.error(f"政策案一覧取得エラー: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"政策案の取得に失敗しました: {str(e)}"
        )


# 投稿履歴取得エンドポイント
@router.get("/my-submissions", response_model=dict)
@audit_log(
    event_type=AuditEventType.READ_POLICY_PROPOSAL, 
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


# 特定の政策テーマタグに紐づく政策案を取得するエンドポイント
@router.get("/by-tag/{tag_id}", response_model=list[ProposalOut])
@audit_log(
    event_type=AuditEventType.DATA_READ,
    resource="policy_proposal",
    action="list_by_tag"
)
async def get_policy_proposals_by_tag(
    http_request: Request,
    tag_id: int,
    status: str | None = Query(None, description="draft / published / archived のいずれか"),
    offset: int = Query(0, ge=0, description="スキップ件数"),
    limit: int = Query(20, ge=1, le=100, description="取得件数"),
    auth_data: dict = Depends(get_current_user_authenticated),  # 依存関係として取得
    db: Session = Depends(get_db),
):
    """
    特定の政策テーマタグに紐づく政策案の一覧を取得する。
    
    🔒 認証: ログインが必要（UserまたはExpert）
    """
    # 認証情報を取得（UserまたはExpert）
    from app.core.security.rbac import RBACService
    from app.core.security.rbac.permissions import Permission
    from app.models.user import User
    from app.models.expert import Expert
    
    # トークンから認証情報を取得
    user_id = auth_data.get("user_id")
    user_type = auth_data.get("user_type")
    
    if not user_id or not user_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証情報が取得できませんでした"
        )
    
    # ユーザータイプに応じて権限チェック
    if user_type == "expert":
        # Expertの場合はExpertテーブルから取得して権限チェック
        expert = db.query(Expert).filter(Expert.id == user_id).first()
        if not expert:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="有識者が見つかりません"
            )
        
        # Expertの権限をチェック
        if not RBACService.check_expert_permission(expert, Permission.POLICY_READ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="政策案の閲覧権限がありません"
            )
    else:
        # Userの場合はUserテーブルから取得して権限チェック
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザーが見つかりません"
            )
        
        # Userの権限をチェック
        if not RBACService.check_user_permission(user, Permission.POLICY_READ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="政策案の閲覧権限がありません"
            )
    
    try:
        rows = get_proposals_by_policy_tag(
            db=db, 
            policy_tag_id=tag_id, 
            status_filter=status, 
            offset=offset, 
            limit=limit
        )
        return [ProposalOut.from_proposal_with_relations(proposal) for proposal in rows]
    except Exception as e:
        logger.error(f"政策テーマタグ別政策案取得エラー: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="政策案の取得に失敗しました"
        )


# 複数の政策テーマタグに紐づく政策案を取得するエンドポイント
@router.get("/by-tags", response_model=list[ProposalOut])
@audit_log(
    event_type=AuditEventType.DATA_READ,
    resource="policy_proposal",
    action="list_by_multiple_tags"
)
async def get_policy_proposals_by_multiple_tags(
    http_request: Request,
    tag_ids: str = Query(..., description="カンマ区切りの政策テーマタグID（例: 1,3,5）"),
    status: str | None = Query(None, description="draft / published / archived のいずれか"),
    offset: int = Query(0, ge=0, description="スキップ件数"),
    limit: int = Query(20, ge=1, le=100, description="取得件数"),
    current_user: User = Depends(require_permissions(Permission.POLICY_READ)),
    db: Session = Depends(get_db),
):
    """
    複数の政策テーマタグに紐づく政策案の一覧を取得する。
    
    🔒 権限: POLICY_READ が必要
    
    ## 機能
    - 指定された複数の政策テーマタグIDに紐づく政策案を取得（OR条件）
    - status でのフィルタ（オプション）
    - 投稿日時の降順でソート
    - ページング対応（limit/offset）
    - 政策タグ情報も含めて返却
    
    ## パラメータ
    - `tag_ids`: カンマ区切りの政策テーマタグID（例: 1,3,5）
    - `status`: ステータスフィルタ（オプション）
    - `offset`: スキップ件数（デフォルト: 0）
    - `limit`: 取得件数（デフォルト: 20, 最大: 100）
    
    ## 使用例
    ```
    GET /api/policy-proposals/by-tags?tag_ids=1,3,5&status=published&limit=10
    ```
    """
    try:
        # タグIDのパース
        try:
            tag_id_list = [int(tid.strip()) for tid in tag_ids.split(',') if tid.strip()]
            if not tag_id_list:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="有効なタグIDが指定されていません"
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="タグIDは数値で指定してください"
            )
        
        rows = get_proposals_by_policy_tags(
            db=db, 
            policy_tag_ids=tag_id_list, 
            status_filter=status, 
            offset=offset, 
            limit=limit
        )
        return [ProposalOut.from_proposal_with_relations(proposal) for proposal in rows]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"複数政策テーマタグ別政策案取得エラー: {e}")
        # 500エラーではなく、400エラーを返すように修正
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="リクエストパラメータが無効です"
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
async def get_policy_proposal_comments(
    http_request: Request,
    proposal_id: str,
    auth_data: dict = Depends(get_current_user_authenticated),  # 変更
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
    from app.core.security.rbac import RBACService
    from app.core.security.rbac.permissions import Permission
    from app.models.user import User
    from app.models.expert import Expert
    from app.crud.policy_proposal.policy_proposal_comment import list_comments_by_policy_proposal_id

    user_id = auth_data.get("user_id")
    user_type = auth_data.get("user_type")
    if not user_id or not user_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="認証情報が取得できませんでした")

    if user_type == "expert":
        expert = db.query(Expert).filter(Expert.id == user_id).first()
        if not expert:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="有識者が見つかりません")
        if not RBACService.check_expert_permission(expert, Permission.COMMENT_READ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="コメント閲覧権限がありません")
    else:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ユーザーが見つかりません")
        if not RBACService.check_user_permission(user, Permission.COMMENT_READ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="コメント閲覧権限がありません")

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
            logger.info(f"Blobファイルを削除: {blob_name}")
        except Exception as cleanup_error:
            logger.error(f"Blobファイル削除でエラー: {cleanup_error}")
            # クリーンアップの失敗はログに記録するが、メインエラーは発生させない