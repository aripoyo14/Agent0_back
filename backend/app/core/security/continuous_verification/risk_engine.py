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

from .models import RiskLevel, ThreatType
from .config import config

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
    
    async def calculate_risk(self, session_id: str, request: Request, user_id: Optional[str] = None, user_type: Optional[str] = None) -> Tuple[int, List[RiskFactor]]:
        try:
            # リスク要因の順序を固定
            risk_factor_order = [
                RiskFactorType.LOCATION_CHANGE,
                RiskFactorType.TIME_ANOMALY,
                RiskFactorType.BEHAVIOR_CHANGE,
                RiskFactorType.ACCESS_FREQUENCY,
                RiskFactorType.PERMISSION_ESCALATION,
                RiskFactorType.DATA_ACCESS_PATTERN,
                RiskFactorType.SESSION_ANOMALY
            ]
            
            # 各リスク要因を計算（非同期と同期を適切に処理）
            risk_factors = []
            
            # 非同期関数
            location_risk = await self._calculate_location_risk(session_id, request)
            time_risk = await self._calculate_time_risk(session_id, request)
            
            # 同期関数（await不要）
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
            
            return total_score, risk_factors
            
        except Exception as e:
            # エラー時は安全なデフォルト値
            return 0, []
    
    async def _calculate_location_risk(self, session_id: str, request: Request) -> RiskFactor:
        """地理的位置のリスクを計算"""
        try:
            current_ip = self._get_client_ip(request)
            previous_ip = await self._get_previous_ip(session_id)
            
            if not previous_ip or current_ip == previous_ip:
                score = 0
            else:
                # 実際の地理情報サービスと連携
                try:
                    from app.services.geo_location import GeoLocationService
                    geo_service = GeoLocationService()
                    
                    current_location = await geo_service.get_location(current_ip)
                    previous_location = await geo_service.get_location(previous_ip)
                    
                    if current_location and previous_location:
                        distance = geo_service.calculate_distance(
                            current_location, previous_location
                        )
                        
                        # 距離に基づくリスク計算
                        if distance < 10:  # 10km以内
                            score = 10
                        elif distance < 100:  # 100km以内
                            score = 30
                        elif distance < 1000:  # 1000km以内
                            score = 60
                        else:  # 1000km以上
                            score = 90
                    else:
                        score = 50  # 地理情報取得失敗
                        
                except ImportError:
                    # 地理情報サービスが利用できない場合
                    score = 25  # 中程度のリスク
            
            return RiskFactor(
                name=RiskFactorType.LOCATION_CHANGE,
                weight=self.risk_factors[RiskFactorType.LOCATION_CHANGE],
                score=score,
                details={
                    "current_ip": current_ip,
                    "previous_ip": previous_ip,
                    "distance_km": distance if 'distance' in locals() else None,
                    "current_location": current_location if 'current_location' in locals() else None
                }
            )
        except Exception as e:
            logger.error(f"地理的位置リスク計算でエラー: {e}")
            return RiskFactor(
                name=RiskFactorType.LOCATION_CHANGE,
                weight=self.risk_factors[RiskFactorType.LOCATION_CHANGE],
                score=50,  # エラー時は中程度のリスク
                details={"error": str(e)}
            )
    
    async def _calculate_time_risk(self, session_id: str, request: Request) -> RiskFactor:
        """時間帯のリスクを計算"""
        try:
            current_time = datetime.now(timezone.utc)
            user_timezone = await self._get_user_timezone(session_id)
            
            # ユーザーの通常アクセス時間帯と比較
            if user_timezone:
                local_time = current_time.astimezone(user_timezone)
                hour = local_time.hour
                
                # 深夜時間帯（0-6時）はリスク高
                if 0 <= hour < 6:
                    score = 80
                # 早朝時間帯（6-9時）はリスク中
                elif 6 <= hour < 9:
                    score = 40
                # 通常時間帯（9-18時）はリスク低
                elif 9 <= hour < 18:
                    score = 0
                # 夜間時間帯（18-24時）はリスク低
                else:
                    score = 20
            else:
                score = 0
            
            return RiskFactor(
                name=RiskFactorType.TIME_ANOMALY,
                weight=self.risk_factors[RiskFactorType.TIME_ANOMALY],
                score=score,
                details={
                    "current_time": current_time.isoformat(),
                    "user_timezone": user_timezone,
                    "local_hour": hour if 'hour' in locals() else None
                }
            )
        except Exception as e:
            return RiskFactor(
                name=RiskFactorType.TIME_ANOMALY,
                weight=self.risk_factors[RiskFactorType.TIME_ANOMALY],
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
        # 既存の実装を再利用
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def _get_previous_ip(self, session_id: str) -> Optional[str]:
        """前回のIPアドレスを取得"""
        # 実装例（データベースから取得）
        try:
            # 実際の実装ではデータベースクエリ
            return None
        except Exception:
            return None
    
    async def _calculate_geographic_distance(self, ip1: str, ip2: str) -> float:
        """IPアドレス間の地理的距離を計算"""
        # 実装例（実際の地理情報サービスと連携）
        try:
            # 簡易的な実装
            return 0.0
        except Exception:
            return 0.0
    
    async def _get_user_timezone(self, session_id: str) -> Optional[str]:
        """ユーザーのタイムゾーンを取得"""
        # 実装例（データベースから取得）
        try:
            # 実際の実装ではデータベースクエリ
            return "Asia/Tokyo"  # デフォルト
        except Exception:
            return None

    def _calculate_behavior_risk(self, session_id: str, request: Request, user_id: Optional[str] = None) -> RiskFactor:
        """行動パターンのリスクを計算"""
        try:
            if not user_id:
                return RiskFactor(
                    name=RiskFactorType.BEHAVIOR_CHANGE,
                    weight=self.risk_factors[RiskFactorType.BEHAVIOR_CHANGE],
                    score=0,
                    details={"reason": "user_id_not_provided"}
                )
            
            # ユーザーの過去の行動パターンを取得
            behavior_pattern = self._get_user_behavior_pattern(user_id)
            if not behavior_pattern:
                return RiskFactor(
                    name=RiskFactorType.BEHAVIOR_CHANGE,
                    weight=self.risk_factors[RiskFactorType.BEHAVIOR_CHANGE],
                    score=20,  # 初回アクセス
                    details={"reason": "first_access"}
                )
            
            # 現在のリクエストパターンを分析
            current_pattern = self._analyze_current_request(request)
            
            # パターンの類似度を計算
            similarity_score = self._calculate_pattern_similarity(
                behavior_pattern.pattern_data, 
                current_pattern
            )
            
            # 類似度に基づくリスクスコア
            if similarity_score > 0.8:
                score = 0  # 正常な行動
            elif similarity_score > 0.6:
                score = 20  # 軽微な変化
            elif similarity_score > 0.4:
                score = 50  # 中程度の変化
            else:
                score = 80  # 大きな変化
            
            return RiskFactor(
                name=RiskFactorType.BEHAVIOR_CHANGE,
                weight=self.risk_factors[RiskFactorType.BEHAVIOR_CHANGE],
                score=score,
                details={
                    "similarity_score": similarity_score,
                    "pattern_change": 1 - similarity_score,
                    "current_pattern": current_pattern
                }
            )
            
        except Exception as e:
            logger.error(f"行動パターンリスク計算でエラー: {e}")
            return RiskFactor(
                name=RiskFactorType.BEHAVIOR_CHANGE,
                weight=self.risk_factors[RiskFactorType.BEHAVIOR_CHANGE],
                score=30,  # エラー時は軽微なリスク
                details={"error": str(e)}
            )