# app/api/routes/user.py
"""
 - ユーザー登録APIルートを定義するモジュール。
 - 主に FastAPI を通じて HTTP リクエスト（POST /register）を受け取り、
   バリデーション、パスワードのハッシュ化、DB登録処理などを行う。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserOut
from app.crud.user import create_user
from app.core.security import hash_password
from app.db.session import SessionLocal


# FastAPIのルーターを初期化
router = APIRouter()

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

# @router.get("/me", response_model=UserOut)
# def get_me(current_user: User = Depends(get_current_user)):
#     return current_user