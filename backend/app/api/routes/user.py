# app/api/routes/user.py
"""
 - ユーザー登録APIルートを定義するモジュール。
 - 主に FastAPI を通じて HTTP リクエスト（POST /register）を受け取り、
   バリデーション、パスワードのハッシュ化、DB登録処理などを行う。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserOut, UserLoginRequest, UserLoginResponse
from app.crud.user import create_user, get_user_by_email
from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token
from fastapi.security import HTTPBearer
from app.db.session import SessionLocal


# FastAPIのルーターを初期化
router = APIRouter(prefix="/users", tags=["Users"])

# DBセッションをリクエストごとに生成・提供する関数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # リクエスト処理が終わると、自動的にセッションをクローズ


""" ------------------------
 ユーザー関連エンドポイント
------------------------ """

# 新規ユーザー登録用のエンドポイント
@router.post("/register", response_model=UserOut)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):

    # パスワードをハッシュ化
    hashed_pw = hash_password(user_in.password)

    # CRUD層の関数を使ってDBにユーザー情報を保存
    user = create_user(db=db, user_in=user_in, password_hash=hashed_pw)

    # 保存された ユーザー情報 （UserOut） を返す
    return user

# ユーザーログイン用のエンドポイント
@router.post("/login", response_model=UserLoginResponse)
def login_user(request: UserLoginRequest, db: Session = Depends(get_db)):

    # メールでユーザーを検索
    user = get_user_by_email(db, email=request.email)
    
    # ユーザーが存在しない or パスワードが間違っている場合はエラー
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません。",
        )

    # JWTトークンを発行
    token = create_access_token({
        "sub": str(user.id),
        "role": "user",
        "type": "user"
    })

    # トークンとユーザー情報をレスポンスとして返す
    return UserLoginResponse(
        access_token=token,
        user=user
    )

# 現在ログイン中のユーザーのプロフィール情報取得用のエンドポイント
@router.get("/me", response_model=UserOut)
def get_user_profile(token: str = Depends(HTTPBearer()), db: Session = Depends(get_db)):

    try:
        payload = decode_access_token(token.credentials)
        user_id = payload.get("sub")
        role = payload.get("role")
        token_type = payload.get("type")
        
        if not user_id or role != "user" or token_type != "user":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なトークンです。"
            )
            
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザーが見つかりません。"
            )
            
        return user
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証に失敗しました。"
        )