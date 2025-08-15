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
        """監査イベントを記録"""
        
        if not self.config.AUDIT_ENABLED:
            return None
        
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
    
    def _get_client_ip(self, request: Request) -> str:
        """クライアントのIPアドレスを取得"""
        try:
            # プロキシ経由の場合の対応
            forwarded_for = request.headers.get("x-forwarded-for")
            if forwarded_for:
                return forwarded_for.split(",")[0].strip()
            
            real_ip = request.headers.get("x-real-ip")
            if real_ip:
                return real_ip
            
            return request.client.host if request.client else "unknown"
        except Exception:
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
