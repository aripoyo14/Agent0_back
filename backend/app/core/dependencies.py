# app/core/dependencies.py
""" 認証情報を取得するための依存関数を提供 """

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Type, Union, Optional, Dict
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.models.user import User
from app.models.expert import Expert
from app.core.config import settings
from app.core.security.session import session_manager

# 認証用のOAuth2スキームを定義
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

""" DBセッションを取得する関数 """
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # リクエスト終了時にクローズ


""" セッション管理を使用した認証情報取得 """
def get_current_user_authenticated(
    token: str = Depends(oauth2_scheme),
    request: Request = None
) -> Optional[Dict]:
    """現在のユーザーをセッション管理で認証"""
    
    # 認証エラーの例外を定義
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # JWTトークンを検証
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        
        # セッションIDを取得
        session_id = payload.get("session_id")
        if not session_id:
            raise credentials_exception
        
        # セッションの有効性をチェック
        session_data = session_manager.validate_session(session_id)
        if not session_data:
            raise credentials_exception
        
        # 最終アクティビティを更新
        session_data.last_activity = datetime.now(timezone.utc)
        
        return {
            "user_id": payload.get("sub"),
            "user_type": payload.get("user_type"),
            "permissions": payload.get("scope", []),
            "session_id": session_id
        }
        
    except JWTError:
        raise credentials_exception



""" 従来の認証方式（後方互換性のため保持） """
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

""" 経産省職員の認証情報を取得する関数（セッション管理版） """
def get_current_user(token: str = Depends(oauth2_scheme), request: Request = None) -> Dict:
    return get_current_user_authenticated(token, request)

""" 外部有識者の認証情報を取得する関数（セッション管理版） """
def get_current_expert(token: str = Depends(oauth2_scheme), request: Request = None) -> Dict:
    return get_current_user_authenticated(token, request)

""" 特定の権限を要求する依存関数 """
def require_permissions(required_permissions: list):
    """特定の権限を要求するデコレータ"""
    def permission_checker(current_user: Dict = Depends(get_current_user)):
        user_permissions = current_user.get("permissions", [])
        
        for permission in required_permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"権限が不足しています: {permission}"
                )
        
        return current_user
    
    return permission_checker

""" セッション管理の依存関数 """
def get_session_manager():
    """セッションマネージャーを取得"""
    return session_manager