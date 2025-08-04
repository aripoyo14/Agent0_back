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

router = APIRouter(prefix="/auth", tags=["Auth"])

# UserログインAPI (ユーザー認証を行い、アクセストークン（JWT）を発行して返す)
@router.post("/login", response_model=TokenResponse)
def login_user(request: LoginRequest, db: Session = Depends(get_db)):
    # メールでユーザーを検索
    user = db.query(User).filter(User.email == request.email).first()
    
    # ユーザーが存在しない or パスワードが間違っている場合はエラー
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません。",
        )

    # JWTトークンを発行（ペイロードに user.id を含める）
    token = create_access_token({"sub": str(user.id)})

    # トークンをレスポンスとして返す
    return TokenResponse(access_token=token)
