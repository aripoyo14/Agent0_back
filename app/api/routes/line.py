from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime
import os
from app.db.session import get_db
from app.models.user import User
from app.models.video import Video
from app.core.blob import upload_video_to_blob

router = APIRouter(prefix="/line", tags=["LINE"])

@router.post("/upload/video/line")
async def upload_video_from_line(
    line_user_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.line_user_id == line_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if file.content_type not in ["video/mp4", "video/quicktime"]:
        raise HTTPException(status_code=400, detail="Invalid video format")

    # Azureにアップロード
    extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid4()}{extension}"
    video_url = upload_video_to_blob(file.file, unique_filename)

    # DB保存
    video = Video(
        user_id=user.user_id,
        video_url=video_url,
        upload_date=datetime.utcnow()
    )
    db.add(video)
    db.commit()

    return {"video_url": video_url, "message": "Upload successful"}
