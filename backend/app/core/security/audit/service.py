"""
監査ログサービスクラス
セキュリティイベントの記録と管理
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Request
from app.core.security.audit.models import AuditLog, AuditEventType
from app.core.security.audit.config import AuditConfig
import logging

logger = logging.getLogger(__name__)


class AuditService:
    """監査ログのビジネスロジックを提供"""
    
    def __init__(self, db: Session):
        self.db = db
        self.config = AuditConfig()
    
    def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        user_type: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        success: bool = True,
        request: Optional[Request] = None,
        details: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> AuditLog:
        """監査イベントを記録（同期版）"""
        
        if not self.config.AUDIT_ENABLED:
            return None
        
        try:
            # リクエスト情報の抽出
            ip_address = None
            user_agent = None
            
            if request:
                ip_address = self._get_client_ip(request)
                user_agent = request.headers.get("user-agent")
            
            # 機密情報のマスキング
            if details and self.config.AUDIT_MASK_SENSITIVE:
                details = self._mask_sensitive_data(details)
            
            # 監査ログの作成
            audit_log = AuditLog(
                user_id=user_id,
                user_type=user_type,
                event_type=event_type,
                resource=resource,
                action=action,
                success=success,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
                session_id=session_id
            )
            
            # データベースに保存
            self.db.add(audit_log)
            self.db.commit()
            self.db.refresh(audit_log)
            
            return audit_log
            
        except Exception as e:
            # データベースの状態を確認
            try:
                self.db.rollback()
            except Exception as rollback_error:
                pass
            
            # エラーを再発生させる
            raise e
    
    def _get_client_ip(self, request: Request) -> str:
        """クライアントのIPアドレスを取得"""
        try:
            logger.debug(f"IPアドレス取得処理開始")
            logger.debug(f"  リクエストヘッダー: {dict(request.headers)}")
            
            # カスタムヘッダーから取得（テスト用）
            custom_ip = request.headers.get("x-client-ip")
            if custom_ip:
                logger.debug(f"  X-Client-IPから取得: {custom_ip}")
                return custom_ip
            
            # プロキシ経由の場合の対応
            forwarded_for = request.headers.get("x-forwarded-for")
            if forwarded_for:
                ip = forwarded_for.split(",")[0].strip()
                logger.debug(f"  X-Forwarded-Forから取得: {ip}")
                return ip
            
            real_ip = request.headers.get("x-real-ip")
            if real_ip:
                logger.debug(f"  X-Real-IPから取得: {real_ip}")
                return real_ip
            
            # クライアントの直接IP
            if request.client and request.client.host:
                ip = request.client.host
                logger.debug(f"  クライアントホストから取得: {ip}")
                return ip
            
            logger.debug(f"  IPアドレスが取得できませんでした")
            return "unknown"
            
        except Exception as e:
            logger.error(f"IPアドレス取得エラー: {e}")
            return "unknown"
    
    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """機密情報をマスキング"""
        sensitive_fields = ["password", "token", "secret", "key"]
        masked_data = data.copy()
        
        for field in sensitive_fields:
            if field in masked_data:
                masked_data[field] = "***MASKED***"
        
        return masked_data
    
    def get_user_audit_logs(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> list[AuditLog]:
        """特定ユーザーの監査ログを取得"""
        return self.db.query(AuditLog)\
            .filter(AuditLog.user_id == user_id)\
            .order_by(AuditLog.timestamp.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
    
    def get_security_alerts(
        self,
        hours: int = 24
    ) -> list[AuditLog]:
        """セキュリティアラートを取得"""
        from datetime import timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        return self.db.query(AuditLog)\
            .filter(
                AuditLog.event_type.in_([
                    AuditEventType.AUTH_LOGIN_FAILURE,
                    AuditEventType.AUTH_PERMISSION_DENIED,
                    AuditEventType.SECURITY_ALERT
                ]),
                AuditLog.timestamp >= cutoff_time
            )\
            .order_by(AuditLog.timestamp.desc())\
            .all()
    
    def get_logs(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> list[AuditLog]:
        """全ての監査ログを取得"""
        return self.db.query(AuditLog)\
            .order_by(AuditLog.timestamp.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
    
    def get_log_by_id(self, log_id: str) -> AuditLog:
        """特定の監査ログをIDで取得"""
        return self.db.query(AuditLog)\
            .filter(AuditLog.id == log_id)\
            .first()
