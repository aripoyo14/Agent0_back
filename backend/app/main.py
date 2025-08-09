from fastapi import FastAPI
from app.api.routes import user, auth, summary, policy_tag, cosmos_summary
from app.core.startup import init_external_services

app = FastAPI()

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
# 面談録要約API（Pinecone使用）
app.include_router(summary.router, prefix="/api")
# 政策タグ関連API
app.include_router(policy_tag.router, prefix="/api/policy-tags")
# 面談録要約API（Cosmos DB使用）
app.include_router(cosmos_summary.router, prefix="/api")


@app.get("/")
def root():
    return {"message": "AgentØ"}
