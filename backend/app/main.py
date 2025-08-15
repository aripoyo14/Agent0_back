from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import user, auth, policy_proposal_comment, policy_proposal, cosmos_minutes, outreach, expert, search_network_map
import app.models
from app.core.startup import init_external_services

app = FastAPI()

""" ----------
 CORS 設定（フロントエンドのNext.js開発サーバと連携するため）
 ---------- """
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await init_external_services()

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


@app.get("/")
def root():
    return {"message": "AgentØ"}
