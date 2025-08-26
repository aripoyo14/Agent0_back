# app/api/routes/cosmos_summary.py
"""
 - Azure Cosmos DBを使用した面談録（minutes）ベクトル化・検索
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Security
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Union
from app.schemas.summary import SummaryRequest, SummaryResponse
from app.db.session import get_db
from app.models.user import User
from app.services.openai import generate_summary
from app.services.cosmos_vector import cosmos_vector_service
from app.core.security.rate_limit.decorators import rate_limit_read_api
from app.core.security.rbac.permissions import Permission
from app.core.dependencies import get_current_user_authenticated
from app.core.security.jwt import decode_access_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
import logging
# 監査ログ用のインポートを追加
from app.core.security.audit.decorators import audit_log
from app.core.security.audit.models import AuditEventType

# FastAPIのルーターを初期化
router = APIRouter(prefix="/cosmos-minutes", tags=["Cosmos Minutes"])

# HTTPBearerの設定（auto_error=Falseで依存段階の即時403を回避）
oauth2_scheme = HTTPBearer(auto_error=False)

# ロガーの設定（アプリ全体のロガー設定に従う）
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Cosmos Vector サービスの初期化
cosmos_vector_service = cosmos_vector_service

# DBセッションをリクエストごとに生成・提供する関数
def get_db():
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # リクエスト処理が終わると、自動的にセッションをクローズ

# ========== 面談録関連のエンドポイント ==========

@router.post("/minutes", summary="Vectorize Minutes", description="面談録（minutes）をベクトル化し、Cosmos DBに保存。関連度も更新")
@rate_limit_read_api
async def vectorize_minutes(
    request: Request,
    minutes_id: int = Query(..., description="ベクトル化する面談録のID"),
    db: Session = Depends(get_db),
    token: HTTPAuthorizationCredentials | None = Security(oauth2_scheme),
):
    """
    指定された面談録をベクトル化してCosmos DBに保存する
    """
    # 権限チェック
    try:
        # トークン取得（Authorizationヘッダー or Cookie）
        token_str = None
        if token and getattr(token, "credentials", None):
            token_str = token.credentials
        else:
            auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
            if auth_header and auth_header.lower().startswith("bearer "):
                token_str = auth_header.split(" ", 1)[1]
            elif request.headers.get("X-Access-Token"):
                token_str = request.headers.get("X-Access-Token")
            elif request.headers.get("X-Auth-Token"):
                token_str = request.headers.get("X-Auth-Token")
            elif request.headers.get("X-Authorization"):
                token_str = request.headers.get("X-Authorization")
                # 先頭に Bearer が付いている場合を許容
                if token_str.lower().startswith("bearer "):
                    token_str = token_str.split(" ", 1)[1]
            elif "access_token" in request.cookies:
                token_str = request.cookies.get("access_token")
            elif "jwt" in request.cookies:
                token_str = request.cookies.get("jwt")
            elif "token" in request.cookies:
                token_str = request.cookies.get("token")

        if not token_str:
            logger.warning("トークンが見つかりません (header/cookie いずれにも存在しません)")
            raise HTTPException(status_code=401, detail="認証トークンが必要です")

        # JWTトークンをデコード
        payload_data = decode_access_token(token_str)
        
        if not payload_data:
            raise HTTPException(
                status_code=401,
                detail="無効なトークンです"
            )
        
        # 認証データからユーザー情報を取得
        user_id = payload_data.get("sub")
        user_type = payload_data.get("user_type")
        permissions = payload_data.get("scope", [])
        
        # 必要最低限の情報のみログ
        logger.info(f"/cosmos-minutes/minutes access by user_id={user_id}, user_type={user_type}")
        
        if not user_id or not user_type:
            raise HTTPException(
                status_code=401,
                detail="認証情報が不完全です"
            )
        
        # 外部有識者の場合は権限なし
        if user_type == "expert":
            logger.warning(f"外部有識者が面談録ベクトル化にアクセスしようとしました: {user_id}")
            raise HTTPException(
                status_code=403, 
                detail="外部有識者は面談録ベクトル化を実行できません"
            )
        
        # 経産省職員の場合、権限チェック
        if user_type == "user":
            # 権限リストを文字列に正規化
            normalized_permissions = [p.value if isinstance(p, Permission) else p for p in permissions]
            
            # system:admin 権限を持つ場合はバイパス
            if Permission.SYSTEM_ADMIN.value in normalized_permissions:
                logger.info(f"user {user_id} bypassed by system:admin")
            elif Permission.SYSTEM_ADMIN.value not in normalized_permissions:
                logger.warning(f"ユーザー {user_id} に面談録ベクトル化権限がありません: {normalized_permissions}")
                raise HTTPException(
                    status_code=403,
                    detail="面談録ベクトル化の権限がありません"
                )
            logger.info(f"user {user_id} permission check ok")
        else:
            logger.warning(f"不明なユーザータイプ: {user_type}")
            raise HTTPException(
                status_code=403,
                detail="適切な権限がありません"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"権限チェック中に予期しないエラー: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"権限チェック中にエラーが発生しました: {str(e)}"
        )

    try:
        result = cosmos_vector_service.vectorize_minutes(minutes_id)
        
        if result["success"]:
            return {
                "status": "success",
                "message": result["message"],
                "database": "cosmos_db"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ベクトル化処理中にエラーが発生しました: {str(e)}"
        )

@router.get("/search", summary="Search Minutes", description="面談録（minutes）ベクトルの類似検索")
@rate_limit_read_api
@audit_log(
    event_type=AuditEventType.SEARCH_MINUTES,
    resource="minutes",
    action="search"
)
async def search_minutes(
    request: Request,
    query: str = Query(..., description="検索クエリ"),
    top_k: int = Query(5, description="返す結果の数"),
    expert_id: Optional[int] = Query(None, description="特定のエキスパートで絞り込み"),
    tag_ids: Optional[str] = Query(None, description="特定のタグで絞り込み（カンマ区切り）")
):
    """
    Cosmos DBを使用した面談録ベクトルの類似検索を行う
    """
    try:
        results = cosmos_vector_service.search_similar_summaries(
            query=query,
            top_k=top_k,
            expert_id=expert_id,
            tag_ids=tag_ids
        )
        
        return {
            "status": "success",
            "query": query,
            "results": results,
            "count": len(results),
            "database": "cosmos_db"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"検索処理中にエラーが発生しました: {str(e)}"
        )

@router.delete("/vector/{minutes_id}", summary="Delete Minutes Vector", description="指定IDのベクトルをCosmos DBから削除")
async def delete_minutes_vector(minutes_id: str):
    """
    指定されたIDのベクトルをCosmos DBから削除する
    """
    try:
        result = cosmos_vector_service.delete_summary_vector(minutes_id)
        
        if result["success"]:
            return {
                "status": "success",
                "message": result["message"],
                "database": "cosmos_db"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ベクトル削除中にエラーが発生しました: {str(e)}"
        )

@router.get("/statistics")
async def get_cosmos_vector_statistics():
    """
    Cosmos DBのベクトル統計情報を取得する
    """
    try:
        stats = cosmos_vector_service.get_vector_statistics()
        
        if stats["success"]:
            return {
                **stats,
                "database": "cosmos_db"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=stats["message"]
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"統計情報取得中にエラーが発生しました: {str(e)}"
        )

# ========== 政策タグ関連のエンドポイント ==========

@router.post("/policy-tags/vectorize")
async def vectorize_policy_tags(db: Session = Depends(get_db)):
    """
    MySQLの全政策タグをベクトル化してCosmos DBに保存する
    """
    try:
        result = cosmos_vector_service.vectorize_policy_tags(db)
        
        if result["success"]:
            return {
                "status": "success",
                "message": result["message"],
                "processed_count": result["processed_count"],
                "database": "cosmos_db"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"政策タグベクトル化中にエラーが発生しました: {str(e)}"
        )

@router.post("/policy-tags/vectorize/{tag_id}")
async def vectorize_single_policy_tag(tag_id: int, db: Session = Depends(get_db)):
    """
    指定されたIDの政策タグをベクトル化してCosmos DBに保存する
    """
    try:
        result = cosmos_vector_service.vectorize_single_policy_tag(db, tag_id)
        
        if result["success"]:
            return {
                "status": "success",
                "message": result["message"],
                "tag_id": result.get("tag_id"),
                "tag_name": result.get("tag_name"),
                "database": "cosmos_db"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"政策タグベクトル化中にエラーが発生しました: {str(e)}"
        )

@router.get("/policy-tags/search")
@audit_log(
    event_type=AuditEventType.SEARCH_POLICY_TAGS,
    resource="policy_tags",
    action="search"
)
async def search_policy_tags(
    request: Request,
    query: str = Query(..., description="検索クエリ"),
    top_k: int = Query(5, description="返す結果の数")
):
    """
    Cosmos DBを使用した政策タグの類似検索を行う
    """
    try:
        results = cosmos_vector_service.search_similar_policy_tags(
            query=query,
            top_k=top_k
        )
        
        return {
            "status": "success",
            "query": query,
            "results": results,
            "count": len(results),
            "database": "cosmos_db"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"政策タグ検索中にエラーが発生しました: {str(e)}"
        )


# マッチングAPIは search_network_map へ移設

@router.delete("/policy-tags/vector/{tag_id}")
async def delete_policy_tag_vector(tag_id: int):
    """
    指定された政策タグIDのベクトルをCosmos DBから削除する
    """
    try:
        result = cosmos_vector_service.delete_policy_tag_vector(tag_id)
        
        if result["success"]:
            return {
                "status": "success",
                "message": result["message"],
                "tag_id": result.get("tag_id"),
                "database": "cosmos_db"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"政策タグベクトル削除中にエラーが発生しました: {str(e)}"
        )
