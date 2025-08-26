from fastapi import APIRouter, Depends, HTTPException, Request, Security
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.summary import MatchRequest, NetworkMapResponseDTO
from app.crud.experts_policy_tags import experts_policy_tags_crud
from app.crud.policy_tag import policy_tag_crud
from app.core.security.rate_limit.decorators import rate_limit_read_api
from app.core.security.rbac.permissions import Permission
from app.core.dependencies import get_current_user_authenticated
from app.models.user import User
from app.models.expert import Expert
from app.core.security.jwt import decode_access_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Union
import logging
# 監査ログ用のインポートを追加
from app.core.security.audit.decorators import audit_log
from app.core.security.audit.models import AuditEventType

# HTTPBearerの設定（auto_error=Falseで依存段階の即時403を回避）
oauth2_scheme = HTTPBearer(auto_error=False)

# ロガーの設定（アプリ全体のロガー設定に従う）
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


router = APIRouter(prefix="/search_network_map", tags=["Search Network Map"])


# デコレータ実行前に request.state に user 情報を注入する依存関係
async def inject_user_state(
    request: Request,
    token: HTTPAuthorizationCredentials | None = Security(oauth2_scheme),
) -> None:
    logger.info(f"inject_user_state called for {request.url.path}")
    
    token_str = None
    if token and getattr(token, "credentials", None):
        token_str = token.credentials
        logger.info("Token found from HTTPAuthorizationCredentials")
    else:
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token_str = auth_header.split(" ", 1)[1]
            logger.info("Token found from Authorization header")
        elif request.headers.get("X-Access-Token"):
            token_str = request.headers.get("X-Access-Token")
            logger.info("Token found from X-Access-Token header")
        elif request.headers.get("X-Auth-Token"):
            token_str = request.headers.get("X-Auth-Token")
            logger.info("Token found from X-Auth-Token header")
        elif request.headers.get("X-Authorization"):
            token_str = request.headers.get("X-Authorization")
            if token_str.lower().startswith("bearer "):
                token_str = token_str.split(" ", 1)[1]
            logger.info("Token found from X-Authorization header")
        elif "access_token" in request.cookies:
            token_str = request.cookies.get("access_token")
            logger.info("Token found from access_token cookie")
        elif "jwt" in request.cookies:
            token_str = request.cookies.get("jwt")
            logger.info("Token found from jwt cookie")
        elif "token" in request.cookies:
            token_str = request.cookies.get("token")
            logger.info("Token found from token cookie")

    if not token_str:
        logger.warning("No token found in any source")
        return None

    logger.info(f"Token found: {token_str[:20]}...")
    
    payload_data = decode_access_token(token_str)
    if not payload_data:
        logger.warning("Failed to decode token")
        return None

    user_id = payload_data.get("sub")
    user_type = payload_data.get("user_type")
    logger.info(f"Decoded user_id: {user_id}, user_type: {user_type}")
    
    try:
        request.state.user_id = user_id
        request.state.user_type = user_type
        request.state.user = {"user_id": user_id, "user_type": user_type}
        logger.info(f"Successfully set request.state: user_id={request.state.user_id}, user_type={request.state.user_type}")
    except Exception as e:
        logger.error(f"Failed to set request.state: {e}")
        pass
    return None


@router.post("/match", response_model=NetworkMapResponseDTO)
@audit_log(
    event_type=AuditEventType.SEARCH_NETWORK_MAP,
    resource="network_map",
    action="search_match"
)
async def match(
    request: Request,
    payload: MatchRequest,
    _: None = Depends(inject_user_state),
    db: Session = Depends(get_db),
    token: HTTPAuthorizationCredentials | None = Security(oauth2_scheme),
):
    # 関数開始
    
    # 人脈マップ閲覧権限チェック
    try:
        # 権限チェック

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
        
        # 監査デコレータが拾えるように request.state に設定
        try:
            if hasattr(request, "state"):
                request.state.user_id = user_id
                request.state.user_type = user_type
                request.state.user = {"user_id": user_id, "user_type": user_type}
        except Exception:
            pass
        
        # 必要最低限の情報のみログ
        logger.info(f"/search_network_map/match access by user_id={user_id}, user_type={user_type}")
        
        if not user_id or not user_type:
            raise HTTPException(
                status_code=401,
                detail="認証情報が不完全です"
            )
        
        # 外部有識者の場合は人脈マップ閲覧権限なし
        if user_type == "expert":
            logger.warning(f"外部有識者が人脈マップにアクセスしようとしました: {user_id}")
            raise HTTPException(
                status_code=403, 
                detail="外部有識者は人脈マップを閲覧できません"
            )
        
        # 経産省職員の場合、権限チェック
        if user_type == "user":
            # 権限リストを文字列に正規化
            normalized_permissions = [p.value if isinstance(p, Permission) else p for p in permissions]
            
            # system:admin 権限を持つ場合はバイパス
            if Permission.SYSTEM_ADMIN.value in normalized_permissions:
                logger.info(f"user {user_id} bypassed by system:admin")
            elif Permission.SEARCH_NETWORK_READ.value not in normalized_permissions:
                logger.warning(f"ユーザー {user_id} に人脈マップ閲覧権限がありません: {normalized_permissions}")
                raise HTTPException(
                    status_code=403,
                    detail="人脈マップの閲覧権限がありません"
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
        # 名前からタグIDを解決（単一/複数）
        if not payload.policy_tag:
            raise HTTPException(status_code=400, detail="policy_tag is required")
        tag_names = payload.policy_tag if isinstance(payload.policy_tag, list) else [payload.policy_tag]
        resolved_tags = []
        not_found = []
        for name in tag_names:
            t = policy_tag_crud.get_policy_tag_by_name(db, name)
            if t:
                resolved_tags.append(t)
            else:
                not_found.append(name)
        if not resolved_tags:
            raise HTTPException(status_code=404, detail=f"policy_tag(s) not found: {', '.join(not_found)}")
        if not_found:
            # 全て必要であれば 404 を返す方針でもよいが、ここでは解決できたものだけで進める
            pass
        tag_ids = [t.id for t in resolved_tags]
        experts_by_tag = experts_policy_tags_crud.get_top_experts_grouped_by_tag(
            db, tag_ids=tag_ids, limit_per_tag=100
        )

        # policy_themes を構築（複数対応）
        policy_themes = [
            {
                "id": str(t.id),
                "title": t.name,
            }
            for t in resolved_tags
        ]

        # experts と relations を構築
        expert_seen = set()
        experts = []
        relations = []
        for tag_id, expert_list in experts_by_tag.items():
            for e in expert_list:
                expert_id = e.get("expert_id")
                if expert_id and expert_id not in expert_seen:
                    expert_seen.add(expert_id)
                    experts.append({
                        "id": expert_id,
                        "name": f"{e.get('last_name','')}{e.get('first_name','')}",
                        "department": e.get("department"),
                        "title": e.get("title"),
                    })
                score = e.get("relation_score")
                if score is None:
                    continue
                # 0..1 にクリップ
                try:
                    s = float(score)
                except Exception:
                    continue
                s = max(0.0, min(1.0, s))
                relations.append({
                    "policy_id": str(tag_id),
                    "expert_id": expert_id,
                    "relation_score": s,
                })

        return NetworkMapResponseDTO(
            policy_themes=policy_themes,
            experts=experts,
            relations=relations,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"マッチング処理中にエラーが発生しました: {str(e)}")

