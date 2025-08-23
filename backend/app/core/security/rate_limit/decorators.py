"""
レート制限デコレータ
FastAPIエンドポイントにレート制限を適用するためのデコレータ
"""

import functools
import logging
from typing import Optional, Union
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

from .service import rate_limit_service
from .models import RateLimitRule, RateLimitType
from .config import default_config

# ロガーの設定
logger = logging.getLogger(__name__)

def rate_limit(
    max_requests: int,
    window_seconds: int,
    request_type: RateLimitType = RateLimitType.IP,
    rule_name: Optional[str] = None,
    error_message: Optional[str] = None,
    custom_identifier: Optional[str] = None
):
    """
    汎用レート制限デコレータ
    
    Args:
        max_requests: 時間枠内での最大リクエスト数
        window_seconds: 時間枠（秒）
        request_type: 制限タイプ
        rule_name: ルール名（監査ログ用）
        error_message: カスタムエラーメッセージ
        custom_identifier: カスタム識別子
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # リクエストオブジェクトを取得（修正版）
            request = None
            
            # kwargsからRequestオブジェクトを探す
            for key, value in kwargs.items():
                if isinstance(value, Request):
                    request = value
                    break
            
            # kwargsで見つからない場合、argsから探す
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            # リクエストオブジェクトが見つからない場合
            if not request:
                logger.warning(f"レート制限デコレータ: Requestオブジェクトが見つかりません")
                logger.warning(f" args: {args}")
                logger.warning(f" kwargs: {kwargs}")
                return await func(*args, **kwargs)
            
            logger.debug(f"レート制限デコレータ: Requestオブジェクトを発見")
            
            # ルール名を決定
            rule_name_final = rule_name or f"{func.__name__}_{request_type.value}"
            
            # エラーメッセージを決定
            error_message_final = error_message or default_config.error_messages.get(
                request_type.value, 
                "レート制限に達しました。しばらく待ってから再試行してください。"
            )
            
            # レート制限ルールを作成
            rule = RateLimitRule(
                name=rule_name_final,
                max_requests=max_requests,
                window_seconds=window_seconds,
                request_type=request_type,
                error_message=error_message_final
            )
            
            # レート制限チェック
            is_allowed, violation = rate_limit_service.check_rate_limit(
                request, rule, custom_identifier
            )
            
            if not is_allowed:
                # レート制限ヘッダーを設定
                headers = {
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(violation.timestamp.timestamp() + window_seconds)),
                    "Retry-After": str(window_seconds)
                }
                
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": error_message_final,
                        "retry_after_seconds": window_seconds,
                        "rule_name": rule_name_final
                    },
                    headers=headers
                )
            
            # レート制限状況を取得
            status_info = rate_limit_service.get_rate_limit_status(request, rule, custom_identifier)
            
            # レート制限ヘッダーを設定
            headers = {
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": str(status_info.remaining_requests),
                "X-RateLimit-Reset": str(int(status_info.reset_time.timestamp()))
            }
            
            # 元の関数を実行
            response = await func(*args, **kwargs)

            # より詳細なデバッグ情報を追加
            logger.debug(f"レスポンスオブジェクト詳細:")
            logger.debug(f"  型: {type(response)}")
            logger.debug(f"  属性: {dir(response)}")
            logger.debug(f"  ヘッダー属性: {hasattr(response, 'headers')}")
            logger.debug(f"  ボディ属性: {hasattr(response, 'body')}")
            logger.debug(f"  ステータスコード属性: {hasattr(response, 'status_code')}")
            
            # レスポンスにヘッダーを追加（確実な方法）
            try:
                logger.debug(f"レスポンスヘッダー設定開始:")
                logger.debug(f"  ヘッダー内容: {headers}")
                
                # 常に新しいレスポンスを作成してヘッダーを設定
                if isinstance(response, dict):
                    logger.debug(f"辞書レスポンス、JSONResponseで再作成")
                    new_response = JSONResponse(
                        status_code=200,
                        content=response,
                        headers=headers
                    )
                    logger.debug(f"  新しいレスポンス作成完了: {type(new_response)}")
                    return new_response
                elif hasattr(response, 'body') and hasattr(response, 'status_code'):
                    logger.debug(f"既存レスポンス、JSONResponseで再作成")
                    return JSONResponse(
                        status_code=response.status_code,
                        content=response.body,
                        headers=headers
                    )
                else:
                    logger.warning(f"特殊なレスポンス、JSONResponseで再作成")
                    return JSONResponse(
                        status_code=200,
                        content=response,
                        headers=headers
                    )
            except Exception as e:
                logger.error(f"レスポンスヘッダー設定エラー: {e}")
                # エラーが発生した場合は元のレスポンスを返す
                return response
        
        return wrapper
    return decorator

def rate_limit_ip(
    max_requests: int,
    window_seconds: int,
    rule_name: Optional[str] = None,
    error_message: Optional[str] = None
):
    """IPベースのレート制限デコレータ"""
    return rate_limit(
        max_requests=max_requests,
        window_seconds=window_seconds,
        request_type=RateLimitType.IP,
        rule_name=rule_name,
        error_message=error_message
    )

def rate_limit_endpoint(
    max_requests: int,
    window_seconds: int,
    rule_name: Optional[str] = None,
    error_message: Optional[str] = None
):
    """エンドポイントベースのレート制限デコレータ"""
    return rate_limit(
        max_requests=max_requests,
        window_seconds=window_seconds,
        request_type=RateLimitType.ENDPOINT,
        rule_name=rule_name,
        error_message=error_message
    )

def rate_limit_user(
    max_requests: int,
    window_seconds: int,
    rule_name: Optional[str] = None,
    error_message: Optional[str] = None
):
    """ユーザーベースのレート制限デコレータ"""
    return rate_limit(
        max_requests=max_requests,
        window_seconds=window_seconds,
        request_type=RateLimitType.USER,
        rule_name=rule_name,
        error_message=error_message
    )

# プリセットデコレータ（よく使う設定）
def rate_limit_auth_login():
    """認証ログイン用のレート制限（1分間に5回まで）"""
    return rate_limit_ip(
        max_requests=default_config.auth_login_max_requests,
        window_seconds=default_config.auth_login_window_seconds,
        rule_name="auth_login",
        error_message=default_config.error_messages["auth_login"]
    )

def rate_limit_user_register():
    """ユーザー登録用のレート制限（1時間に3回まで）"""
    return rate_limit_ip(
        max_requests=default_config.user_register_max_requests,
        window_seconds=default_config.user_register_window_seconds,
        rule_name="user_register",
        error_message=default_config.error_messages["user_register"]
    )

def rate_limit_file_upload():
    """ファイルアップロード用のレート制限（1分間に10回まで）"""
    return rate_limit_ip(
        max_requests=default_config.file_upload_max_requests,
        window_seconds=default_config.file_upload_window_seconds,
        rule_name="file_upload",
        error_message=default_config.error_messages["file_upload"]
    )

def rate_limit_comment_post():
    """コメント投稿用のレート制限（1分間に20回まで）"""
    return rate_limit_ip(
        max_requests=default_config.comment_post_max_requests,
        window_seconds=default_config.comment_post_window_seconds,
        rule_name="comment_post",
        error_message=default_config.error_messages["comment_post"]
    )

def rate_limit_read_api():
    """読み取りAPI用のレート制限（1分間に100回まで）"""
    return rate_limit_ip(
        max_requests=default_config.read_api_max_requests,
        window_seconds=default_config.read_api_window_seconds,
        rule_name="read_api",
        error_message=default_config.error_messages["read_api"]
    )

# 修正版：デコレータを直接返す
def rate_limit_read_api(func):
    """読み取りAPI用のレート制限（1分間に100回まで）"""
    return rate_limit(
        max_requests=default_config.read_api_max_requests,
        window_seconds=default_config.read_api_window_seconds,
        request_type=RateLimitType.IP,
        rule_name="read_api",
        error_message=default_config.error_messages["read_api"]
    )(func)
