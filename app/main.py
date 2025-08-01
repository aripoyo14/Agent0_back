from fastapi import FastAPI
from app.api.routes import video, auth, line, coach, user

app = FastAPI(title="BBC Backend API", version="1.0.0")

# ルーター登録
app.include_router(video.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(line.router, prefix="/api")
app.include_router(coach.router, prefix="/api")
app.include_router(user.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Hello from BBC backend", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
