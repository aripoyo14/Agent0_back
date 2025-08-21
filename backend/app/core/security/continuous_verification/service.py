# app/core/security/continuous_verification/service.py
"""
継続的検証サービスクラス
セッション監視、リスク評価、脅威検出の統合管理
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy.orm import Session
from fastapi import Request, HTTPException
from contextlib import asynccontextmanager

from .config import config
from .models import RiskScore, BehaviorPattern, ThreatDetection, RiskLevel, ThreatType
from .risk_engine import RiskEngine
from app.core.security.audit.service import AuditService
from app.core.security.audit.models import AuditEventType

# ロガーの設定
logger = logging.getLogger(__name__)

class ContinuousVerificationService:
    """継続的検証サービスクラス"""
    
    def __init__(self, db: Session):
        self.db = db
        self.config = config
        self.risk_engine = RiskEngine(db)
        self.audit_service = AuditService(db)
        
        # パフォーマンス最適化
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5分
        
        logger.info(f"継続的検証サービス初期化完了: {self.config}")
    
    async def monitor_session(
        self, 
        session_id: str, 
        request: Request,
        user_id: Optional[str] = None,
        user_type: Optional[str] = None
    ) -> bool:
        """セッションの継続的監視"""
        
        if not self.config.ENABLED:
            logger.info("継続的検証が無効化されています")
            return True
        
        try:
            # 同期的な監視処理（制御機能を有効化）
            if not self.config.MONITORING_ONLY:
                logger.info(f"制御モードでセッション監視: session={session_id}")
                return await self._synchronous_monitoring(session_id, request, user_id, user_type)
            
            # 非同期で監視処理を実行（監視のみモード）
            else:
                logger.info(f"監視モードでセッション監視: session={session_id}")
                asyncio.create_task(
                    self._background_monitoring(session_id, request, user_id, user_type)
                )
                return True  # 即座にアクセス許可
                
        except Exception as e:
            logger.error(f"セッション監視でエラー: {e}")
            # エラー時は設定に応じて制御
            if self.config.FAILSAFE_MODE:
                logger.warning("フェイルセーフモード：エラー時はアクセス許可")
                return True  # フェイルセーフ時はアクセス許可
            else:
                logger.error("本番モード：エラー時はアクセス拒否")
                return False  # 本番環境ではアクセス拒否
    
    async def _background_monitoring(
        self, 
        session_id: str, 
        request: Request,
        user_id: Optional[str] = None,
        user_type: Optional[str] = None
    ):
        """バックグラウンドでの監視処理"""
        try:
            # リスクスコアの計算
            risk_score, risk_factors = await self.risk_engine.calculate_risk(
                session_id, request, user_id, user_type
            )
            
            # リスクスコアの記録
            await self._record_risk_score(session_id, risk_score, risk_factors, request)
            
            # 脅威検出
            if self.config.THREAT_DETECTION_ENABLED:
                await self._detect_threats(session_id, risk_score, risk_factors, request)
            
            # 行動パターンの更新
            if self.config.BEHAVIOR_LEARNING_ENABLED and user_id:
                await self._update_behavior_pattern(user_id, request, risk_factors)
            
            # 高リスク時の対応
            if risk_score > self.config.EXTREME_RISK_THRESHOLD:
                await self._handle_extreme_risk(session_id, risk_score, request)
            
        except Exception as e:
            logger.error(f"バックグラウンド監視でエラー: {e}")
            # 監視処理のエラーはメイン処理に影響しない
    
    async def _synchronous_monitoring(
        self, 
        session_id: str, 
        request: Request,
        user_id: Optional[str] = None,
        user_type: Optional[str] = None
    ) -> bool:
        """同期的な監視処理（制御機能付き）"""
        try:
            logger.info(f"セッション監視開始: session={session_id}, user={user_id}")
            
            # リスクスコアの計算
            risk_score, risk_factors = await self.risk_engine.calculate_risk(
                session_id, request, user_id, user_type
            )
            
            # リスクスコアの記録
            await self._record_risk_score(session_id, risk_score, risk_factors, request)
            
            # 段階的な制御を実装
            if risk_score > self.config.EXTREME_RISK_THRESHOLD:
                logger.warning(f"極高リスク検出: session={session_id}, score={risk_score}")
                await self._handle_extreme_risk(session_id, risk_score, request)
                return False  # アクセス拒否
            
            elif risk_score > self.config.HIGH_RISK_THRESHOLD:
                logger.warning(f"高リスク検出: session={session_id}, score={risk_score}")
                await self._handle_high_risk(session_id, risk_score, request)
                # 追加認証を要求
                return await self._require_additional_verification(session_id, request)
            
            elif risk_score > self.config.MEDIUM_RISK_THRESHOLD:
                logger.info(f"中リスク検出: session={session_id}, score={risk_score}")
                # 監視強化
                await self._enhance_monitoring(session_id, risk_score, request)
            
            logger.info(f"セッション監視完了: session={session_id}, score={risk_score}, access=ALLOWED")
            return True
            
        except Exception as e:
            logger.error(f"同期的監視でエラー: {e}")
            # エラー時は設定に応じて制御
            if self.config.FAILSAFE_MODE:
                logger.warning("フェイルセーフモード：エラー時はアクセス許可")
                return True  # フェイルセーフ時はアクセス許可
            else:
                logger.error("本番モード：エラー時はアクセス拒否")
                return False  # 本番環境ではアクセス拒否
    
    async def _record_risk_score(
        self, 
        session_id: str, 
        risk_score: int, 
        risk_factors: List[Any], 
        request: Request
    ):
        """リスクスコアを記録"""
        try:
            risk_level = RiskLevel.from_score(risk_score)
            
            risk_record = RiskScore(
                session_id=session_id,
                risk_score=risk_score,
                risk_level=risk_level.value,
                factors=[factor.__dict__ for factor in risk_factors] if risk_factors and hasattr(risk_factors[0], '__dict__') else risk_factors,
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("user-agent"),
                endpoint=str(request.url.path),
                http_method=request.method
            )
            
            self.db.add(risk_record)
            self.db.commit()
            
            logger.debug(f"リスクスコア記録完了: session={session_id}, score={risk_score}, level={risk_level.value}")
            
        except Exception as e:
            logger.error(f"リスクスコア記録でエラー: {e}")
            self.db.rollback()
    
    async def _detect_threats(
        self, 
        session_id: str, 
        risk_score: int, 
        risk_factors: List[Any], 
        request: Request
    ):
        """脅威を検出"""
        try:
            threats = []
            
            # リスクスコアに基づく脅威検出
            if risk_score > self.config.HIGH_RISK_THRESHOLD:
                threats.append(ThreatType.SUSPICIOUS_ACTIVITY)
            
            # 特定のリスク要因に基づく脅威検出
            for factor in risk_factors:
                if hasattr(factor, 'score') and factor.score > 80:
                    if 'location' in factor.name.lower():
                        threats.append(ThreatType.LOCATION_ANOMALY)
                    elif 'time' in factor.name.lower():
                        threats.append(ThreatType.TIME_ANOMALY)
                    elif 'behavior' in factor.name.lower():
                        threats.append(ThreatType.UNUSUAL_BEHAVIOR)
            
            # 脅威記録
            for threat_type in threats:
                threat_record = ThreatDetection(
                    session_id=session_id,
                    threat_type=threat_type.value,
                    threat_level=RiskLevel.from_score(risk_score).value,
                    details={
                        "risk_score": risk_score,
                        "risk_factors": [f.name for f in risk_factors] if risk_factors and hasattr(risk_factors[0], 'name') else [],
                        "endpoint": str(request.url.path),
                        "http_method": request.method
                    },
                    risk_score_at_detection=risk_score
                )
                
                self.db.add(threat_record)
            
            self.db.commit()
            
            if threats:
                logger.warning(f"脅威検出: session={session_id}, threats={threats}, score={risk_score}")
            
        except Exception as e:
            logger.error(f"脅威検出でエラー: {e}")
            self.db.rollback()
    
    async def _update_behavior_pattern(
        self, 
        user_id: str, 
        request: Request, 
        risk_factors: List[Any]
    ):
        """行動パターンを更新"""
        try:
            # 既存のパターンを取得
            existing_pattern = self.db.query(BehaviorPattern).filter(
                BehaviorPattern.user_id == user_id
            ).first()
            
            # 新しい行動データ
            new_behavior = {
                "endpoint": str(request.url.path),
                "method": request.method,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "risk_score": sum(f.score for f in risk_factors) / len(risk_factors) if risk_factors else 0,
                "ip_address": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent")
            }
            
            if existing_pattern:
                # 既存パターンを更新
                pattern_data = existing_pattern.pattern_data
                if "behaviors" not in pattern_data:
                    pattern_data["behaviors"] = []
                
                pattern_data["behaviors"].append(new_behavior)
                
                # 古いデータを削除（最新100件のみ保持）
                if len(pattern_data["behaviors"]) > 100:
                    pattern_data["behaviors"] = pattern_data["behaviors"][-100:]
                
                existing_pattern.pattern_data = pattern_data
                existing_pattern.last_updated = datetime.now(timezone.utc)
                existing_pattern.sample_count += 1
                
                # 信頼度スコアの更新
                existing_pattern.confidence_score = min(
                    existing_pattern.confidence_score + 1, 100
                )
            else:
                # 新しいパターンを作成
                new_pattern = BehaviorPattern(
                    user_id=user_id,
                    pattern_data={"behaviors": [new_behavior]},
                    confidence_score=1,
                    sample_count=1
                )
                self.db.add(new_pattern)
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"行動パターン更新でエラー: {e}")
            self.db.rollback()
    
    async def _handle_extreme_risk(
        self, 
        session_id: str, 
        risk_score: int, 
        request: Request
    ):
        """極めて高いリスクへの対応"""
        try:
            # セッション無効化
            await self._invalidate_session(session_id)
            
            # セキュリティアラート
            await self._send_security_alert(session_id, risk_score, request)
            
            # 監査ログ記録
            await self._log_security_event(session_id, risk_score, request)
            
            logger.critical(f"極めて高いリスク検出: session={session_id}, score={risk_score}")
            
        except Exception as e:
            logger.error(f"高リスク対応でエラー: {e}")
    
    async def _invalidate_session(self, session_id: str):
        """セッションを無効化"""
        try:
            # 既存のセッション管理と連携
            from app.core.security.session.manager import session_manager
            session_manager.invalidate_session(session_id)
            
        except Exception as e:
            logger.error(f"セッション無効化でエラー: {e}")
    
    async def _send_security_alert(self, session_id: str, risk_score: int, request: Request):
        """セキュリティアラートを送信"""
        try:
            # 実装例（メール、Slack、SMS等）
            alert_data = {
                "session_id": session_id,
                "risk_score": risk_score,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "endpoint": str(request.url.path),
                "ip_address": self._get_client_ip(request)
            }
            
            logger.warning(f"セキュリティアラート: {alert_data}")
            
        except Exception as e:
            logger.error(f"セキュリティアラート送信でエラー: {e}")
    
    async def _log_security_event(self, session_id: str, risk_score: int, request: Request):
        """セキュリティイベントを監査ログに記録"""
        try:
            await self.audit_service.log_event(
                event_type=AuditEventType.SECURITY_ALERT,
                resource="session",
                action="high_risk_detected",
                success=False,
                details={
                    "session_id": session_id,
                    "risk_score": risk_score,
                    "endpoint": str(request.url.path),
                    "ip_address": self._get_client_ip(request)
                }
            )
            
        except Exception as e:
            logger.error(f"セキュリティイベント記録でエラー: {e}")
    
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
    
    @asynccontextmanager
    async def get_session_monitor(self, session_id: str):
        """セッション監視のコンテキストマネージャー"""
        try:
            yield self
        finally:
            # クリーンアップ処理
            await self._cleanup_session_data(session_id)
    
    async def _cleanup_session_data(self, session_id: str):
        """セッションデータのクリーンアップ"""
        try:
            # 古いリスクスコアを削除
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.config.MAX_SESSION_AGE_HOURS)
            
            self.db.query(RiskScore).filter(
                RiskScore.session_id == session_id,
                RiskScore.timestamp < cutoff_time
            ).delete()
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"セッションデータクリーンアップでエラー: {e}")
            self.db.rollback()

    async def _handle_high_risk(
        self, 
        session_id: str, 
        risk_score: int, 
        request: Request
    ):
        """高リスク時の対応"""
        try:
            # 脅威検出レコードを作成
            threat_record = ThreatDetection(
                session_id=session_id,
                threat_type=ThreatType.SUSPICIOUS_ACTIVITY.value,
                threat_level=RiskLevel.HIGH.value,
                details={
                    "risk_score": risk_score,
                    "action": "additional_verification_required",
                    "endpoint": str(request.url.path),
                    "http_method": request.method,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                risk_score_at_detection=risk_score,
                mitigated=False,
                mitigation_action="additional_verification_required"
            )
            
            self.db.add(threat_record)
            self.db.commit()
            
            logger.warning(f"高リスク対応完了: session={session_id}, action=additional_verification_required")
            
        except Exception as e:
            logger.error(f"高リスク対応でエラー: {e}")
            self.db.rollback()
    
    async def _require_additional_verification(self, session_id: str, request: Request) -> bool:
        """追加認証の要求"""
        try:
            logger.info(f"追加認証要求: session={session_id}")
            
            # 現在は簡易実装：追加認証が必要なためアクセス拒否
            # 実際の実装では、追加の認証フローを実装
            return False
            
        except Exception as e:
            logger.error(f"追加認証要求でエラー: {e}")
            return False
    
    async def _enhance_monitoring(self, session_id: str, risk_score: int, request: Request):
        """監視強化"""
        try:
            logger.info(f"監視強化: session={session_id}, score={risk_score}")
            
            # 監視レベルを上げる（ログの詳細化、頻度の向上など）
            # 現在はログ出力のみ
            
        except Exception as e:
            logger.error(f"監視強化でエラー: {e}")
