from fastapi import FastAPI
from app.api.routes import video, auth, line, coach, user

app = FastAPI()

# ルーター登録
app.include_router(video.router)
app.include_router(auth.router)
app.include_router(line.router)
app.include_router(coach.router)
app.include_router(user.router)

@app.get("/")
def root():
    return {"message": "Hello from BBC backend"}
