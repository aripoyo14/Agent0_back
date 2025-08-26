from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.security.audit.service import AuditService
from app.core.security.audit.models import AuditLog, AuditEventType
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from typing import List, Optional
from datetime import datetime, timedelta

router = APIRouter(prefix="/audit-logs", tags=["AuditLogs"])

@router.get("/", response_model=List[dict])
async def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    event_type: Optional[str] = Query(None, description="イベントタイプでフィルタ"),
    resource: Optional[str] = Query(None, description="リソースでフィルタ"),
    user_id: Optional[str] = Query(None, description="ユーザーIDでフィルタ"),
    user_type: Optional[str] = Query(None, description="ユーザータイプでフィルタ"),
    success: Optional[bool] = Query(None, description="成功/失敗でフィルタ"),
    hours: Optional[int] = Query(24, description="過去何時間のログを取得するか"),
    limit: int = Query(100, ge=1, le=1000, description="取得件数"),
    offset: int = Query(0, ge=0, description="オフセット")
):
    """監査ログの一覧を取得（フィルタリング対応）"""
    try:
        audit_service = AuditService(db)
        
        # フィルタリング条件を構築
        filters = {}
        if event_type:
            filters["event_type"] = event_type
        if resource:
            filters["resource"] = resource
        if user_id:
            filters["user_id"] = user_id
        if user_type:
            filters["user_type"] = user_type
        if success is not None:
            filters["success"] = success
        
        # 時間範囲を設定
        if hours:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            filters["since"] = cutoff_time
        
        logs = audit_service.get_logs_with_filters(
            filters=filters,
            limit=limit,
            offset=offset
        )
        
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
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "details": log.details,
                "session_id": log.session_id
            }
            for log in logs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"監査ログの取得でエラー: {str(e)}")

@router.get("/categories", response_model=dict)
async def get_audit_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """監査ログのカテゴリ別統計を取得"""
    try:
        audit_service = AuditService(db)
        
        # 検索・分析系API
        search_events = [
            AuditEventType.SEARCH_NETWORK_MAP,
            AuditEventType.SEARCH_MINUTES,
            AuditEventType.SEARCH_POLICY_TAGS,
            AuditEventType.SEARCH_EXPERTS,
            AuditEventType.SEARCH_POLICY_PROPOSALS,
            AuditEventType.SEARCH_COMMENTS,
            AuditEventType.SEARCH_USERS,
            AuditEventType.SEARCH_DEPARTMENTS,
            AuditEventType.SEARCH_POSITIONS
        ]
        
        # データ読み取り系API
        read_events = [
            AuditEventType.READ_EXPERT_PROFILE,
            AuditEventType.READ_EXPERT_INSIGHTS,
            AuditEventType.READ_USER_PROFILE,
            AuditEventType.READ_MEETING_DETAILS,
            AuditEventType.READ_MEETING_EVALUATION,
            AuditEventType.READ_POLICY_PROPOSAL,
            AuditEventType.READ_POLICY_COMMENTS,
            AuditEventType.READ_INVITATION_CODES,
            AuditEventType.READ_SECURITY_STATUS,
            AuditEventType.READ_SECURITY_METRICS,
            AuditEventType.READ_SECURITY_CONFIG
        ]
        
        # 権限変更系API
        permission_events = [
            AuditEventType.ROLE_ASSIGNMENT,
            AuditEventType.ROLE_REMOVAL,
            AuditEventType.PERMISSION_GRANT,
            AuditEventType.PERMISSION_REVOKE,
            AuditEventType.USER_ACTIVATION,
            AuditEventType.USER_DEACTIVATION,
            AuditEventType.EXPERT_ACTIVATION,
            AuditEventType.EXPERT_DEACTIVATION,
            AuditEventType.MFA_ENABLE,
            AuditEventType.MFA_DISABLE,
            AuditEventType.INVITATION_CODE_GENERATE,
            AuditEventType.INVITATION_CODE_DEACTIVATE
        ]
        
        # 各カテゴリの統計を取得
        search_stats = audit_service.get_event_type_statistics(search_events)
        read_stats = audit_service.get_event_type_statistics(read_events)
        permission_stats = audit_service.get_event_type_statistics(permission_events)
        
        return {
            "search_analysis": {
                "description": "検索・分析系API - 機密情報へのアクセス追跡",
                "total_events": search_stats["total"],
                "success_rate": search_stats["success_rate"],
                "recent_events": search_stats["recent_count"]
            },
            "data_read": {
                "description": "データ読み取り系API - 情報漏洩の追跡",
                "total_events": read_stats["total"],
                "success_rate": read_stats["success_rate"],
                "recent_events": read_stats["recent_count"]
            },
            "permission_changes": {
                "description": "権限変更系API - セキュリティ侵害の追跡",
                "total_events": permission_stats["total"],
                "success_rate": permission_stats["success_rate"],
                "recent_events": permission_stats["recent_count"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"カテゴリ統計の取得でエラー: {str(e)}")

@router.get("/{log_id}", response_model=dict)
async def get_audit_log(
    log_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """特定の監査ログを取得"""
    try:
        audit_service = AuditService(db)
        log = audit_service.get_log_by_id(log_id)
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
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "details": log.details,
            "session_id": log.session_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"監査ログの取得でエラー: {str(e)}")
