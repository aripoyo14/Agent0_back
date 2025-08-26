# app/core/dependencies.py
""" 認証情報を取得するための依存関数を提供 """

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Type, Union, Optional, Dict
from datetime import datetime, timezone
import logging

from app.db.session import SessionLocal
from app.models.user import User
from app.models.expert import Expert
from app.core.config import settings
from app.core.security.session import session_manager
from app.core.security.rbac import RBACService
from app.core.security.rbac.permissions import Permission  # この行を追加

# ロガーの設定
logger = logging.getLogger(__name__)

# 認証用のOAuth2スキームを定義（正しいパスに修正）
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

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

    # デバッグログを追加
    logger.debug(f"認証開始: token length = {len(token) if token else 0}")
    
    # JWTトークンを検証
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        
        logger.debug(f"JWTデコード成功: payload = {payload}")
        
        # セッションIDを取得（フロントエンドのトークン形式に対応）
        session_id = payload.get("session_id") or payload.get("sub")
        if not session_id:
            logger.error("セッションIDがトークンに含まれていません")
            raise credentials_exception
        
        logger.debug(f"セッションID: {session_id}")
        
        # セッションの有効性をチェック（セッション管理が利用可能な場合のみ）
        try:
            session_data = session_manager.validate_session(session_id)
            if session_data:
                logger.debug(f"セッション検証成功: {session_data}")
                # 最終アクティビティを更新
                session_data.last_activity = datetime.now(timezone.utc)
        except Exception as session_error:
            logger.warning(f"セッション検証でエラー（無視）: {session_error}")
            # セッション検証が失敗しても、JWTトークンの内容で認証を継続
        
        result = {
            "user_id": payload.get("sub") or session_id,
            "user_type": payload.get("user_type", "user"),  # デフォルトは"user"
            "permissions": payload.get("scope", []),
            "session_id": session_id
        }
        
        logger.debug(f"認証成功: {result}")
        return result
        
    except JWTError as e:
        logger.error(f"JWTデコードエラー: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"予期しない認証エラー: {e}")
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
def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db),
    request: Request = None
) -> Union[User, Expert]:  # 戻り値の型を修正
    # 認証情報を取得
    auth_data = get_current_user_authenticated(token, request)
    
    # データベースからUserオブジェクトまたはExpertオブジェクトを取得
    user_id = auth_data.get("user_id")
    user_type = auth_data.get("user_type")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーIDが取得できませんでした"
        )
    
    if user_type == "expert":
        # Expertの場合はExpertテーブルから取得
        expert = db.query(Expert).filter(Expert.id == user_id).first()
        if not expert:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="有識者が見つかりません"
            )
        return expert
    else:
        # Userの場合はUserテーブルから取得
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザーが見つかりません"
            )
        return user

""" 外部有識者の認証情報を取得する関数（セッション管理版） """
def get_current_expert(token: str = Depends(oauth2_scheme), request: Request = None) -> Dict:
    return get_current_user_authenticated(token, request)

""" 特定の権限を要求する依存関数 """
def require_permissions(*required: Permission):
    """
    使用例:
        current_user: User = Depends(require_permissions(Permission.POLICY_READ))
    """
    def _checker(current_user: User = Depends(get_current_user)) -> User:  # 🔒 asyncを削除
        try:
            # RBACサービスで User から権限を解決・検証
            RBACService.enforce_user_permissions(current_user, required)
        except Exception:
            # ここで例外型を細かく分けたい場合は RBAC 側で専用例外を投げてハンドリング
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        return current_user  # 以降のハンドラで User をそのまま使える
    return _checker

""" セッション管理の依存関数 """
def get_session_manager():
    """セッションマネージャーを取得"""
    return session_manager