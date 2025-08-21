"""
監査ログ用デコレーター
エンドポイントで簡単に監査ログを記録
"""
from functools import wraps
from typing import Optional, Callable, Dict, Any
from app.core.security.audit.service import AuditService
from app.core.security.audit.models import AuditEventType
from app.core.dependencies import get_db
from sqlalchemy.orm import Session
from fastapi import Request


def audit_log(
    event_type: AuditEventType,
    resource: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    user_type: Optional[str] = None
):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # デバッグ出力を削除し、適切なログに変更
            import logging
            logger = logging.getLogger(__name__)
            
            # リクエストオブジェクトを取得（複数の方法を試行）
            request = None
            
            # 1. kwargsからhttp_requestを取得（面談APIで使用されている名前）
            if 'http_request' in kwargs:
                request = kwargs['http_request']
                # print(f"🔍 kwargsからhttp_requestを取得: {type(request)}")
            
            # 2. argsからRequest型のオブジェクトを取得
            if not request:
                for arg in args: 
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            # 3. kwargsからRequest型のオブジェクトを取得
            if not request:
                for key, value in kwargs.items():
                    # print(f"🔍 kwargs[{key}]: {type(value).__name__} = {value}")
                    if isinstance(value, Request):
                        request = value
                        # print(f"🔍 kwargsからRequest型を取得: {key} -> {type(value)}")
                        break
                        
            # データベースセッションを取得（より確実な方法）
            db = None
            # 1. kwargsから取得を試行
            if 'db' in kwargs:
                db = kwargs['db']
            # 2. argsから取得を試行（Dependsで注入された場合）
            else:
                for arg in args:
                    if hasattr(arg, 'execute') and hasattr(arg, 'commit'):
                        db = arg
                        break
            
            # ユーザー情報を抽出（より確実な方法）
            current_user = None
            extracted_user_id = user_id
            extracted_user_type = user_type
            
            # 1. kwargsから取得を試行
            if 'current_user' in kwargs:
                current_user = kwargs['current_user']
            # 2. argsから取得を試行
            else:
                for arg in args:
                    if hasattr(arg, 'id') or (isinstance(arg, dict) and 'user_id' in arg):
                        current_user = arg
                        break
            
            # ユーザー情報を設定
            if current_user:
                if hasattr(current_user, 'id'):
                    extracted_user_id = str(current_user.id)
                elif isinstance(current_user, dict) and 'user_id' in current_user:
                    extracted_user_id = str(current_user['user_id'])
                
                # user_typeの取得を改善
                if hasattr(current_user, 'role'):
                    extracted_user_type = current_user.role
                elif hasattr(current_user, 'user_type'):
                    extracted_user_type = current_user.user_type
                elif isinstance(current_user, dict) and 'role' in current_user:
                    extracted_user_type = current_user['role']
                elif isinstance(current_user, dict) and 'user_type' in current_user:
                    extracted_user_type = current_user['user_type']
                
                # デバッグ用のログを追加
                # print(f"🔍 ユーザー情報抽出: ID={extracted_user_id}, Type={extracted_user_type}")
            
            try:
                # 関数を実行
                # print(f"🔍 関数実行開始: {func.__name__}")
                result = await func(*args, **kwargs)
                # print(f"🔍 関数実行完了: {func.__name__}")
                
                # 成功時の監査ログ（dbが利用可能な場合のみ）
                if db:
                    try:
                        # print(f"🔍 監査ログ記録開始")
                        audit_service = AuditService(db)
                                                
                        await audit_service.log_event(
                            event_type=event_type,
                            resource=resource,
                            action=action,
                            user_id=extracted_user_id,
                            user_type=extracted_user_type,
                            success=True,
                            request=request,
                            details={"result": "success"}
                        )
                        logger.debug(f"✅ 監査ログ記録完了: {event_type} - {resource} - {action}")
                    except Exception as audit_error:
                        logger.debug(f"⚠️ 監査ログ記録でエラー: {audit_error}")
                        import traceback
                        traceback.print_exc()
                        # 監査ログのエラーは本処理を妨げない
                else:
                    logger.debug(f"⚠️ データベースセッションが見つかりません: {event_type}")
                
                return result
            except Exception as e:
                logger.debug(f"❌ 関数実行でエラー: {e}")
                # エラー時の監査ログ
                if db:
                    try:
                        audit_service = AuditService(db)
                        await audit_service.log_event(
                            event_type=event_type,
                            resource=resource,
                            action=action,
                            user_id=extracted_user_id,
                            user_type=extracted_user_type,
                            success=False,
                            request=request,
                            details={"error": str(e)}
                        )
                        # print(f"✅ エラー時の監査ログ記録完了: {event_type}")
                    except Exception as audit_error:
                        logger.debug(f"⚠️ エラー時の監査ログ記録でエラー: {audit_error}")
                
                raise e
        return wrapper
    return decorator


def audit_log_sync(
    event_type: AuditEventType,
    resource: Optional[str] = None,
    action: Optional[str] = None
):
    """
    同期関数用の監査ログデコレーター
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # リクエストオブジェクトをkwargsから取得
            request = kwargs.get('http_request')
            
            # データベースセッションを取得
            db = None
            for arg in args:
                if hasattr(arg, 'execute'):  # Sessionオブジェクトの可能性
                    db = arg
                    break
            
            # ユーザー情報を抽出
            current_user = None
            for arg in args:
                if hasattr(arg, 'id') and hasattr(arg, 'role'):  # Userオブジェクトの可能性
                    current_user = arg
                    break
            
            try:
                # 関数を実行
                result = func(*args, **kwargs)
                
                # 成功時の監査ログ（dbが利用可能な場合のみ）
                if db:
                    audit_service = AuditService(db)
                    audit_service.log_event(
                        event_type=event_type,
                        resource=resource,
                        action=action,
                        user_id=current_user.id if current_user else None,
                        user_type=current_user.role if current_user else None,
                        success=True,
                        request=request,
                        details={"result": "success"}
                    )
                
                return result
            except Exception as e:
                # エラー時の監査ログ
                if db:
                    audit_service = AuditService(db)
                    audit_service.log_event(
                        event_type=event_type,
                        resource=resource,
                        action=action,
                        user_id=current_user.id if current_user else None,
                        user_type=current_user.role if current_user else None,
                        success=False,
                        request=request,
                        details={"error": str(e)}
                    )
                raise e
        return wrapper
    return decorator


# 継続的検証付き監査ログデコレーター
def continuous_verification_audit(
    event_type: AuditEventType,
    resource: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    user_type: Optional[str] = None
):
    """継続的検証付き監査ログデコレーター"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 既存の監査ログ処理
            result = await audit_log(
                event_type, resource, action, user_id, user_type
            )(func)(*args, **kwargs)
            
            # 継続的検証の追加
            try:
                from app.core.security.continuous_verification.service import ContinuousVerificationService
                from app.core.dependencies import get_db
                import logging
                
                logger = logging.getLogger(__name__)
                
                # データベースセッションを取得
                db = None
                for arg in args:
                    if hasattr(arg, 'execute') and hasattr(arg, 'commit'):
                        db = arg
                        break
                
                if db:
                    # 継続的検証サービスを初期化
                    cv_service = ContinuousVerificationService(db)
                    
                    # リクエストオブジェクトを取得
                    request = None
                    for arg in args:
                        if isinstance(arg, Request):
                            request = arg
                            break
                    
                    if request:
                        # セッションIDを取得
                        session_id = kwargs.get('session_id') or 'unknown'
                        
                        # 継続的検証を実行
                        await cv_service.monitor_session(
                            session_id=session_id,
                            request=request,
                            user_id=user_id,
                            user_type=user_type
                        )
                
            except Exception as e:
                # 継続的検証のエラーは本処理を妨げない
                logger.error(f"継続的検証でエラー: {e}")
            
            return result
        return wrapper
    return decorator
