# app/core/security/continuous_verification/risk_engine.py
"""
リスクスコア計算エンジン
複数の要因を統合した総合的なリスク評価
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
from sqlalchemy.orm import Session
from fastapi import Request
import logging  # ロガーをインポート

from .models import RiskLevel, ThreatType
from .config import config

# ロガーの設定を追加
logger = logging.getLogger(__name__)

@dataclass
class RiskFactor:
    """リスク要因の定義"""
    name: str
    weight: float
    score: int
    details: Dict[str, Any]
    
    def __post_init__(self):
        """バリデーション"""
        if not 0 <= self.weight <= 1:
            raise ValueError("Weight must be between 0 and 1")
        if not 0 <= self.score <= 100:
            raise ValueError("Score must be between 0 and 100")

class RiskFactorType(str, Enum):
    """リスク要因のタイプ"""
    LOCATION_CHANGE = "location_change"
    TIME_ANOMALY = "time_anomaly"
    BEHAVIOR_CHANGE = "behavior_change"
    ACCESS_FREQUENCY = "access_frequency"
    PERMISSION_ESCALATION = "permission_escalation"
    DATA_ACCESS_PATTERN = "data_access_pattern"
    SESSION_ANOMALY = "session_anomaly"

class RiskEngine:
    """リスクスコア計算エンジン"""
    
    def __init__(self, db: Session):
        self.db = db
        self.risk_factors: Dict[RiskFactorType, float] = {
            RiskFactorType.LOCATION_CHANGE: 0.25,
            RiskFactorType.TIME_ANOMALY: 0.20,
            RiskFactorType.BEHAVIOR_CHANGE: 0.30,
            RiskFactorType.ACCESS_FREQUENCY: 0.15,
            RiskFactorType.PERMISSION_ESCALATION: 0.35,
            RiskFactorType.DATA_ACCESS_PATTERN: 0.25,
            RiskFactorType.SESSION_ANOMALY: 0.20,
        }
        logger.info(f"リスクエンジン初期化完了: 要因数={len(self.risk_factors)}")
    
    async def calculate_risk(self, session_id: str, request: Request, user_id: Optional[str] = None, user_type: Optional[str] = None) -> Tuple[int, List[RiskFactor]]:
        """総合リスクスコアを計算"""
        try:
            logger.debug(f"リスク計算開始: session={session_id}, user={user_id}")
            
            # 各リスク要因を計算
            risk_factors = []
            
            # 非同期関数
            location_risk = await self._calculate_location_risk(session_id, request)
            time_risk = await self._calculate_time_risk(session_id, request)
            
            # 同期関数
            behavior_risk = self._calculate_behavior_risk(session_id, request, user_id)
            access_frequency_risk = self._calculate_access_frequency_risk(session_id, request)
            permission_risk = self._calculate_permission_risk(session_id, request, user_id)
            data_access_risk = self._calculate_data_access_risk(session_id, request)
            session_risk = self._calculate_session_risk(session_id, request)
            
            # 結果を順序通りに追加
            risk_factors = [
                location_risk,
                time_risk,
                behavior_risk,
                access_frequency_risk,
                permission_risk,
                data_access_risk,
                session_risk
            ]
            
            # 重み付き平均で総合スコアを計算
            total_score = self._calculate_weighted_score(risk_factors)
            
            logger.debug(f"リスク計算完了: session={session_id}, score={total_score}")
            return total_score, risk_factors
            
        except Exception as e:
            logger.error(f"リスク計算でエラー: {e}")
            # エラー時は安全なデフォルト値
            return 50, []  # 中程度のリスク
    
    async def _calculate_location_risk(self, session_id: str, request: Request) -> RiskFactor:
        """地理的位置のリスクを計算"""
        try:
            current_ip = self._get_client_ip(request)
            
            # 簡易実装：IPアドレスの変化を検出
            # 実際の実装では地理情報サービスと連携
            score = 0
            
            # IPアドレスが変わった場合のリスク
            if session_id != 'unknown':
                # セッション履歴から前回のIPを取得（簡易実装）
                score = 20  # 軽微なリスク
            
            return RiskFactor(
                name=RiskFactorType.LOCATION_CHANGE,
                weight=self.risk_factors[RiskFactorType.LOCATION_CHANGE],
                score=score,
                details={
                    "current_ip": current_ip,
                    "implementation": "basic"
                }
            )
        except Exception as e:
            logger.error(f"地理的位置リスク計算でエラー: {e}")
            return RiskFactor(
                name=RiskFactorType.LOCATION_CHANGE,
                weight=self.risk_factors[RiskFactorType.LOCATION_CHANGE],
                score=25,  # エラー時は中程度のリスク
                details={"error": str(e)}
            )
    
    async def _calculate_time_risk(self, session_id: str, request: Request) -> RiskFactor:
        """時間帯のリスクを計算"""
        try:
            current_time = datetime.now(timezone.utc)
            hour = current_time.hour
            
            # 時間帯に基づくリスク計算
            if 0 <= hour < 6:  # 深夜時間帯（0-6時）
                score = 60
            elif 6 <= hour < 9:  # 早朝時間帯（6-9時）
                score = 30
            elif 9 <= hour < 18:  # 通常時間帯（9-18時）
                score = 0
            else:  # 夜間時間帯（18-24時）
                score = 20
            
            return RiskFactor(
                name=RiskFactorType.TIME_ANOMALY,
                weight=self.risk_factors[RiskFactorType.TIME_ANOMALY],
                score=score,
                details={
                    "current_time": current_time.isoformat(),
                    "hour": hour,
                    "timezone": "UTC"
                }
            )
        except Exception as e:
            logger.error(f"時間リスク計算でエラー: {e}")
            return RiskFactor(
                name=RiskFactorType.TIME_ANOMALY,
                weight=self.risk_factors[RiskFactorType.TIME_ANOMALY],
                score=0,
                details={"error": str(e)}
            )
    
    def _calculate_behavior_risk(self, session_id: str, request: Request, user_id: Optional[str] = None) -> RiskFactor:
        """行動パターンのリスクを計算"""
        try:
            if not user_id:
                return RiskFactor(
                    name=RiskFactorType.BEHAVIOR_CHANGE,
                    weight=self.risk_factors[RiskFactorType.BEHAVIOR_CHANGE],
                    score=20,  # 初回アクセス
                    details={"reason": "user_id_not_provided"}
                )
            
            # 簡易実装：エンドポイントの異常性を検出
            endpoint = str(request.url.path)
            method = request.method
            
            # 機密性の高いエンドポイントへのアクセス
            sensitive_endpoints = ['/api/admin', '/api/system', '/api/user/delete']
            if any(ep in endpoint for ep in sensitive_endpoints):
                score = 40
            else:
                score = 0
            
            return RiskFactor(
                name=RiskFactorType.BEHAVIOR_CHANGE,
                weight=self.risk_factors[RiskFactorType.BEHAVIOR_CHANGE],
                score=score,
                details={
                    "endpoint": endpoint,
                    "method": method,
                    "implementation": "basic"
                }
            )
            
        except Exception as e:
            logger.error(f"行動パターンリスク計算でエラー: {e}")
            return RiskFactor(
                name=RiskFactorType.BEHAVIOR_CHANGE,
                weight=self.risk_factors[RiskFactorType.BEHAVIOR_CHANGE],
                score=30,
                details={"error": str(e)}
            )
    
    def _calculate_access_frequency_risk(self, session_id: str, request: Request) -> RiskFactor:
        """アクセス頻度のリスクを計算"""
        try:
            # 簡易実装：現在は基本スコア
            score = 0
            
            return RiskFactor(
                name=RiskFactorType.ACCESS_FREQUENCY,
                weight=self.risk_factors[RiskFactorType.ACCESS_FREQUENCY],
                score=score,
                details={"implementation": "basic"}
            )
        except Exception as e:
            logger.error(f"アクセス頻度リスク計算でエラー: {e}")
            return RiskFactor(
                name=RiskFactorType.ACCESS_FREQUENCY,
                weight=self.risk_factors[RiskFactorType.ACCESS_FREQUENCY],
                score=0,
                details={"error": str(e)}
            )
    
    def _calculate_permission_risk(self, session_id: str, request: Request, user_id: Optional[str] = None) -> RiskFactor:
        """権限エスカレーションのリスクを計算"""
        try:
            # 簡易実装：現在は基本スコア
            score = 0
            
            return RiskFactor(
                name=RiskFactorType.PERMISSION_ESCALATION,
                weight=self.risk_factors[RiskFactorType.PERMISSION_ESCALATION],
                score=score,
                details={"implementation": "basic"}
            )
        except Exception as e:
            logger.error(f"権限リスク計算でエラー: {e}")
            return RiskFactor(
                name=RiskFactorType.PERMISSION_ESCALATION,
                weight=self.risk_factors[RiskFactorType.PERMISSION_ESCALATION],
                score=0,
                details={"error": str(e)}
            )
    
    def _calculate_data_access_risk(self, session_id: str, request: Request) -> RiskFactor:
        """データアクセスパターンのリスクを計算"""
        try:
            # 簡易実装：現在は基本スコア
            score = 0
            
            return RiskFactor(
                name=RiskFactorType.DATA_ACCESS_PATTERN,
                weight=self.risk_factors[RiskFactorType.DATA_ACCESS_PATTERN],
                score=score,
                details={"implementation": "basic"}
            )
        except Exception as e:
            logger.error(f"データアクセスリスク計算でエラー: {e}")
            return RiskFactor(
                name=RiskFactorType.DATA_ACCESS_PATTERN,
                weight=self.risk_factors[RiskFactorType.DATA_ACCESS_PATTERN],
                score=0,
                details={"error": str(e)}
            )
    
    def _calculate_session_risk(self, session_id: str, request: Request) -> RiskFactor:
        """セッション異常のリスクを計算"""
        try:
            # 簡易実装：セッションIDの妥当性チェック
            if session_id == 'unknown' or not session_id:
                score = 50
            else:
                score = 0
            
            return RiskFactor(
                name=RiskFactorType.SESSION_ANOMALY,
                weight=self.risk_factors[RiskFactorType.SESSION_ANOMALY],
                score=score,
                details={
                    "session_id": session_id,
                    "implementation": "basic"
                }
            )
        except Exception as e:
            logger.error(f"セッションリスク計算でエラー: {e}")
            return RiskFactor(
                name=RiskFactorType.SESSION_ANOMALY,
                weight=self.risk_factors[RiskFactorType.SESSION_ANOMALY],
                score=0,
                details={"error": str(e)}
            )
    
    def _calculate_weighted_score(self, risk_factors: List[RiskFactor]) -> int:
        """重み付き平均で総合スコアを計算"""
        if not risk_factors:
            return 0
        
        total_weighted_score = 0
        total_weight = 0
        
        for factor in risk_factors:
            total_weighted_score += factor.score * factor.weight
            total_weight += factor.weight
        
        if total_weight == 0:
            return 0
        
        return min(int(total_weighted_score / total_weight), 100)
    
    def _get_client_ip(self, request: Request) -> str:
        """クライアントIPを取得"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        if request.client:
            return request.client.host
        
        return "unknown"