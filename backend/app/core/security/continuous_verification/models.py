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
    
    # 実際のDB構造に合わせて修正
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=True, index=True)
    user_id = Column(String(255), nullable=True, index=True)
    risk_score = Column(Integer, nullable=True)
    risk_level = Column(String(50), nullable=True)
    # 実際のDBのカラム名に合わせて修正
    risk_factors = Column(JSON, nullable=True)
    # データベースの実際の構造に合わせてカラム名を変更
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6対応
    user_agent = Column(Text, nullable=True)
    endpoint = Column(String(500), nullable=True)
    http_method = Column(String(10), nullable=True)
    
    # インデックス（パフォーマンス向上）
    __table_args__ = (
        Index('idx_risk_scores_session_created', 'session_id', 'created_at'),
        Index('idx_risk_scores_user_created', 'user_id', 'created_at'),
        Index('idx_risk_scores_risk_level', 'risk_level'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<RiskScore(session_id={self.session_id}, score={self.risk_score}, level={self.risk_level})>"
    
    @property
    def timestamp(self):
        """後方互換性のためのプロパティ"""
        return self.created_at
    
    @property
    def factors(self):
        """後方互換性のためのプロパティ"""
        return self.risk_factors

class BehaviorPattern(Base):
    """行動パターンテーブル"""
    __tablename__ = "behavior_patterns"
    __table_args__ = {'extend_existing': True}
    
    # 実際のDB構造に合わせて修正
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=True, index=True)
    pattern_type = Column(String(100), nullable=True)  # 実際のDBに存在
    pattern_data = Column(JSON, nullable=True)
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=True)
    confidence_score = Column(Integer, default=0, nullable=True)
    sample_count = Column(Integer, default=0, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=True)
    
    def __repr__(self):
        return f"<BehaviorPattern(user_id={self.user_id}, confidence={self.confidence_score})>"

class ThreatDetection(Base):
    """脅威検出テーブル"""
    __tablename__ = "threat_detections"
    __table_args__ = {'extend_existing': True}
    
    # 実際のDB構造に合わせて修正
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    user_type = Column(String(50), nullable=False)  # 実際のDBに存在
    threat_type = Column(String(100), nullable=False, index=True)
    threat_level = Column(String(20), nullable=False, index=True)
    description = Column(Text, nullable=True)  # 実際のDBに存在
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    endpoint = Column(String(255), nullable=True)
    http_method = Column(String(10), nullable=True)
    request_data = Column(JSON, nullable=True)  # 実際のDBに存在
    response_data = Column(JSON, nullable=True)  # 実際のDBに存在
    confidence_score = Column(String(10), nullable=True)  # 実際のDBに存在
    detected_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=True, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=True)  # 実際のDBに存在
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=True)
    
    def __repr__(self):
        return f"<ThreatDetection(user_id={self.user_id}, type={self.threat_type}, level={self.threat_level})>"
    
    @property
    def timestamp(self):
        """後方互換性のためのプロパティ"""
        return self.detected_at
    
    @property
    def mitigated(self):
        """後方互換性のためのプロパティ"""
        return self.status == "resolved"