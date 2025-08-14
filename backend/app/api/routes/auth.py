# app/api/routes/auth.py
"""
 - ユーザーのログイン認証用APIルートを定義するモジュール。
 - 入力されたメールアドレス・パスワードを検証し、
   有効であればJWTトークンを返す。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.auth import LoginRequest, TokenResponse
from app.core.security import verify_password
from app.core.jwt import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.models.expert import Expert

router = APIRouter(prefix="/auth", tags=["Auth"])

# User/ExpertログインAPI (ユーザー認証を行い、アクセストークン（JWT）を発行して返す)
@router.post("/login", response_model=TokenResponse)
def login_user(request: LoginRequest, db: Session = Depends(get_db)):

    # まずUserテーブルで検索
    user = db.query(User).filter(User.email == request.email).first()

    # ユーザーが存在して、パスワードが正しい場合
    if user and verify_password(request.password, user.password_hash):
        # Userとしてログイン
        token = create_access_token({
            "sub": str(user.id),
            "user_type": "user",
            "role": user.role
        })
        return TokenResponse(access_token=token)
    
    # Userで見つからない場合、Expertテーブルで検索
    expert = db.query(Expert).filter(Expert.email == request.email).first()
    if expert and verify_password(request.password, expert.password_hash):
        # Expertとしてログイン
        token = create_access_token({
            "sub": str(expert.id),
            "user_type": "expert",
            "role": expert.role
        })
        return TokenResponse(access_token=token)
    
    # どちらでも認証失敗
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="メールアドレスまたはパスワードが正しくありません。",
    )

