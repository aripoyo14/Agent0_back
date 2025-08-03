# app/crud/user.py
"""
 - ユーザーに関するDB操作（CRUD）を定義するモジュール。
 - 主に SQLAlchemy を通じて User モデルとデータベースをやり取りする。
"""

from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import HTTPException, status

# 新規ユーザーを登録する関数　（事前にハッシュ化されたパスワードを引数として受け取る)
def create_user(db: Session, user_in: UserCreate, password_hash: str) -> User:

    # 1. メールアドレスの重複チェック（既に存在していたらエラー）
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このメールアドレスは既に登録されています。"
        )
    # 2. Userモデルのインスタンスを作成
    user = User(
        id=str(uuid4()),
        email=user_in.email,
        password_hash=password_hash,
        last_name=user_in.last_name,
        first_name=user_in.first_name,
        extension=user_in.extension,
        direct_phone=user_in.direct_phone,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # 3. ユーザー情報をDBに保存
    db.add(user)
    db.commit()
    db.refresh(user)    # 保存後の情報（例：自動で付与された値）を再取得

    # 4. 登録したユーザーオブジェクトを返す
    return user

# def get_by_email(db: Session, email: str) -> Optional[User]:
#     return db.query(User).filter(User.email == email).first()

# def get_by_email_and_verify_password(db: Session, email: str, password: str):
#     user = get_by_email(db, email=email)
#     if user and verify_password(password, user.password_hash):
#         return user
#     return None
