# app/core/security/continuous_verification/models.py
"""
継続的検証のデータモデル
SQLAlchemy ORMを使用した堅牢なデータ構造
"""
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, String, DateTime, Integer, JSON, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.base_class import Base
import uuid

class RiskLevel(str, Enum):
    """リスクレベルの定義"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"
    
    @classmethod
    def from_score(cls, score: int) -> "RiskLevel":
        """スコアからリスクレベルを判定"""
        if score <= 30:
            return cls.LOW
        elif score <= 60:
            return cls.MEDIUM
        elif score <= 80:
            return cls.HIGH
        else:
            return cls.EXTREME

class ThreatType(str, Enum):
    """脅威タイプの定義"""
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    UNUSUAL_BEHAVIOR = "unusual_behavior"
    LOCATION_ANOMALY = "location_anomaly"
    TIME_ANOMALY = "time_anomaly"
    ACCESS_PATTERN_CHANGE = "access_pattern_change"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"

class RiskScore(Base):
    """リスクスコアテーブル"""
    __tablename__ = "risk_scores"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    risk_score = Column(Integer, nullable=False)
    risk_level = Column(String(20), nullable=False)
    factors = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    ip_address = Column(String(45), nullable=True)  # IPv6対応
    user_agent = Column(Text, nullable=True)
    endpoint = Column(String(255), nullable=True)
    http_method = Column(String(10), nullable=True)
    
    # インデックス（パフォーマンス向上）
    __table_args__ = (
        Index('idx_risk_scores_session_timestamp', 'session_id', 'timestamp'),
        Index('idx_risk_scores_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_risk_scores_risk_level', 'risk_level'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<RiskScore(session_id={self.session_id}, score={self.risk_score}, level={self.risk_level})>"

class BehaviorPattern(Base):
    """行動パターンテーブル"""
    __tablename__ = "behavior_patterns"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), nullable=False, unique=True, index=True)
    pattern_data = Column(JSON, nullable=False)
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    confidence_score = Column(Integer, default=0, nullable=False)
    sample_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    def __repr__(self):
        return f"<BehaviorPattern(user_id={self.user_id}, confidence={self.confidence_score})>"

class ThreatDetection(Base):
    """脅威検出テーブル"""
    __tablename__ = "threat_detections"
    __table_args__ = {'extend_existing': True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    threat_type = Column(String(50), nullable=False)
    threat_level = Column(String(20), nullable=False)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    mitigated = Column(Boolean, default=False, nullable=False)
    mitigation_action = Column(String(100), nullable=True)
    risk_score_at_detection = Column(Integer, nullable=True)
    
    # インデックス
    __table_args__ = (
        Index('idx_threat_detections_session_timestamp', 'session_id', 'timestamp'),
        Index('idx_threat_detections_type_level', 'threat_type', 'threat_level'),
        Index('idx_threat_detections_mitigated', 'mitigated'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<ThreatDetection(session_id={self.session_id}, type={self.threat_type}, level={self.threat_level})>"