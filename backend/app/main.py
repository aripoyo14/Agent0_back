from fastapi import FastAPI
from app.api.routes import user

app = FastAPI()

# ルーター登録
# app.include_router(video.router)
# app.include_router(auth.router)
# app.include_router(line.router)
# app.include_router(coach.router)
app.include_router(user.router, prefix="/api/users", tags=["Users"])    # ユーザー関連

@app.get("/")
def root():
    return {"message": "AgentØ"}
