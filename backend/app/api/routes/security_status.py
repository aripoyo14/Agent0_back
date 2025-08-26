# app/api/routes/security_status.py
"""
セキュリティ状況確認用APIルート
継続的検証システムの動作状況、リスクスコア、脅威検出状況を確認
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import logging

from app.db.session import get_db
from app.core.security.continuous_verification.models import RiskScore, ThreatDetection, BehaviorPattern
from app.core.security.continuous_verification.config import config
from app.core.security.audit.decorators import audit_log
from app.core.security.audit import AuditEventType

# ロガーの設定
logger = logging.getLogger(__name__)

# FastAPIのルーターを初期化
router = APIRouter(prefix="/security", tags=["Security"])

@router.get("/status")
@audit_log(
    event_type=AuditEventType.READ_SECURITY_STATUS,
    resource="security",
    action="status_check"
)
async def get_security_status(db: Session = Depends(get_db)):
    """セキュリティシステムの全体的な状況を取得"""
    try:
        # 継続的検証システムの設定状況
        cv_status = {
            "enabled": config.ENABLED,
            "async_processing": config.ASYNC_PROCESSING,
            "debug_mode": config.DEBUG_MODE,
            "threat_detection_enabled": config.THREAT_DETECTION_ENABLED,
            "behavior_learning_enabled": config.BEHAVIOR_LEARNING_ENABLED,
            "location_monitoring_enabled": config.LOCATION_MONITORING_ENABLED,
            "time_anomaly_detection_enabled": config.TIME_ANOMALY_DETECTION_ENABLED
        }
        
        # リスク閾値設定
        risk_thresholds = {
            "low_risk": config.LOW_RISK_THRESHOLD,
            "medium_risk": config.MEDIUM_RISK_THRESHOLD,
            "high_risk": config.HIGH_RISK_THRESHOLD,
            "extreme_risk": config.EXTREME_RISK_THRESHOLD
        }
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_status": "operational",
            "continuous_verification": cv_status,
            "risk_thresholds": risk_thresholds
        }
        
    except Exception as e:
        logger.error(f"セキュリティ状況取得でエラー: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"セキュリティ状況の取得に失敗: {str(e)}"
        )

@router.get("/metrics/risk-scores")
@audit_log(
    event_type=AuditEventType.READ_SECURITY_METRICS,
    resource="security",
    action="risk_metrics"
)
async def get_risk_score_metrics(
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """リスクスコアの統計情報を取得"""
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # 時間範囲内のリスクスコア統計
        risk_stats = db.query(
            func.avg(RiskScore.risk_score).label("avg_score"),
            func.max(RiskScore.risk_score).label("max_score"),
            func.min(RiskScore.risk_score).label("min_score"),
            func.count(RiskScore.id).label("total_records")
        ).filter(RiskScore.created_at >= cutoff_time).first()
        
        # リスクレベル別の集計
        risk_level_counts = db.query(
            RiskScore.risk_level,
            func.count(RiskScore.id).label("count")
        ).filter(RiskScore.created_at >= cutoff_time).group_by(RiskScore.risk_level).all()
        
        # 高リスクセッション（スコア80以上）
        high_risk_sessions = db.query(
            RiskScore.session_id,
            RiskScore.risk_score,
            RiskScore.created_at,
            RiskScore.endpoint
        ).filter(
            and_(
                RiskScore.created_at >= cutoff_time,
                RiskScore.risk_score >= 80
            )
        ).order_by(desc(RiskScore.created_at)).limit(10).all()
        
        return {
            "time_range_hours": hours,
            "statistics": {
                "average_score": float(risk_stats.avg_score) if risk_stats.avg_score else 0,
                "max_score": risk_stats.max_score or 0,
                "min_score": risk_stats.min_score or 0,
                "total_records": risk_stats.total_records or 0
            },
            "risk_level_distribution": [
                {"level": level, "count": count} 
                for level, count in risk_level_counts
            ],
            "high_risk_sessions": [
                {
                    "session_id": session.session_id,
                    "risk_score": session.risk_score,
                    "timestamp": session.created_at.isoformat(),
                    "endpoint": session.endpoint
                }
                for session in high_risk_sessions
            ]
        }
        
    except Exception as e:
        logger.error(f"リスクスコアメトリクス取得でエラー: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"リスクスコアメトリクスの取得に失敗: {str(e)}"
        )

@router.get("/metrics/threats")
@audit_log(
    event_type=AuditEventType.DATA_READ,
    resource="security",
    action="threat_metrics"
)
async def get_threat_metrics(
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """脅威検出の統計情報を取得"""
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # 脅威タイプ別の集計
        threat_type_counts = db.query(
            ThreatDetection.threat_type,
            func.count(ThreatDetection.id).label("count")
        ).filter(ThreatDetection.created_at >= cutoff_time).group_by(ThreatDetection.threat_type).all()
        
        # 脅威レベル別の集計
        threat_level_counts = db.query(
            ThreatDetection.threat_level,
            func.count(ThreatDetection.id).label("count")
        ).filter(ThreatDetection.created_at >= cutoff_time).group_by(ThreatDetection.threat_level).all()
        
        # 最近の脅威検出（最新10件）
        recent_threats = db.query(
            ThreatDetection.session_id,
            ThreatDetection.threat_type,
            ThreatDetection.threat_level,
            ThreatDetection.created_at,
            ThreatDetection.mitigated
        ).filter(ThreatDetection.created_at >= cutoff_time).order_by(desc(ThreatDetection.created_at)).limit(10).all()
        
        return {
            "time_range_hours": hours,
            "threat_type_distribution": [
                {"type": threat_type, "count": count} 
                for threat_type, count in threat_type_counts
            ],
            "threat_level_distribution": [
                {"level": level, "count": count} 
                for level, count in threat_level_counts
            ],
            "recent_threats": [
                {
                    "session_id": threat.session_id,
                    "threat_type": threat.threat_type,
                    "threat_level": threat.threat_level,
                    "timestamp": threat.created_at.isoformat(),
                    "mitigated": threat.mitigated
                }
                for threat in recent_threats
            ]
        }
        
    except Exception as e:
        logger.error(f"脅威メトリクス取得でエラー: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"脅威メトリクスの取得に失敗: {str(e)}"
        )

@router.get("/metrics/sessions")
@audit_log(
    event_type=AuditEventType.DATA_READ,
    resource="security",
    action="session_metrics"
)
async def get_session_metrics(
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """セッション監視の統計情報を取得"""
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # セッション別のリスクスコア統計
        session_stats = db.query(
            RiskScore.session_id,
            func.avg(RiskScore.risk_score).label("avg_score"),
            func.max(RiskScore.risk_score).label("max_score"),
            func.count(RiskScore.id).label("access_count")
        ).filter(RiskScore.created_at >= cutoff_time).group_by(RiskScore.session_id).all()
        
        # 行動パターンの学習状況
        behavior_patterns = db.query(
            BehaviorPattern.user_id,
            BehaviorPattern.confidence_score,
            BehaviorPattern.sample_count,
            BehaviorPattern.last_updated
        ).order_by(desc(BehaviorPattern.last_updated)).limit(10).all()
        
        return {
            "time_range_hours": hours,
            "session_risk_summary": [
                {
                    "session_id": session.session_id,
                    "average_risk_score": float(session.avg_score) if session.avg_score else 0,
                    "max_risk_score": session.max_score or 0,
                    "access_count": session.access_count or 0
                }
                for session in session_stats
            ],
            "behavior_patterns": [
                {
                    "user_id": pattern.user_id,
                    "confidence_score": pattern.confidence_score,
                    "sample_count": pattern.sample_count,
                    "last_updated": pattern.last_updated.isoformat()
                }
                for pattern in behavior_patterns
            ]
        }
        
    except Exception as e:
        logger.error(f"セッションメトリクス取得でエラー: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"セッションメトリクスの取得に失敗: {str(e)}"
        )

@router.get("/live/session/{session_id}")
@audit_log(
    event_type=AuditEventType.DATA_READ,
    resource="security",
    action="live_session_check"
)
async def get_live_session_status(
    session_id: str,
    db: Session = Depends(get_db)
):
    """特定セッションの現在のセキュリティ状況を取得"""
    try:
        # 最新のリスクスコア
        latest_risk = db.query(RiskScore).filter(
            RiskScore.session_id == session_id
        ).order_by(desc(RiskScore.created_at)).first()
        
        # セッションの脅威検出履歴
        threats = db.query(ThreatDetection).filter(
            ThreatDetection.session_id == session_id
        ).order_by(desc(ThreatDetection.created_at)).limit(5).all()
        
        # セッションのアクセス履歴
        access_history = db.query(RiskScore).filter(
            RiskScore.session_id == session_id
        ).order_by(desc(RiskScore.created_at)).limit(10).all()
        
        return {
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "current_risk_score": latest_risk.risk_score if latest_risk else None,
            "current_risk_level": latest_risk.risk_level if latest_risk else None,
            "threats_detected": [
                {
                    "threat_type": threat.threat_type,
                    "threat_level": threat.threat_level,
                    "timestamp": threat.created_at.isoformat(),
                    "mitigated": threat.mitigated
                }
                for threat in threats
            ],
            "access_history": [
                {
                    "timestamp": access.created_at.isoformat(),
                    "risk_score": access.risk_score,
                    "endpoint": access.endpoint,
                    "ip_address": access.ip_address
                }
                for access in access_history
            ]
        }
        
    except Exception as e:
        logger.error(f"セッション状況取得でエラー: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"セッション状況の取得に失敗: {str(e)}"
        )

@router.get("/config")
@audit_log(
    event_type=AuditEventType.DATA_READ,
    resource="security",
    action="config_check"
)
async def get_security_config():
    """セキュリティ設定の現在値を取得"""
    try:
        return {
            "continuous_verification": {
                "enabled": config.ENABLED,
                "async_processing": config.ASYNC_PROCESSING,
                "debug_mode": config.DEBUG_MODE,
                "threat_detection_enabled": config.THREAT_DETECTION_ENABLED,
                "behavior_learning_enabled": config.BEHAVIOR_LEARNING_ENABLED,
                "location_monitoring_enabled": config.LOCATION_MONITORING_ENABLED,
                "time_anomaly_detection_enabled": config.TIME_ANOMALY_DETECTION_ENABLED
            },
            "risk_thresholds": {
                "low_risk": config.LOW_RISK_THRESHOLD,
                "medium_risk": config.MEDIUM_RISK_THRESHOLD,
                "high_risk": config.HIGH_RISK_THRESHOLD,
                "extreme_risk": config.EXTREME_RISK_THRESHOLD
            },
            "performance": {
                "cache_ttl_seconds": config.CACHE_TTL_SECONDS,
                "max_session_age_hours": config.MAX_SESSION_AGE_HOURS,
                "batch_processing_size": config.BATCH_PROCESSING_SIZE
            },
            "alerts": {
                "security_alert_enabled": config.SECURITY_ALERT_ENABLED,
                "alert_email_enabled": config.ALERT_EMAIL_ENABLED,
                "alert_slack_enabled": config.ALERT_SLACK_ENABLED
            }
        }
        
    except Exception as e:
        logger.error(f"セキュリティ設定取得でエラー: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"セキュリティ設定の取得に失敗: {str(e)}"
        )
