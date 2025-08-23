"""
セッション管理クラス
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Set
from jose import JWTError, jwt
from app.core.config import settings
import uuid
import logging
from .models import SessionData, SessionCreate, TokenResponse

# ロガーの設定
logger = logging.getLogger(__name__)

class SessionManager:
    """セッション管理クラス"""
    
    def __init__(self):
        self.active_sessions: Dict[str, SessionData] = {}
        self.user_sessions: Dict[str, Set[str]] = {}
        self.blacklisted_tokens: Set[str] = set()
    
    def create_session(self, session_id: str, user_id: str, user_type: str, metadata: dict = None) -> bool:
        """新しいセッションを作成（session_idを指定）"""
        try:
            now = datetime.now(timezone.utc)
            
            # セッション情報を保存
            session_data = SessionData(
                session_id=session_id,
                user_id=user_id,
                user_type=user_type,
                permissions=["read", "write"],  # デフォルト権限
                created_at=now,
                last_activity=now,
                ip_address=metadata.get("ip_address") if metadata else None,
                user_agent=metadata.get("user_agent") if metadata else None,
                is_active=True
            )
            
            self.active_sessions[session_id] = session_data
            
            # ユーザーセッション管理
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session_id)
            
            return True
            
        except Exception as e:
            logger.error(f"セッション作成エラー: {e}")
            return False
    
    def _create_access_token(self, user_id: str, user_type: str, permissions: list, session_id: str) -> str:
        """アクセストークンを作成"""
        to_encode = {
            "sub": user_id,
            "user_type": user_type,
            "scope": permissions,
            "session_id": session_id,
            "token_type": "access"
        }
        
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    def _create_refresh_token(self, session_id: str) -> str:
        """リフレッシュトークンを作成"""
        to_encode = {
            "session_id": session_id,
            "token_type": "refresh"
        }
        
        # リフレッシュトークンは7日間有効
        expire = datetime.now(timezone.utc) + timedelta(days=7)
        to_encode.update({"exp": expire})
        
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    def refresh_access_token(self, refresh_token: str) -> Optional[TokenResponse]:
        """リフレッシュトークンを使用してアクセストークンを更新"""
        try:
            payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[settings.algorithm])
            session_id = payload.get("session_id")
            token_type = payload.get("token_type")
            
            if token_type != "refresh" or not session_id:
                return None
            
            # セッションが有効かチェック
            if session_id not in self.active_sessions:
                return None
            
            session_data = self.active_sessions[session_id]
            if not session_data.is_active:
                return None
            
            # 新しいアクセストークンを作成
            new_access_token = self._create_access_token(
                session_data.user_id,
                session_data.user_type,
                session_data.permissions,
                session_id
            )
            
            # 最終アクティビティを更新
            session_data.last_activity = datetime.now(timezone.utc)
            
            return TokenResponse(
                access_token=new_access_token,
                refresh_token=refresh_token,  # 同じリフレッシュトークン
                session_id=session_id,
                expires_in=settings.access_token_expire_minutes * 60
            )
            
        except JWTError:
            return None
    
    def invalidate_session(self, session_id: str) -> bool:
        """セッションを無効化"""
        if session_id in self.active_sessions:
            session_data = self.active_sessions[session_id]
            user_id = session_data.user_id
            
            # セッションを無効化
            session_data.is_active = False
            
            # ユーザーセッション管理から削除
            if user_id in self.user_sessions:
                self.user_sessions[user_id].discard(session_id)
            
            # セッションを削除
            del self.active_sessions[session_id]
            
            return True
        return False
    
    def invalidate_user_sessions(self, user_id: str) -> int:
        """ユーザーの全セッションを無効化（パスワード変更時など）"""
        if user_id not in self.user_sessions:
            return 0
        
        count = 0
        for session_id in list(self.user_sessions[user_id]):
            if self.invalidate_session(session_id):
                count += 1
        
        return count
    
    def validate_session(self, session_id: str) -> Optional[SessionData]:
        """セッションの有効性をチェック"""
        if session_id not in self.active_sessions:
            return None
        
        session_data = self.active_sessions[session_id]
        if not session_data.is_active:
            return None
        
        # セッションの有効期限チェック（30日）
        if (datetime.now(timezone.utc) - session_data.created_at).days > 30:
            self.invalidate_session(session_id)
            return None
        
        return session_data
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """セッション情報を取得"""
        session_data = self.validate_session(session_id)
        if not session_data:
            return None
        
        return {
            "session_id": session_data.session_id,
            "user_id": session_data.user_id,
            "user_type": session_data.user_type,
            "created_at": session_data.created_at.isoformat(),
            "last_activity": session_data.last_activity.isoformat(),
            "ip_address": session_data.ip_address,
            "user_agent": session_data.user_agent,
            "is_active": session_data.is_active
        }
    
    def is_session_valid(self, session_id: str) -> bool:
        """セッションが有効かどうかをチェック"""
        return self.validate_session(session_id) is not None

# グローバルセッションマネージャーインスタンス
session_manager = SessionManager()