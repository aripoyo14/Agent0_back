from fastapi import FastAPI
from app.api.routes import user, auth

app = FastAPI()

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


@app.get("/")
def root():
    return {"message": "AgentØ"}
