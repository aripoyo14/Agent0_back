from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.api.routes import user, auth, policy_proposal_comment, policy_proposal, cosmos_minutes, outreach, expert, search_network_map, meeting, network_routes, business_card, invitation_code
import app.models
from app.core.startup import init_external_services
from app.core.security.mfa import mfa_router
from app.core.security.audit.router import router as audit_router
from app.core.security.cors import get_cors_middleware_config, get_cors_config
from app.core.config import get_settings

# ロガーの設定
logger = logging.getLogger(__name__)

app = FastAPI()

# 環境別CORS設定
app.add_middleware(CORSMiddleware, **get_cors_middleware_config())

# CORS設定のログ出力（デバッグ用）
settings = get_settings()
logger.info(f"環境: {settings.environment}")
logger.info(f"CORS設定: {get_cors_config()}")

@app.on_event("startup")
async def startup_event():
    await init_external_services()
    # レート制限サービスの初期化を確認
    from app.core.security.rate_limit.service import rate_limit_service
    logger.info(f"レート制限サービス初期化完了: enabled={rate_limit_service.config.enabled}")

""" ----------
 ルーター登録
---------- """
# app.include_router(video.router)
# app.include_router(auth.router)
# app.include_router(line.router)
# app.include_router(coach.router)

# ユーザー関連API（登録・取得など）
app.include_router(user.router, prefix="/api") 

# 認証関連API（ログイン・トークン発行） 
app.include_router(auth.router, prefix="/api")

# 政策案関連API（登録・取得など）
app.include_router(policy_proposal.router, prefix="/api")

# 政策案コメント関連API（投稿など）
app.include_router(policy_proposal_comment.router, prefix="/api")

# 面談録要約・政策タグAPI（Cosmos DB使用）
app.include_router(cosmos_minutes.router, prefix="/api")

# 外部有識者関連API
app.include_router(expert.router, prefix="/api")

# ネットワークマップ検索API
app.include_router(search_network_map.router, prefix="/api")

# MFA関連API
app.include_router(mfa_router, prefix="/api")

# 面談関連API
app.include_router(meeting.router, prefix="/api")

# 人脈ルートAPI
app.include_router(network_routes.router, prefix="/api")

# 名刺画像アップロードAPI
app.include_router(business_card.router, prefix="/api")

# 招待コードルートを追加
app.include_router(invitation_code.router, prefix="/api")

# 監査ログAPI
app.include_router(audit_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "AgentØ"}
