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
    PolicyWithComments,
    PolicyProposalReplyCreate,
    AIReplyRequest,
)
from app.crud.policy_proposal.policy_proposal_comment import (
    create_comment,
    get_comment_by_id,
    list_comments_by_policy_proposal_id,
    list_comments_for_policies_by_user,
    create_reply,
)
from app.services.openai import generate_ai_reply
from app.services.file_analyzer import extract_file_content
from app.services.file_analyzer_full import extract_file_content_full, compare_analysis_results
from app.db.session import SessionLocal
from app.crud.policy_proposal.policy_proposal import list_attachments_by_policy_proposal_id
from app.schemas.policy_proposal.policy_proposal import AttachmentOut


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
    comment = create_comment(db=db, comment_in=comment_in)
    return comment

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