"""
セッション管理クラス
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Set
from jose import JWTError, jwt
from app.core.config import settings
import uuid

from .models import SessionData, SessionCreate, TokenResponse

class SessionManager:
    """セッション管理クラス"""
    
    def __init__(self):
        self.active_sessions: Dict[str, SessionData] = {}
        self.user_sessions: Dict[str, Set[str]] = {}
        self.blacklisted_tokens: Set[str] = set()
    
    def create_session(self, session_create: SessionCreate) -> TokenResponse:
        """新しいセッションを作成"""
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        # アクセストークン（短期限）
        access_token = self._create_access_token(
            session_create.user_id,
            session_create.user_type,
            session_create.permissions,
            session_id
        )
        
        # リフレッシュトークン（長期限）
        refresh_token = self._create_refresh_token(session_id)
        
        # セッション情報を保存
        session_data = SessionData(
            session_id=session_id,
            user_id=session_create.user_id,
            user_type=session_create.user_type,
            permissions=session_create.permissions,
            created_at=now,
            last_activity=now,
            ip_address=session_create.ip_address,
            user_agent=session_create.user_agent,
            is_active=True
        )
        
        self.active_sessions[session_id] = session_data
        
        # ユーザーセッション管理
        if session_create.user_id not in self.user_sessions:
            self.user_sessions[session_create.user_id] = set()
        self.user_sessions[session_create.user_id].add(session_id)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            session_id=session_id,
            expires_in=settings.access_token_expire_minutes * 60
        )
    
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

# グローバルセッションマネージャーインスタンス
session_manager = SessionManager()