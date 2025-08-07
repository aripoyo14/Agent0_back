# app/api/routes/relation.py
"""
 - 面談録の要約する
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.summary import SummaryRequest, SummaryResponse
from app.db.session import get_db
from app.models.user import User
from app.services.openai import generate_summary

# FastAPIのルーターを初期化
router = APIRouter(prefix="/summary", tags=["Summary"])

@router.post("/summary")
async def summary(request: SummaryRequest, db: Session = Depends(get_db)):
    summary = generate_summary(request.minutes)
    
    return SummaryResponse(title=summary["title"], summary=summary["summary"])

