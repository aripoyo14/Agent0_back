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
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from fastapi import Request

from .models import RiskScore, BehaviorPattern, ThreatDetection, RiskLevel, ThreatType
from .config import config

# ロガーの設定
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
            # 実装例（実際のIP地理情報サービスと連携）
            current_ip = self._get_client_ip(request)
            previous_ip = await self._get_previous_ip(session_id)
            
            if not previous_ip or current_ip == previous_ip:
                score = 0
            else:
                # 地理的距離に基づくリスク計算
                distance = await self._calculate_geographic_distance(previous_ip, current_ip)
                score = min(distance * 2, 100)  # 距離に応じたスコア
            
            return RiskFactor(
                name=RiskFactorType.LOCATION_CHANGE,
                weight=self.risk_factors[RiskFactorType.LOCATION_CHANGE],
                score=score,
                details={
                    "current_ip": current_ip,
                    "previous_ip": previous_ip,
                    "distance_km": distance if 'distance' in locals() else None
                }
            )
        except Exception as e:
            return RiskFactor(
                name=RiskFactorType.LOCATION_CHANGE,
                weight=self.risk_factors[RiskFactorType.LOCATION_CHANGE],
                score=0,
                details={"error": str(e)}
            )
    
    async def _calculate_time_risk(self, session_id: str, request: Request) -> RiskFactor:
        """時間帯のリスクを計算"""
        try:
            current_time = datetime.now(timezone.utc)
            user_timezone_str = await self._get_user_timezone(session_id)
            
            # ユーザーの通常アクセス時間帯と比較
            if user_timezone_str:
                user_timezone = self._get_timezone_object(user_timezone_str)
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
            else:
                score = 0
            
            return RiskFactor(
                name=RiskFactorType.TIME_ANOMALY,
                weight=self.risk_factors[RiskFactorType.TIME_ANOMALY],
                score=score,
                details={
                    "current_time": current_time.isoformat(),
                    "user_timezone": user_timezone_str,
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
    
    def _calculate_behavior_risk(self, session_id: str, request: Request, user_id: Optional[str] = None) -> RiskFactor:
        """行動パターンのリスクを計算"""
        try:
            if not user_id:
                return RiskFactor(
                    name=RiskFactorType.BEHAVIOR_CHANGE,
                    weight=self.risk_factors[RiskFactorType.BEHAVIOR_CHANGE],
                    score=0,
                    details={"reason": "no_user_id"}
                )
            
            # ユーザーの行動パターンを取得
            behavior_pattern = self.db.query(BehaviorPattern).filter(
                BehaviorPattern.user_id == user_id
            ).first()
            
            if not behavior_pattern or behavior_pattern.confidence_score < 10:
                # 十分なデータがない場合は低リスク
                return RiskFactor(
                    name=RiskFactorType.BEHAVIOR_CHANGE,
                    weight=self.risk_factors[RiskFactorType.BEHAVIOR_CHANGE],
                    score=10,
                    details={"reason": "insufficient_behavior_data"}
                )
            
            # 現在のリクエストと過去のパターンを比較
            current_endpoint = getattr(request, 'path', str(request.url.path) if hasattr(request, 'url') else '/unknown')
            current_method = request.method
            current_ip = self._get_client_ip(request)
            
            # 過去の行動データから異常度を計算
            anomaly_score = self._calculate_behavior_anomaly(
                behavior_pattern.pattern_data,
                current_endpoint,
                current_method,
                current_ip
            )
            
            return RiskFactor(
                name=RiskFactorType.BEHAVIOR_CHANGE,
                weight=self.risk_factors[RiskFactorType.BEHAVIOR_CHANGE],
                score=anomaly_score,
                details={
                    "current_endpoint": current_endpoint,
                    "current_method": current_method,
                    "current_ip": current_ip,
                    "confidence_score": behavior_pattern.confidence_score,
                    "anomaly_score": anomaly_score
                }
            )
            
        except Exception as e:
            logger.error(f"行動パターンリスク計算でエラー: {e}")
            return RiskFactor(
                name=RiskFactorType.BEHAVIOR_CHANGE,
                weight=self.risk_factors[RiskFactorType.BEHAVIOR_CHANGE],
                score=0,
                details={"error": str(e)}
            )
    
    def _calculate_access_frequency_risk(self, session_id: str, request: Request) -> RiskFactor:
        """アクセス頻度のリスクを計算"""
        try:
            current_time = datetime.now(timezone.utc)
            window_start = current_time - timedelta(minutes=5)  # 5分間のウィンドウ
            
            # 過去5分間のアクセス回数を取得
            recent_accesses = self.db.query(RiskScore).filter(
                and_(
                    RiskScore.session_id == session_id,
                    RiskScore.created_at >= window_start
                )
            ).count()
            
            # アクセス頻度に基づくリスク計算
            if recent_accesses == 0:
                score = 0
            elif recent_accesses <= 5:
                score = 10
            elif recent_accesses <= 20:
                score = 30
            elif recent_accesses <= 50:
                score = 60
            elif recent_accesses <= 100:
                score = 80
            else:
                score = 100
            
            return RiskFactor(
                name=RiskFactorType.ACCESS_FREQUENCY,
                weight=self.risk_factors[RiskFactorType.ACCESS_FREQUENCY],
                score=score,
                details={
                    "recent_accesses": recent_accesses,
                    "window_minutes": 5,
                    "current_time": current_time.isoformat()
                }
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
        """権限昇格のリスクを計算"""
        try:
            if not user_id:
                return RiskFactor(
                    name=RiskFactorType.PERMISSION_ESCALATION,
                    weight=self.risk_factors[RiskFactorType.PERMISSION_ESCALATION],
                    score=0,
                    details={"reason": "no_user_id"}
                )
            
            # エンドポイントの権限レベルを判定
            endpoint = getattr(request, 'path', str(request.url.path) if hasattr(request, 'url') else '/unknown')
            method = request.method
            
            # 高権限エンドポイントの判定
            high_privilege_endpoints = [
                "/api/admin/",
                "/api/users/",
                "/api/system/",
                "/api/security/"
            ]
            
            # 危険なHTTPメソッドの判定
            dangerous_methods = ["DELETE", "PUT", "PATCH"]
            
            risk_score = 0
            
            # 高権限エンドポイントへのアクセス
            if any(ep in endpoint for ep in high_privilege_endpoints):
                risk_score += 40
            
            # 危険なHTTPメソッドの使用
            if method in dangerous_methods:
                risk_score += 30
            
            # 大量データ操作の検出
            if "bulk" in endpoint.lower() or "batch" in endpoint.lower():
                risk_score += 20
            
            # 設定変更系のエンドポイント
            if "config" in endpoint.lower() or "settings" in endpoint.lower():
                risk_score += 25
            
            return RiskFactor(
                name=RiskFactorType.PERMISSION_ESCALATION,
                weight=self.risk_factors[RiskFactorType.PERMISSION_ESCALATION],
                score=min(risk_score, 100),
                details={
                    "endpoint": endpoint,
                    "method": method,
                    "high_privilege": any(ep in endpoint for ep in high_privilege_endpoints),
                    "dangerous_method": method in dangerous_methods,
                    "risk_factors": {
                        "high_privilege_endpoint": any(ep in endpoint for ep in high_privilege_endpoints),
                        "dangerous_method": method in dangerous_methods,
                        "bulk_operation": "bulk" in endpoint.lower() or "batch" in endpoint.lower(),
                        "config_change": "config" in endpoint.lower() or "settings" in endpoint.lower()
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"権限昇格リスク計算でエラー: {e}")
            return RiskFactor(
                name=RiskFactorType.PERMISSION_ESCALATION,
                weight=self.risk_factors[RiskFactorType.PERMISSION_ESCALATION],
                score=0,
                details={"error": str(e)}
            )
    
    def _calculate_data_access_risk(self, session_id: str, request: Request) -> RiskFactor:
        """データアクセスパターンのリスクを計算"""
        try:
            endpoint = getattr(request, 'path', str(request.url.path) if hasattr(request, 'url') else '/unknown')
            method = request.method
            
            risk_score = 0
            
            # 大量データ取得の検出
            if "list" in endpoint.lower() or "search" in endpoint.lower():
                # クエリパラメータからページサイズを確認
                query_params = dict(request.query_params)
                page_size = query_params.get("page_size", "10")
                limit = query_params.get("limit", "10")
                
                try:
                    size = max(int(page_size), int(limit))
                    if size > 100:
                        risk_score += 30
                    elif size > 50:
                        risk_score += 20
                    elif size > 20:
                        risk_score += 10
                except (ValueError, TypeError):
                    pass
            
            # 機密データへのアクセス
            sensitive_endpoints = [
                "/api/users/password",
                "/api/users/email",
                "/api/security/",
                "/api/admin/"
            ]
            
            if any(ep in endpoint for ep in sensitive_endpoints):
                risk_score += 40
            
            # データエクスポート系のエンドポイント
            if any(keyword in endpoint.lower() for keyword in ["export", "download", "backup"]):
                risk_score += 25
            
            # 削除系の操作
            if method == "DELETE":
                risk_score += 35
            
            return RiskFactor(
                name=RiskFactorType.DATA_ACCESS_PATTERN,
                weight=self.risk_factors[RiskFactorType.DATA_ACCESS_PATTERN],
                score=min(risk_score, 100),
                details={
                    "endpoint": endpoint,
                    "method": method,
                    "query_params": dict(request.query_params),
                    "risk_factors": {
                        "large_data_request": risk_score > 0,
                        "sensitive_endpoint": any(ep in endpoint for ep in sensitive_endpoints),
                        "export_operation": any(keyword in endpoint.lower() for keyword in ["export", "download", "backup"]),
                        "delete_operation": method == "DELETE"
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"データアクセスパターンリスク計算でエラー: {e}")
            return RiskFactor(
                name=RiskFactorType.DATA_ACCESS_PATTERN,
                weight=self.risk_factors[RiskFactorType.DATA_ACCESS_PATTERN],
                score=0,
                details={"error": str(e)}
            )
    
    def _calculate_session_risk(self, session_id: str, request: Request) -> RiskFactor:
        """セッション異常のリスクを計算"""
        try:
            risk_score = 0
            
            # セッションの有効性チェック
            from app.core.security.session.manager import session_manager
            session_data = session_manager.validate_session(session_id)
            
            if not session_data:
                risk_score += 100  # 無効なセッション
            else:
                # セッションの経過時間チェック
                session_age = datetime.now(timezone.utc) - session_data.created_at
                if session_age.total_seconds() > 3600 * 24:  # 24時間以上
                    risk_score += 30
                elif session_age.total_seconds() > 3600 * 12:  # 12時間以上
                    risk_score += 20
                elif session_age.total_seconds() > 3600 * 6:   # 6時間以上
                    risk_score += 10
                
                # 最終アクティビティからの経過時間
                if hasattr(session_data, 'last_activity'):
                    inactivity_time = datetime.now(timezone.utc) - session_data.last_activity
                    if inactivity_time.total_seconds() > 3600 * 2:  # 2時間以上
                        risk_score += 25
                    elif inactivity_time.total_seconds() > 3600:    # 1時間以上
                        risk_score += 15
            
            # セッション固定攻撃の検出
            if session_id in self._get_suspicious_sessions():
                risk_score += 50
            
            return RiskFactor(
                name=RiskFactorType.SESSION_ANOMALY,
                weight=self.risk_factors[RiskFactorType.SESSION_ANOMALY],
                score=min(risk_score, 100),
                details={
                    "session_id": session_id,
                    "session_valid": session_data is not None,
                    "session_age_hours": session_age.total_seconds() / 3600 if 'session_age' in locals() else None,
                    "inactivity_hours": inactivity_time.total_seconds() / 3600 if 'inactivity_time' in locals() else None,
                    "suspicious_session": session_id in self._get_suspicious_sessions()
                }
            )
            
        except Exception as e:
            logger.error(f"セッション異常リスク計算でエラー: {e}")
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
        try:
            if not config.GEOIP_SERVICE_ENABLED:
                return 0.0
            
            # 簡易的なIP距離計算（実際の実装では地理情報サービスと連携）
            # 本番環境では MaxMind GeoIP2 や IP2Location 等のサービスを使用
            
            # 例: 同じIPアドレスブロック内なら距離0
            if ip1 == ip2:
                return 0.0
            
            # 例: 異なるIPアドレスブロックなら固定距離（実際は地理情報から計算）
            return 50.0  # 仮の値
            
        except Exception as e:
            logger.warning(f"地理的距離計算でエラー: {e}")
            return 0.0
    
    async def _get_user_timezone(self, session_id: str) -> Optional[str]:
        """ユーザーのタイムゾーンを取得"""
        try:
            # 実際の実装ではデータベースから取得
            # または、IPアドレスベースで推定
            
            # デフォルトは日本時間
            return "Asia/Tokyo"
            
        except Exception as e:
            logger.warning(f"タイムゾーン取得でエラー: {e}")
            return None
    
    def _get_timezone_object(self, timezone_str: str):
        """文字列からタイムゾーンオブジェクトを取得"""
        try:
            import zoneinfo
            return zoneinfo.ZoneInfo(timezone_str)
        except ImportError:
            # Python 3.8以前の場合
            try:
                import pytz
                return pytz.timezone(timezone_str)
            except ImportError:
                logger.warning("タイムゾーンライブラリが利用できません")
                return None
        except Exception as e:
            logger.warning(f"タイムゾーン変換でエラー: {e}")
            return None
    
    def _calculate_behavior_anomaly(self, pattern_data: Dict[str, Any], current_endpoint: str, current_method: str, current_ip: str) -> int:
        """行動パターンの異常度を計算"""
        try:
            if not pattern_data or "behaviors" not in pattern_data:
                return 0
            
            behaviors = pattern_data["behaviors"]
            if not behaviors:
                return 0
            
            # 過去の行動パターンから異常度を計算
            endpoint_anomaly = 0
            method_anomaly = 0
            ip_anomaly = 0
            
            # エンドポイントの異常度
            endpoint_counts = {}
            for behavior in behaviors:
                endpoint = behavior.get("endpoint", "")
                endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
            
            total_behaviors = len(behaviors)
            if total_behaviors > 0:
                current_endpoint_freq = endpoint_counts.get(current_endpoint, 0) / total_behaviors
                if current_endpoint_freq < 0.1:  # 10%未満の頻度
                    endpoint_anomaly = 40
                elif current_endpoint_freq < 0.3:  # 30%未満の頻度
                    endpoint_anomaly = 20
            
            # HTTPメソッドの異常度
            method_counts = {}
            for behavior in behaviors:
                method = behavior.get("method", "")
                method_counts[method] = method_counts.get(method, 0) + 1
            
            if total_behaviors > 0:
                current_method_freq = method_counts.get(current_method, 0) / total_behaviors
                if current_method_freq < 0.2:  # 20%未満の頻度
                    method_anomaly = 30
                elif current_method_freq < 0.5:  # 50%未満の頻度
                    method_anomaly = 15
            
            # IPアドレスの異常度
            ip_counts = {}
            for behavior in behaviors:
                ip = behavior.get("ip_address", "")
                ip_counts[ip] = ip_counts.get(ip, 0) + 1
            
            if total_behaviors > 0:
                current_ip_freq = ip_counts.get(current_ip, 0) / total_behaviors
                if current_ip_freq < 0.1:  # 10%未満の頻度
                    ip_anomaly = 50
                elif current_ip_freq < 0.3:  # 30%未満の頻度
                    ip_anomaly = 25
            
            # 総合異常度
            total_anomaly = endpoint_anomaly + method_anomaly + ip_anomaly
            return min(total_anomaly, 100)
            
        except Exception as e:
            logger.error(f"行動パターン異常度計算でエラー: {e}")
            return 0
    
    def _get_suspicious_sessions(self) -> List[str]:
        """疑わしいセッションのリストを取得"""
        try:
            # 過去1時間で異常なアクセスパターンを示したセッションを検出
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
            
            suspicious_sessions = self.db.query(RiskScore.session_id).filter(
                and_(
                    RiskScore.created_at >= cutoff_time,
                    RiskScore.risk_score > 70
                )
            ).distinct().all()
            
            return [session[0] for session in suspicious_sessions]
            
        except Exception as e:
            logger.error(f"疑わしいセッション取得でエラー: {e}")
            return []