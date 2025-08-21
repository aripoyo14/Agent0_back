from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.security.audit.service import AuditService
from app.core.security.audit.models import AuditLog
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from typing import List

router = APIRouter(prefix="/audit-logs", tags=["AuditLogs"])

@router.get("/", response_model=List[dict])
async def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """監査ログの一覧を取得"""
    try:
        audit_service = AuditService(db)
        logs = audit_service.get_logs()  # 非同期メソッドを同期メソッドに変更
        return [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "event_type": log.event_type,
                "resource": log.resource,
                "action": log.action,
                "user_id": log.user_id,
                "user_type": log.user_type,
                "success": log.success,
                "details": log.details
            }
            for log in logs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"監査ログの取得でエラー: {str(e)}")

@router.get("/{log_id}", response_model=dict)
async def get_audit_log(
    log_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """特定の監査ログを取得"""
    try:
        audit_service = AuditService(db)
        log = audit_service.get_log_by_id(log_id)  # 非同期メソッドを同期メソッドに変更
        if not log:
            raise HTTPException(status_code=404, detail="監査ログが見つかりません")
        
        return {
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "event_type": log.event_type,
            "resource": log.resource,
            "action": log.action,
            "user_id": log.user_id,
            "user_type": log.user_type,
            "success": log.success,
            "details": log.details
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"監査ログの取得でエラー: {str(e)}")
