from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes import user, auth, policy_proposal_comment, policy_proposal, cosmos_minutes, outreach, expert, search_network_map, meeting, network_routes, business_card
import app.models
from app.core.startup import init_external_services
from app.core.security.mfa import mfa_router

app = FastAPI()

""" ----------
 CORS 設定（フロントエンドのNext.js開発サーバと連携するため）
 ---------- """
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://aps-agent0-02-afawambwf2bxd2fv.italynorth-01.azurewebsites.net",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await init_external_services()
    # レート制限サービスの初期化を確認（この部分を修正）
    from app.core.security.rate_limit.service import rate_limit_service
    print(f" レート制限サービス状態: {rate_limit_service.config.enabled}")

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


@app.get("/")
def root():
    return {"message": "AgentØ"}
