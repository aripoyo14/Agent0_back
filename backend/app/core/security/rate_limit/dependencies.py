"""
レート制限の依存性注入
"""

from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from .service import rate_limit_service
from .models import RateLimitRule, RateLimitType
from .config import default_config


"""認証ログインのレート制限チェック"""
def check_auth_login_rate_limit(request: Request):
    
    print(f"🔍 レート制限依存性: チェック開始")
    
    # レート制限ルールを作成
    rule = RateLimitRule(
        name="auth_login",
        max_requests=default_config.auth_login_max_requests,
        window_seconds=default_config.auth_login_window_seconds,
        request_type=RateLimitType.IP,
        error_message=default_config.error_messages["auth_login"]
    )
    
    # レート制限チェック
    is_allowed, violation = rate_limit_service.check_rate_limit(request, rule)
    
    if not is_allowed:
        print(f"🚫 レート制限違反: {violation}")
        # レート制限ヘッダーを設定
        headers = {
            "X-RateLimit-Limit": str(rule.max_requests),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(violation.timestamp.timestamp() + rule.window_seconds)),
            "Retry-After": str(rule.window_seconds)
        }
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=rule.error_message,
            headers=headers
        )
    
    print(f"✅ レート制限チェック通過")
    return True

"""ユーザー登録のレート制限チェック"""
def check_user_register_rate_limit(request: Request):
    
    print(f"�� ユーザー登録レート制限依存性: チェック開始")
    
    # レート制限ルールを作成
    rule = RateLimitRule(
        name="user_register",
        max_requests=default_config.user_register_max_requests,
        window_seconds=default_config.user_register_window_seconds,
        request_type=RateLimitType.IP,
        error_message=default_config.error_messages["user_register"]
    )
    
    # レート制限チェック
    is_allowed, violation = rate_limit_service.check_rate_limit(request, rule)
    
    if not is_allowed:
        print(f"🚫 ユーザー登録レート制限違反: {violation}")
        # レート制限ヘッダーを設定
        headers = {
            "X-RateLimit-Limit": str(rule.max_requests),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(violation.timestamp.timestamp() + rule.window_seconds)),
            "Retry-After": str(rule.window_seconds)
        }
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=rule.error_message,
            headers=headers
        )
    
    print(f"✅ ユーザー登録レート制限チェック通過")
    return True

"""エキスパート登録のレート制限チェック"""
def check_expert_register_rate_limit(request: Request):
        
    print(f"�� エキスパート登録レート制限依存性: チェック開始")
    
    # レート制限ルールを作成
    rule = RateLimitRule(
        name="expert_register",
        max_requests=default_config.user_register_max_requests,  # 同じ設定を使用
        window_seconds=default_config.user_register_window_seconds,
        request_type=RateLimitType.IP,
        error_message=default_config.error_messages["user_register"]  # 同じメッセージを使用
    )
    
    # レート制限チェック
    is_allowed, violation = rate_limit_service.check_rate_limit(request, rule)
    
    if not is_allowed:
        print(f"�� エキスパート登録レート制限違反: {violation}")
        # レート制限ヘッダーを設定
        headers = {
            "X-RateLimit-Limit": str(rule.max_requests),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(violation.timestamp.timestamp() + rule.window_seconds)),
            "Retry-After": str(rule.window_seconds)
        }
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=rule.error_message,
            headers=headers
        )
    
    print(f"✅ エキスパート登録レート制限チェック通過")
    return True