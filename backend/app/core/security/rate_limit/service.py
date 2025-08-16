"""
レート制限サービスクラス
レート制限のビジネスロジックを管理
"""

import time
from typing import Dict, Optional, List
from collections import defaultdict, deque
from datetime import datetime, timedelta
from fastapi import Request

from .models import RateLimitRule, RateLimitViolation, RateLimitStatus, RateLimitStats, RateLimitType
from .config import RateLimitConfig

class RateLimitService:
    """レート制限のビジネスロジックを提供するサービス層"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        
        print(f"🔧 レート制限サービス初期化: {self.config}")  # デバッグログ
        print(f"🔧 認証ログイン設定: {self.config.auth_login_max_requests}/{self.config.auth_login_window_seconds}")  # デバッグログ
        
        # リクエスト履歴の管理
        self.ip_requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.endpoint_requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.user_requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.global_requests: Dict[str, deque] = defaultdict(lambda: deque())
        
        # 違反記録の管理
        self.violations: List[RateLimitViolation] = []
        
        # 統計情報
        self.stats = RateLimitStats(
            total_requests=0,
            blocked_requests=0,
            violations_count=0,
            active_identifiers=0
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """クライアントのIPアドレスを取得"""
        try:
            # プロキシ経由の場合の対応
            forwarded_for = request.headers.get("x-forwarded-for")
            if forwarded_for:
                # ポート番号を除去してIPアドレスのみを取得
                ip_with_port = forwarded_for.split(",")[0].strip()
                return ip_with_port.split(":")[0]  # ポート番号を除去
            
            real_ip = request.headers.get("x-real-ip")
            if real_ip:
                # ポート番号を除去してIPアドレスのみを取得
                return real_ip.split(":")[0]
            
            # request.client.hostからポート番号を除去
            if request.client:
                client_host = request.client.host
                return client_host.split(":")[0]  # ポート番号を除去
            
            return "unknown"
        except Exception:
            return "unknown"
    
    def _get_user_id_from_token(self, request: Request) -> Optional[str]:
        """JWTトークンからユーザーIDを取得"""
        try:
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            token = auth_header.split(" ")[1]
            # 簡易的なJWTデコード（実際の実装では適切な検証が必要）
            import jwt
            from app.core.config import settings
            
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            return payload.get("sub")
        except Exception:
            return None
    
    def _cleanup_old_requests(self, requests_deque: deque, window_seconds: int):
        """古いリクエストを削除"""
        current_time = time.time()
        while requests_deque and current_time - requests_deque[0] > window_seconds:
            requests_deque.popleft()
    
    def check_rate_limit(
        self,
        request: Request,
        rule: RateLimitRule,
        custom_identifier: Optional[str] = None
    ) -> tuple[bool, Optional[RateLimitViolation]]:
        """レート制限をチェック"""
        
        print(f" レート制限チェック開始: {rule.name}")  # デバッグログ
        
        if not self.config.enabled or not rule.enabled:
            print(f"⚠️  レート制限が無効: enabled={self.config.enabled}, rule.enabled={rule.enabled}")  # デバッグログ
            return True, None
        
        # 識別子を決定
        identifier = custom_identifier or self._get_identifier(request, rule.request_type)
        print(f" 識別子: {identifier}, タイプ: {rule.request_type}")  # デバッグログ
        
        # 適切なリクエスト履歴を選択
        requests_deque = self._get_requests_deque(rule.request_type, identifier)
        
        # 古いリクエストを削除
        self._cleanup_old_requests(requests_deque, rule.window_seconds)
        
        # 制限チェック
        current_count = len(requests_deque)
        is_allowed = current_count < rule.max_requests
        
        print(f"📊 現在のカウント: {current_count}/{rule.max_requests}, 許可: {is_allowed}")  # デバッグログ
        
        if is_allowed:
            # リクエストを記録
            requests_deque.append(time.time())
            print(f"✅ リクエスト記録: {len(requests_deque)}")  # デバッグログ
        else:
            # 違反を記録
            violation = RateLimitViolation(
                timestamp=datetime.utcnow(),
                identifier=identifier,
                request_type=rule.request_type,
                rule_name=rule.name,
                current_count=current_count,
                max_allowed=rule.max_requests,
                window_seconds=rule.window_seconds,
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("user-agent"),
                endpoint=str(request.url.path),
                user_id=self._get_user_id_from_token(request)
            )
            self.violations.append(violation)
            print(f"🚫 レート制限違反記録: {violation}")  # デバッグログ
        
        return is_allowed, None if is_allowed else violation
    
    def _get_identifier(self, request: Request, request_type: RateLimitType) -> str:
        """リクエストタイプに基づいて識別子を取得"""
        if request_type == RateLimitType.IP:
            return self._get_client_ip(request)
        elif request_type == RateLimitType.ENDPOINT:
            return f"{request.method}:{request.url.path}"
        elif request_type == RateLimitType.USER:
            user_id = self._get_user_id_from_token(request)
            return user_id or self._get_client_ip(request)
        elif request_type == RateLimitType.GLOBAL:
            return self._get_client_ip(request)
        else:
            return "unknown"
    
    def _get_requests_deque(self, request_type: RateLimitType, identifier: str) -> deque:
        """リクエストタイプに基づいて適切なdequeを取得"""
        if request_type == RateLimitType.IP:
            return self.ip_requests[identifier]
        elif request_type == RateLimitType.ENDPOINT:
            return self.endpoint_requests[identifier]
        elif request_type == RateLimitType.USER:
            return self.user_requests[identifier]
        elif request_type == RateLimitType.GLOBAL:
            return self.global_requests[identifier]
        else:
            return deque()
    
    def get_rate_limit_status(
        self,
        request: Request,
        rule: RateLimitRule,
        custom_identifier: Optional[str] = None
    ) -> RateLimitStatus:
        """レート制限の現在の状況を取得"""
        identifier = custom_identifier or self._get_identifier(request, rule.request_type)
        requests_deque = self._get_requests_deque(rule.request_type, identifier)
        
        # 古いリクエストを削除
        self._cleanup_old_requests(requests_deque, rule.window_seconds)
        
        current_count = len(requests_deque)
        remaining_requests = max(0, rule.max_requests - current_count)
        
        # リセット時刻を計算
        if requests_deque:
            oldest_request = requests_deque[0]
            reset_time = datetime.fromtimestamp(oldest_request + rule.window_seconds)
        else:
            reset_time = datetime.utcnow()
        
        return RateLimitStatus(
            identifier=identifier,
            request_type=rule.request_type,
            current_count=current_count,
            max_allowed=rule.max_requests,
            remaining_requests=remaining_requests,
            window_seconds=rule.window_seconds,
            reset_time=reset_time,
            is_blocked=current_count >= rule.max_requests
        )
    
    def get_stats(self) -> RateLimitStats:
        """統計情報を取得"""
        # アクティブな識別子数を計算
        active_identifiers = (
            len(self.ip_requests) + 
            len(self.endpoint_requests) + 
            len(self.user_requests) + 
            len(self.global_requests)
        )
        
        # 最後の違反時刻を取得
        last_violation = None
        if self.violations:
            last_violation = max(violation.timestamp for violation in self.violations)
        
        return RateLimitStats(
            total_requests=self.stats.total_requests,
            blocked_requests=self.stats.blocked_requests,
            violations_count=self.stats.violations_count,
            active_identifiers=active_identifiers,
            last_violation=last_violation
        )
    
    def reset_limits(self):
        """すべてのレート制限をリセット（テスト用）"""
        self.ip_requests.clear()
        self.endpoint_requests.clear()
        self.user_requests.clear()
        self.global_requests.clear()
        self.violations.clear()
        self.stats = RateLimitStats(
            total_requests=0,
            blocked_requests=0,
            violations_count=0,
            active_identifiers=0
        )
    
    def cleanup_old_data(self, max_age_hours: int = 24):
        """古いデータをクリーンアップ"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        # 古いリクエスト履歴を削除
        for requests_dict in [self.ip_requests, self.endpoint_requests, self.user_requests, self.global_requests]:
            for identifier in list(requests_dict.keys()):
                requests_deque = requests_dict[identifier]
                self._cleanup_old_requests(requests_deque, max_age_hours * 3600)
                if not requests_deque:
                    del requests_dict[identifier]
        
        # 古い違反記録を削除
        self.violations = [
            v for v in self.violations 
            if v.timestamp.timestamp() > cutoff_time
        ]

# グローバルなレート制限サービスインスタンス
rate_limit_service = RateLimitService()
