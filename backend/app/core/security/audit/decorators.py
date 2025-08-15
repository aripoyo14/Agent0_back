"""
監査ログ用デコレーター
エンドポイントで簡単に監査ログを記録
"""
from functools import wraps
from typing import Optional, Callable
from app.core.security.audit.service import AuditService
from app.core.security.audit.models import AuditEventType
from app.core.dependencies import get_db
from sqlalchemy.orm import Session


def audit_log(
    event_type: AuditEventType,
    resource: Optional[str] = None,
    action: Optional[str] = None
):
    """
    監査ログを記録するデコレーター
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # リクエストオブジェクトをkwargsから取得
            request = kwargs.get('http_request')
            
            # データベースセッションを取得
            db = next(get_db())
            audit_service = AuditService(db)
            
            try:
                # 関数を実行
                result = await func(*args, **kwargs)
                
                # 成功時の監査ログ
                audit_service.log_event(
                    event_type=event_type,
                    resource=resource,
                    action=action,
                    success=True,
                    request=request,
                    details={"result": "success"}
                )
                
                return result
                
            except Exception as e:
                # 失敗時の監査ログ（イベントタイプを適切に変更）
                if "login" in action:
                    failure_event_type = AuditEventType.AUTH_LOGIN_FAILURE
                else:
                    failure_event_type = event_type
                    
                # 失敗時の監査ログ
                audit_service.log_event(
                    event_type=failure_event_type,
                    resource=resource,
                    action=action,
                    success=False,
                    request=request,
                    details={"error": str(e), "result": "failure"}
                )
                raise
        
        return wrapper
    return decorator


def audit_log_sync(
    event_type: AuditEventType,
    resource: Optional[str] = None,
    action: Optional[str] = None
):
    """
    同期関数用の監査ログデコレーター
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # リクエストオブジェクトをkwargsから取得
            request = kwargs.get('http_request')
            
            # データベースセッションを取得
            db = next(get_db())
            audit_service = AuditService(db)
            
            try:
                # 関数を実行
                result = func(*args, **kwargs)
                
                # 成功時の監査ログ
                audit_service.log_event(
                    event_type=event_type,
                    resource=resource,
                    action=action,
                    success=True,
                    request=request,
                    details={"result": "success"}
                )
                
                return result
                
            except Exception as e:
                # 失敗時の監査ログ
                audit_service.log_event(
                    event_type=event_type,
                    resource=resource,
                    action=action,
                    success=False,
                    request=request,
                    details={"error": str(e), "result": "failure"}
                )
                raise
        
        return wrapper
    return decorator
