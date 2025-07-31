from fastapi import APIRouter

router = APIRouter(prefix="/video", tags=["Video"])

@router.get("/ping")
def ping():
    return {"message": "pong from video"}
