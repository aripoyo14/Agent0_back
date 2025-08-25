# app/api/routes/policy_proposal_comment.py
"""
 - 政策案コメントAPIルートを定義するモジュール。
 - コメント投稿（POST）を受け取り、バリデーション・DB登録処理を行う。
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
import uuid
from app.schemas.policy_proposal_comment import (
    PolicyProposalCommentCreate,
    PolicyProposalCommentResponse,
    PolicyWithComments,
    PolicyProposalReplyCreate,
    AIReplyRequest,
    CommentRatingCreate,
    CommentRatingResponse,
    PolicyProposalCommentsCountResponse,
    RepliesResponse,
    ReplyCountResponse,
)
from app.crud.policy_proposal.policy_proposal_comment import (
    create_comment,
    get_comment_by_id,
    list_comments_by_policy_proposal_id,
    list_comments_for_policies_by_user,
    create_reply,
    update_comment_rating,
    get_comment_count_by_policy_proposal,
    get_replies_by_parent_comment_id,
    get_reply_count_by_parent_comment_id,
)
from app.services.openai import generate_ai_reply
from datetime import datetime
from app.services.file_analyzer import extract_file_content
from app.services.file_analyzer_full import extract_file_content_full, compare_analysis_results
from app.db.session import SessionLocal
from app.crud.policy_proposal.policy_proposal import list_attachments_by_policy_proposal_id
from app.schemas.policy_proposal.policy_proposal import AttachmentOut
from app.core.security.rate_limit.decorators import rate_limit_comment_post
from app.core.security.rbac import RBACService
from app.core.security.rbac.permissions import Permission
from app.models.user import User
from app.models.expert import Expert
from app.core.dependencies import get_current_user_authenticated
import logging

logger = logging.getLogger(__name__)

def is_valid_uuid(uuid_string: str) -> bool:
    """UUID形式の検証"""
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False


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
@rate_limit_comment_post()
async def post_comment(
    request: Request,
    comment_in: PolicyProposalCommentCreate,
    auth_data: dict = Depends(get_current_user_authenticated),  # 追加
    db: Session = Depends(get_db)
):
    """
    政策案に対するコメントを新規投稿する。
    
    ## 機能
    - 政策案に新しいコメントを投稿
    - 返信コメントの場合は `parent_comment_id` を指定
    
    ## 制約
    - `viewer` タイプのユーザーは投稿不可
    - 有効な `author_type`: admin, staff, contributor, viewer
    
    ## 使用例
    ```json
    {
      "policy_proposal_id": "uuid",
      "author_type": "staff",
      "author_id": "uuid",
      "comment_text": "コメント内容",
      "parent_comment_id": null
    }
    ```
    """
    from app.core.security.rbac import RBACService
    from app.core.security.rbac.permissions import Permission
    from app.models.user import User
    from app.models.expert import Expert

    user_id = auth_data.get("user_id")
    user_type = auth_data.get("user_type")
    if not user_id or not user_type:
        raise HTTPException(status_code=401, detail="認証情報が取得できませんでした")

    if user_type == "expert":
        expert = db.query(Expert).filter(Expert.id == user_id).first()
        if not expert:
            raise HTTPException(status_code=401, detail="有識者が見つかりません")
        if not RBACService.check_expert_permission(expert, Permission.COMMENT_CREATE):
            raise HTTPException(status_code=403, detail="コメント投稿権限がありません")
        # 安全のため author_type/author_id をトークンで上書きするならここで行う
        # comment_in.author_type = "contributor" など
        # comment_in.author_id = expert.id
    else:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="ユーザーが見つかりません")
        if not RBACService.check_user_permission(user, Permission.COMMENT_CREATE):
            raise HTTPException(status_code=403, detail="コメント投稿権限がありません")
        # 同様に author_type/author_id を上書きするならここ

    try:
        comment = create_comment(db=db, comment_in=comment_in)
        return comment
    except Exception as e:
        # エラーハンドリングを追加
        logger.error(f"コメント作成エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"コメントの作成に失敗しました: {str(e)}")

# 単一コメント取得
@router.get("/{comment_id}", response_model=PolicyProposalCommentResponse)
def get_comment(comment_id: str, db: Session = Depends(get_db)):
    """
    単一コメントを取得する。
    
    ## 機能
    - 指定されたコメントIDの詳細情報を取得
    - 論理削除されたコメントは除外
    
    ## パラメータ
    - `comment_id`: コメントのUUID
    
    ## レスポンス
    - コメントが見つからない場合: 404 Not Found
    - 成功時: コメントの詳細情報
    
    ## 使用例
    ```
    GET /api/policy-proposal-comments/7803bd7d-dc24-4730-adf9-f3e0d5c7c18a
    ```
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
    
    ## 機能
    - 指定された政策案に投稿されたコメント一覧を取得
    - 投稿日時の降順でソート
    - ページング対応（limit/offset）
    
    ## パラメータ
    - `policy_proposal_id`: 政策案のUUID
    - `limit`: 取得件数（デフォルト: 50, 最大: 100）
    - `offset`: スキップ件数（デフォルト: 0）
    
    ## レスポンス
    - 論理削除されたコメントは除外
    - 空の場合は空配列を返却
    
    ## 使用例
    ```
    GET /api/policy-proposal-comments/by-proposal/11111111-2222-3333-4444-555555555555?limit=20&offset=0
    ```
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
    
    ## 機能
    - 指定ユーザーが作成した政策案を取得
    - 各政策案に投稿されたコメント一覧を取得
    - 政策案ごとにグループ化して返却
    
    ## パラメータ
    - `user_id`: ユーザーのUUID
    - `limit`: 取得件数（デフォルト: 20）
    - `offset`: スキップ件数（デフォルト: 0）
    
    ## レスポンス
    - 政策案が見つからない場合: 404 Not Found
    - 成功時: 政策案とコメントのグループ化されたリスト
    
    ## 使用例
    ```
    GET /api/policy-proposal-comments/by-user/581c56f8-6885-467d-a113-ffbbe65cd184?limit=10&offset=0
    ```
    """
    results = list_comments_for_policies_by_user(db, user_id, limit=limit, offset=offset)
    if not results:
        raise HTTPException(status_code=404, detail="No policies or comments found for this user")
    return results

""" ------------------------
  返信関連エンドポイント
------------------------ """

# 既存コメントに対する返信の投稿
@router.post("/{parent_comment_id}/replies", response_model=PolicyProposalCommentResponse)
def post_reply(
    parent_comment_id: str,
    reply_in: PolicyProposalReplyCreate,
    db: Session = Depends(get_db),
):
    """
    既存コメントに対する返信を投稿する。
    
    ## 機能
    - 指定されたコメントに対する返信を作成
    - 親コメントと同じ政策案に自動的に紐付け
    - スレッド形式のコメント構造を構築
    
    ## パラメータ
    - `parent_comment_id`: 返信先のコメントUUID
    
    ## リクエストボディ
    ```json
    {
      "author_type": "staff",
      "author_id": "uuid",
      "comment_text": "返信内容"
    }
    ```
    
    ## 制約
    - `viewer` タイプのユーザーは返信投稿不可
    - 親コメントが存在しない場合: 404 Not Found
    - 親コメントが削除されていても返信は可能（履歴保持）
    
    ## レスポンス
    - 成功時: 作成された返信コメントの詳細
    - 返信コメントの `parent_comment_id` に親コメントIDが設定される
    
    ## 使用例
    ```
    POST /api/policy-proposal-comments/7803bd7d-dc24-4730-adf9-f3e0d5c7c18a/replies
    ```
    """
    reply = create_reply(
        db,
        parent_comment_id=parent_comment_id,
        author_type=reply_in.author_type,
        author_id=str(reply_in.author_id),
        comment_text=reply_in.comment_text,
    )
    return reply

# OpenAIで返信文案を生成
@router.post("/{comment_id}/ai-reply")
def generate_reply_suggestion(
    comment_id: str,
    req: AIReplyRequest,
    db: Session = Depends(get_db),
):
    """
    OpenAIを使用してコメントに対する返信文案を生成する。
    
    ## 機能
    - 指定されたコメントに対するAI返信案を生成
    - コメントに紐づく添付ファイルの内容も考慮
    - 完全版ファイル解析を使用（高品質な分析）
    
    ## パラメータ
    - `comment_id`: 対象コメントのUUID
    
    ## リクエストボディ
    ```json
    {
      "author_type": "staff",
      "author_id": "uuid",
      "persona": "丁寧で建設的な政策担当者",
      "instruction": "具体的な提案を含めて返信してください"
    }
    ```
    
    ## 処理内容
    1. コメントの存在確認
    2. コメントに紐づく政策案の添付ファイル取得
    3. 完全版ファイル解析（PDF、Word、Excel、テキスト対応）
    4. キーポイント抽出と構造分析
    5. OpenAIによる返信案生成
    
    ## 制約
    - OpenAI APIキーが必要
    - 処理時間: 最大30秒（ファイル解析含む）
    - ファイルサイズ制限: 10MBまで
    - 生成された文案は自動保存されない
    
    ## レスポンス
    ```json
    {
      "suggested_reply": "AIが生成した返信文案"
    }
    ```
    
    ## 使用例
    ```
    POST /api/policy-proposal-comments/7803bd7d-dc24-4730-adf9-f3e0d5c7c18a/ai-reply
    ```
    
    ## 注意事項
    - 添付ファイルがない場合でも、コメント内容に基づいて返信を生成
    - ファイル解析に失敗した場合でも、コメント内容のみで返信を生成
    - 生成された文案は手動で返信として投稿する必要がある
    """
    target = get_comment_by_id(db, comment_id)
    if not target:
        raise HTTPException(status_code=404, detail="Comment not found")

    # コメントに紐づく添付ファイルを取得
    attachments = list_attachments_by_policy_proposal_id(
        db, policy_proposal_id=str(target.policy_proposal_id)
    )
    
    # 添付ファイル情報を辞書のリストに変換
    attachments_info = []
    for att in attachments:
        attachments_info.append({
            "file_name": att.file_name,
            "file_type": att.file_type,
            "file_url": att.file_url,
        })

    ai_text = generate_ai_reply(
        target.comment_text,
        attachments_info=attachments_info,
        persona=req.persona,
        instruction=req.instruction,
    )

    # 生成した文案をそのまま返す（保存はしない）
    return {"suggested_reply": ai_text}


""" ------------------------
  評価関連エンドポイント
------------------------ """

# コメントの評価を更新
@router.patch("/{comment_id}/rating", response_model=CommentRatingResponse)
def update_rating(
    comment_id: str,
    rating_in: CommentRatingCreate,
    db: Session = Depends(get_db),
):
    """
    コメントの評価を更新する。
    
    ## 機能
    - 既存のコメントに評価（evaluation/stance）を追加・更新
    - 評価のみの操作（コメント本文は変更しない）
    
    ## パラメータ
    - `comment_id`: 評価対象のコメントUUID
    
    ## リクエストボディ
    ```json
    {
      "evaluation": 4,  // 純粋な評価（1-5：悪い-良い）
      "stance": 3       // スタンス（1-5：否定的-肯定的）
    }
    ```
    
    ## 制約
    - evaluation: 1-5の範囲
    - stance: 1-5の範囲
    - 両方ともNULL可（部分更新対応）
    
    ## レスポンス
    - 成功時: 更新された評価情報
    - コメントが見つからない場合: 404 Not Found
    - 評価値が範囲外の場合: 400 Bad Request
    
    ## 使用例
    ```
    PATCH /api/policy-proposal-comments/7803bd7d-dc24-4730-adf9-f3e0d5c7c18a/rating
    ```
    """
    updated_comment = update_comment_rating(
        db,
        comment_id=comment_id,
        evaluation=rating_in.evaluation,
        stance=rating_in.stance,
    )
    
    return CommentRatingResponse(
        id=updated_comment.id,
        evaluation=updated_comment.evaluation,
        stance=updated_comment.stance,
        updated_at=updated_comment.posted_at  # 一時的にposted_atを使用（DBマイグレーション後はupdated_atに変更）
    )


# ファイル解析比較テスト用エンドポイント
@router.post("/{comment_id}/analyze-files-compare")
def analyze_files_compare(
    comment_id: str,
    db: Session = Depends(get_db),
):
    """
    軽量版と完全版のファイル解析結果を比較する（開発・テスト用）。
    
    ## 機能
    - コメントに紐づく添付ファイルを軽量版と完全版で解析
    - 両版の処理時間、内容詳細度、キーポイント抽出を比較
    - 開発時の性能評価と品質比較に使用
    
    ## パラメータ
    - `comment_id`: 対象コメントのUUID
    
    ## 処理内容
    1. コメントの存在確認
    2. コメントに紐づく政策案の添付ファイル取得
    3. 各ファイルを軽量版で解析
    4. 各ファイルを完全版で解析
    5. 両版の結果を比較
    
    ## 軽量版 vs 完全版の違い
    | 項目 | 軽量版 | 完全版 |
    |------|--------|--------|
    | 処理速度 | 高速（10秒以内） | 低速（30秒以内） |
    | ファイルサイズ制限 | 50KB | 10MB |
    | PDF処理 | 最初の3ページのみ | 全ページ |
    | Word処理 | 最初の20段落のみ | 全段落 + 全テーブル |
    | Excel処理 | 最初の10行×10列のみ | 全シート + 全データ |
    | 構造分析 | ❌ | ✅ |
    | キーポイント抽出 | ❌ | ✅ |
    
    ## レスポンス
    ```json
    {
      "comment_id": "uuid",
      "policy_proposal_id": "uuid",
      "total_attachments": 2,
      "comparison_results": [
        {
          "file_name": "計画書.pdf",
          "file_type": "application/pdf",
          "lightweight": {
            "processing_time": 0.5,
            "content_length": 1500
          },
          "full": {
            "processing_time": 8.2,
            "content_length": 15000,
            "key_points": ["重要な結論..."]
          },
          "comparison": {
            "time_ratio": 16.4,
            "content_ratio": 10.0,
            "improvement_factor": 5.0
          }
        }
      ]
    }
    ```
    
    ## 使用例
    ```
    POST /api/policy-proposal-comments/7803bd7d-dc24-4730-adf9-f3e0d5c7c18a/analyze-files-compare
    ```
    
    ## 注意事項
    - 開発・テスト用途のエンドポイント
    - 添付ファイルがない場合は適切なメッセージを返却
    - 処理時間が長くなる可能性がある（複数ファイルの完全解析）
    """
    target = get_comment_by_id(db, comment_id)
    if not target:
        raise HTTPException(status_code=404, detail="Comment not found")

    # コメントに紐づく添付ファイルを取得
    attachments = list_attachments_by_policy_proposal_id(
        db, policy_proposal_id=str(target.policy_proposal_id)
    )
    
    if not attachments:
        return {
            "message": "添付ファイルがありません",
            "comment_id": comment_id,
            "policy_proposal_id": str(target.policy_proposal_id)
        }
    
    comparison_results = []
    
    for att in attachments:
        # 軽量版で解析
        lightweight_result = extract_file_content(
            att.file_url, 
            att.file_type or "unknown", 
            att.file_name
        )
        
        # 完全版で解析
        full_result = extract_file_content_full(
            att.file_url, 
            att.file_type or "unknown", 
            att.file_name
        )
        
        # 比較結果
        comparison = compare_analysis_results(lightweight_result, full_result)
        
        comparison_results.append({
            "file_name": att.file_name,
            "file_type": att.file_type,
            "lightweight": lightweight_result,
            "full": full_result,
            "comparison": comparison
        })
    
    return {
        "comment_id": comment_id,
        "policy_proposal_id": str(target.policy_proposal_id),
        "total_attachments": len(attachments),
        "comparison_results": comparison_results
    }


""" ------------------------
  コメントから添付取得
------------------------ """

@router.get("/{comment_id}/attachments", response_model=list[AttachmentOut])
def list_attachments_for_comment(
    comment_id: str,
    db: Session = Depends(get_db),
):
    """
    コメントに紐づく政策案の添付ファイル一覧を取得する。
    
    ## 機能
    - 指定されたコメントが属する政策案の添付ファイル一覧を取得
    - コメントIDから政策案IDを自動的に特定
    - 添付ファイルのメタ情報（ファイル名、タイプ、URL等）を返却
    
    ## パラメータ
    - `comment_id`: 対象コメントのUUID
    
    ## 処理内容
    1. コメントの存在確認
    2. コメントから政策案IDを取得
    3. 政策案に紐づく添付ファイル一覧を取得
    
    ## レスポンス
    - コメントが見つからない場合: 404 Not Found
    - 添付ファイルがない場合: 空配列 `[]`
    - 成功時: 添付ファイルの詳細情報リスト
    
    ## レスポンス例
    ```json
    [
      {
        "id": "uuid",
        "policy_proposal_id": "uuid",
        "file_name": "計画書.pdf",
        "file_url": "https://...",
        "file_type": "application/pdf",
        "file_size": 1024000,
        "uploaded_by_user_id": "uuid",
        "uploaded_at": "2025-08-11T..."
      }
    ]
    ```
    
    ## 使用例
    ```
    GET /api/policy-proposal-comments/7803bd7d-dc24-4730-adf9-f3e0d5c7c18a/attachments
    ```
    
    ## 注意事項
    - 添付ファイルは政策案レベルで管理されている
    - コメントIDから政策案IDを介して添付ファイルを取得
    - ファイルの実体はAzure Blobに保存（URLのみ返却）
    """
    # 1) コメントを取得
    comment = get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # 2) コメントが属する政策案IDを使い、添付を取得
    rows = list_attachments_by_policy_proposal_id(
        db, policy_proposal_id=str(comment.policy_proposal_id)
    )
    return rows

# コメント数取得API
@router.get("/policy-proposals/{policy_proposal_id}/comment-count", response_model=PolicyProposalCommentsCountResponse)
def get_comment_count_by_policy_proposal_endpoint(
    policy_proposal_id: str,
    db: Session = Depends(get_db)
):
    """
    特定の政策提案に対するPolicyProposalComments数を取得する。
    
    ## 機能
    - 指定された政策提案に対するPolicyProposalComments数を取得
    - 論理削除されたコメントは除外
    
    ## パラメータ
    - `policy_proposal_id`: 政策提案ID（パスパラメータ）
    
    ## レスポンス
    - `policy_proposal_id`: 政策提案ID
    - `comment_count`: その政策提案に対するPolicyProposalComments数
    
    ## 使用例
    ```
    GET /api/policy-proposal-comments/policy-proposals/policy-001/comment-count
    ```
    
    ## レスポンス例
    ```json
    {
      "policy_proposal_id": "policy-001",
      "comment_count": 157
    }
    ```
    """
    try:
        comment_count = get_comment_count_by_policy_proposal(db, policy_proposal_id)
        return {
            "policy_proposal_id": policy_proposal_id,
            "comment_count": comment_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"コメント数取得中にエラーが発生しました: {str(e)}"
        )

# 返信コメント取得API
@router.get("/{parent_comment_id}/replies", response_model=RepliesResponse)
def get_replies_by_parent_comment(
    parent_comment_id: str,
    limit: int = Query(20, ge=1, le=100, description="取得件数制限"),
    offset: int = Query(0, ge=0, description="オフセット"),
    db: Session = Depends(get_db)
):
    """
    指定された親コメントに対する返信コメント一覧を取得する。
    
    ## 機能
    - 指定された親コメントに対する返信コメント一覧を取得
    - ページネーション対応（limit/offset）
    - 投稿日時の昇順でソート
    - 論理削除されたコメントは除外
    
    ## パラメータ
    - `parent_comment_id`: 親コメントID（パスパラメータ）
    - `limit`: 取得件数制限（デフォルト: 20, 最大: 100）
    - `offset`: オフセット（デフォルト: 0）
    
    ## レスポンス
    - 親コメントが見つからない場合: 404 Not Found
    - 成功時: 返信コメント一覧とメタ情報
    
    ## 使用例
    ```
    GET /api/policy-proposal-comments/7803bd7d-dc24-4730-adf9-f3e0d5c7c18a/replies?limit=10&offset=0
    ```
    
    ## レスポンス例
    ```json
    {
      "replies": [
        {
          "id": "uuid",
          "comment_text": "返信内容",
          "author_type": "staff",
          "author_id": "uuid",
          "author_name": "投稿者名",
          "posted_at": "2025-01-01T00:00:00Z",
          "parent_comment_id": "uuid"
        }
      ],
      "total_count": 5,
      "has_more": true
    }
    ```
    """
    try:
        # UUID形式の検証
        if not is_valid_uuid(parent_comment_id):
            raise HTTPException(
                status_code=400, 
                detail="Invalid comment ID format"
            )
        
        # 返信コメントを取得
        replies = get_replies_by_parent_comment_id(db, parent_comment_id, limit, offset)
        
        # 総件数を取得
        total_count = get_reply_count_by_parent_comment_id(db, parent_comment_id)
        
        # 次のページがあるかどうかを判定
        has_more = (offset + limit) < total_count
        
        return RepliesResponse(
            replies=replies,
            total_count=total_count,
            has_more=has_more
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching replies"
        )

# 返信コメント件数取得API
@router.get("/{parent_comment_id}/replies/count", response_model=ReplyCountResponse)
def get_reply_count_by_parent_comment(
    parent_comment_id: str,
    db: Session = Depends(get_db)
):
    """
    指定された親コメントに対する返信コメント数を取得する。
    
    ## 機能
    - 指定された親コメントに対する返信コメント数を取得
    - 論理削除されたコメントは除外
    
    ## パラメータ
    - `parent_comment_id`: 親コメントID（パスパラメータ）
    
    ## レスポンス
    - 親コメントが見つからない場合: 404 Not Found
    - 成功時: 返信コメント数
    
    ## 使用例
    ```
    GET /api/policy-proposal-comments/7803bd7d-dc24-4730-adf9-f3e0d5c7c18a/replies/count
    ```
    
    ## レスポンス例
    ```json
    {
      "reply_count": 5
    }
    ```
    """
    try:
        # UUID形式の検証
        if not is_valid_uuid(parent_comment_id):
            raise HTTPException(
                status_code=400, 
                detail="Invalid comment ID format"
            )
        
        reply_count = get_reply_count_by_parent_comment_id(db, parent_comment_id)
        return ReplyCountResponse(reply_count=reply_count)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching reply count"
        )