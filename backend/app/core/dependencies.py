# app/core/dependencies.py
""" 認証情報を取得するための依存関数を提供 """

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Type, Union

from app.db.session import SessionLocal
from app.models.user import User
from app.models.expert import Expert
from app.core.config import settings

# 認証用のOAuth2スキームを定義
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

""" DBセッションを取得する関数 """
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # リクエスト終了時にクローズ

""" アクセストークンからユーザーまたは有識者情報を安全に取り出す関数 """
def _get_current_entity(token: str, db: Session, model: Type[Union[User, Expert]]) -> Union[User, Expert]:

    # 認証エラーの例外を定義
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # JWTトークンを検証し、ユーザーまたは有識者のIDを取得
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        entity_id: str = payload.get("sub")

        # トークンにIDが含まれていない場合はエラー
        if not entity_id:
            raise credentials_exception

    # JWTエラーの場合はエラーを返す
    except JWTError:
        raise credentials_exception

    # データベースからユーザーまたは有識者を取得
    entity = db.query(model).filter(model.id == entity_id).first()

    # ユーザーまたは有識者が存在しない場合はエラーを返す
    if not entity:
        raise credentials_exception
    return entity

""" 経産省職員の認証情報を取得する関数 """
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    return _get_current_entity(token, db, User)

""" 外部有識者の認証情報を取得する関数 """
def get_current_expert(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Expert:
    return _get_current_entity(token, db, Expert)