# app/crud/user.py
"""
 - ユーザーに関するDB操作（CRUD）を定義するモジュール。
 - 主に SQLAlchemy を通じて User モデルとデータベースをやり取りする。
"""

from sqlalchemy.orm import Session
from app.models.user import User, UsersDepartments, UsersPositions
from app.schemas.user import UserCreate
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status


# 日本時間（JST）のタイムゾーンを定義
JST = timezone(timedelta(hours=9))

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
        created_at=datetime.now(JST),
        updated_at=datetime.now(JST)
    )

    # 3. ユーザー情報をDBに保存
    db.add(user)
    db.flush()  # user.id を得るため

    # 4. 部署との中間テーブルに登録
    db.execute(
        UsersDepartments.__table__.insert().values(
            user_id=user.id,
            department_id=user_in.department_id
        )
    )

    # ５. 役職との中間テーブルに登録
    db.execute(
        UsersPositions.__table__.insert().values(
            user_id=user.id,
            position_id=user_in.position_id
        )
    )

    db.commit()
    db.refresh(user)    # 保存後の情報（例：自動で付与された値）を再取得

    # 4. 登録したユーザーオブジェクトを返す
    return user

# メールアドレスでユーザーを検索する関数
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()
