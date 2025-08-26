"""
監査ログ用デコレーター（ベストプラクティス版）
- 依存は kwargs / request.state から明示取得
- 成否に関わらず finally でロギング
- 非同期/同期の両方に対応（sync → anyio.from_thread.run で安全に await）
- 監査ログ失敗は本処理に影響させない
- 継続的検証（Continuous Verification）は本処理完了後に非同期 fire-and-forget
"""
from __future__ import annotations

from functools import wraps
from typing import Optional, Callable, Any, Dict, Tuple
import logging
import inspect
import asyncio

from fastapi import Request
from anyio import from_thread

from app.core.security.audit.service import AuditService
from app.core.security.audit.models import AuditEventType

# Optional: Continuous Verification（ある場合のみ読み込み）
try:
    from app.core.security.continuous_verification.service import (
        ContinuousVerificationService,
    )
    HAS_CV = True
except Exception:
    HAS_CV = False


logger = logging.getLogger(__name__)


# ------------------------------
# ユーティリティ
# ------------------------------
def _extract_request(args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> Optional[Request]:
    # 1) 明示名
    for key in ("request", "http_request"):
        if isinstance(kwargs.get(key), Request):
            return kwargs[key]
    # 2) 位置引数
    for a in args:
        if isinstance(a, Request):
            return a
    # 3) 取得不可
    return None


def _extract_db(args: Tuple[Any, ...], kwargs: Dict[str, Any], request: Optional[Request]):
    # 1) 明示名
    for key in ("db", "session"):
        if key in kwargs:
            return kwargs[key]
    # 2) 位置引数（SQLAlchemy Session ライク）
    for a in args:
        if hasattr(a, "execute") and hasattr(a, "commit"):
            return a
    # 3) request.state.db（DB セッションをミドルウェア注入している場合）
    if request is not None:
        db = getattr(getattr(request, "state", None), "db", None)
        if db is not None:
            return db
    return None


def _extract_user(
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
    request: Optional[Request],
    explicit_user_id: Optional[str],
    explicit_user_type: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """
    user_id / user_type をできるだけ確実に抽出
    優先順位:
      kwargs['current_user'] → args の user らしきもの → request.state.user → 明示引数
    """
    user_obj = kwargs.get("current_user")

    if user_obj is None:
        # 位置引数から user らしきものを拾う（id/role or user_type があるもの）
        for a in args:
            if hasattr(a, "id") and (hasattr(a, "role") or hasattr(a, "user_type")):
                user_obj = a
                break
            if isinstance(a, dict) and ("user_id" in a or "role" in a or "user_type" in a):
                user_obj = a
                break

    if user_obj is None and request is not None:
        user_obj = getattr(getattr(request, "state", None), "user", None)

    user_id = explicit_user_id
    user_type = explicit_user_type

    if user_obj is not None:
        if hasattr(user_obj, "id"):
            user_id = str(getattr(user_obj, "id"))
        elif isinstance(user_obj, dict) and "user_id" in user_obj:
            user_id = str(user_obj["user_id"])

        if hasattr(user_obj, "role"):
            user_type = getattr(user_obj, "role")
        elif hasattr(user_obj, "user_type"):
            user_type = getattr(user_obj, "user_type")
        elif isinstance(user_obj, dict) and "role" in user_obj:
            user_type = user_obj["role"]
        elif isinstance(user_obj, dict) and "user_type" in user_obj:
            user_type = user_obj["user_type"]

    return user_id, user_type


async def _audit_log_async(
    audit_service: AuditService,
    *,
    event_type: AuditEventType,
    resource: Optional[str],
    action: Optional[str],
    user_id: Optional[str],
    user_type: Optional[str],
    success: bool,
    request: Optional[Request],
    details: Dict[str, Any],
) -> None:
    """AuditService.log_event() は非同期前提で await する"""
    try:
        await audit_service.log_event(
            event_type=event_type,
            resource=resource,
            action=action,
            user_id=user_id,
            user_type=user_type,
            success=success,
            request=request,
            details=details,
        )
    except Exception as e:
        # 監査ログ失敗は本処理に影響させない
        logger.debug("Audit logging failed: %s", e)


def _audit_log_sync_in_thread(
    audit_service: AuditService,
    *,
    event_type: AuditEventType,
    resource: Optional[str],
    action: Optional[str],
    user_id: Optional[str],
    user_type: Optional[str],
    success: bool,
    request: Optional[Request],
    details: Dict[str, Any],
) -> None:
    """
    同期エンドポイント（FastAPI はスレッドプールで実行されがち）から
    非同期メソッドを安全に実行するため anyio.from_thread.run を使う。
    """
    try:
        from_thread.run(
            audit_service.log_event,
            event_type=event_type,
            resource=resource,
            action=action,
            user_id=user_id,
            user_type=user_type,
            success=success,
            request=request,
            details=details,
        )
    except Exception as e:
        logger.debug("Audit logging failed (sync wrapper): %s", e)


# ------------------------------
# デコレーター本体
# ------------------------------

def audit_log_sync(
    event_type: AuditEventType,
    *,
    resource: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    user_type: Optional[str] = None,
):
    """
    同期関数専用の監査ログデコレーター
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            request = _extract_request(args, kwargs)
            db = _extract_db(args, kwargs, request)
            uid, utype = _extract_user(args, kwargs, request, user_id, user_type)

            success = False
            details: Dict[str, Any] = {}

            try:
                result = func(*args, **kwargs)
                success = True
                details = {"result": "success"}
                return result
            except Exception as e:
                details = {"error": str(e)}
                raise
            finally:
                if db is not None:
                    audit_service = AuditService(db)
                    _audit_log_sync_in_thread(
                        audit_service,
                        event_type=event_type,
                        resource=resource,
                        action=action,
                        user_id=uid,
                        user_type=utype,
                        success=success,
                        request=request,
                        details=details,
                    )
                else:
                    logger.debug("Audit skipped (no DB session).")

        return wrapper
    return decorator


def audit_log(
    event_type: AuditEventType,
    *,
    resource: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    user_type: Optional[str] = None,
):
    """
    非同期/同期のエンドポイント両対応デコレーター。
    - エンドポイントが async def の場合 → そのまま await
    - def（同期）の場合 → anyio.from_thread.run で安全に実行
    """
    def decorator(func: Callable):
        is_async = inspect.iscoroutinefunction(func)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            request = _extract_request(args, kwargs)
            db = _extract_db(args, kwargs, request)
            uid, utype = _extract_user(args, kwargs, request, user_id, user_type)

            # 本処理
            try:
                result = await func(*args, **kwargs)
                success = True
                details: Dict[str, Any] = {"result": "success"}
            except Exception as e:
                success = False
                details = {"error": str(e)}
                # 監査は finally で走らせる
                raise
            finally:
                if db is not None:
                    audit_service = AuditService(db)
                    await _audit_log_async(
                        audit_service,
                        event_type=event_type,
                        resource=resource,
                        action=action,
                        user_id=uid,
                        user_type=utype,
                        success=success,
                        request=request,
                        details=details,
                    )
                else:
                    logger.debug("Audit skipped (no DB session).")

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            request = _extract_request(args, kwargs)
            db = _extract_db(args, kwargs, request)
            uid, utype = _extract_user(args, kwargs, request, user_id, user_type)

            success = False
            details: Dict[str, Any] = {}

            try:
                result = func(*args, **kwargs)
                success = True
                details = {"result": "success"}
                return result
            except Exception as e:
                details = {"error": str(e)}
                raise
            finally:
                if db is not None:
                    audit_service = AuditService(db)
                    _audit_log_sync_in_thread(
                        audit_service,
                        event_type=event_type,
                        resource=resource,
                        action=action,
                        user_id=uid,
                        user_type=utype,
                        success=success,
                        request=request,
                        details=details,
                    )
                else:
                    logger.debug("Audit skipped (no DB session).")

        return async_wrapper if is_async else sync_wrapper

    return decorator


def continuous_verification_audit(
    event_type: AuditEventType,
    *,
    resource: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    user_type: Optional[str] = None,
    session_id_key: str = "session_id",  # kwargs から拾うキー名
):
    """
    継続的検証（Continuous Verification）を“本処理完了後に”非同期で実行するデコレーター。
    - 監査ログは audit_log を合成（ダブル実行しないよう素直にネスト）
    - CV 側は fire-and-forget（失敗はログのみ）
    """
    base = audit_log(
        event_type,
        resource=resource,
        action=action,
        user_id=user_id,
        user_type=user_type,
    )

    def decorator(func: Callable):
        # まず監査ログ付きの関数にしておく
        wrapped = base(func)
        is_async = inspect.iscoroutinefunction(wrapped)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 1) 本処理（＋監査ログ）はこれで完了
            result = await wrapped(*args, **kwargs)

            # 2) CV を後追いで実行
            if HAS_CV:
                try:
                    request = _extract_request(args, kwargs)
                    db = _extract_db(args, kwargs, request)

                    # session_idの取得を改善
                    sid = kwargs.get(session_id_key)
                    if not sid or sid == "unknown":
                        # request.stateからsession_idを取得を試行
                        sid = getattr(getattr(request, "state", None), "session_id", None)
                    if not sid:
                        # デフォルト値
                        sid = "unknown"
                    
                    uid, utype = _extract_user(args, kwargs, request, user_id, user_type)
                    
                    # request.stateからuser_idとuser_typeも取得を試行
                    if not uid:
                        uid = getattr(getattr(request, "state", None), "user_id", uid)
                    if not utype:
                        utype = getattr(getattr(request, "state", None), "user_type", utype)
                    
                    logger.debug(f"継続的検証情報取得: session_id={sid}, user_id={uid}, user_type={utype}")

                    if db is not None and request is not None:
                        cv = ContinuousVerificationService(db)

                        async def _run_cv():
                            try:
                                await cv.monitor_session(
                                    session_id=sid,
                                    request=request,
                                    user_id=uid,
                                    user_type=utype,
                                )
                            except Exception as e:
                                logger.debug("Continuous verification failed: %s", e)

                        # 現在のイベントループにスケジュール（火消し）
                        asyncio.create_task(_run_cv())
                except Exception as e:
                    logger.debug("Continuous verification scheduling failed: %s", e)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 監査は wrapped に委譲（sync なら sync で包まれている）
            result = wrapped(*args, **kwargs)

            if HAS_CV:
                try:
                    request = _extract_request(args, kwargs)
                    db = _extract_db(args, kwargs, request)

                    # session_idの取得を改善
                    sid = kwargs.get(session_id_key)
                    if not sid or sid == "unknown":
                        # request.stateからsession_idを取得を試行
                        sid = getattr(getattr(request, "state", None), "session_id", None)
                    if not sid:
                        # デフォルト値
                        sid = "unknown"
                    
                    uid, utype = _extract_user(args, kwargs, request, user_id, user_type)
                    
                    # request.stateからuser_idとuser_typeも取得を試行
                    if not uid:
                        uid = getattr(getattr(request, "state", None), "user_id", uid)
                    if not utype:
                        utype = getattr(getattr(request, "state", None), "user_type", utype)
                    
                    logger.debug(f"継続的検証情報取得: session_id={sid}, user_id={uid}, user_type={utype}")

                    if db is not None and request is not None:
                        cv = ContinuousVerificationService(db)

                        # スレッド → イベントループで実行
                        def _run_cv_in_thread():
                            from anyio import from_thread
                            try:
                                from_thread.run(
                                    cv.monitor_session,
                                    session_id=sid,
                                    request=request,
                                    user_id=uid,
                                    user_type=utype,
                                )
                            except Exception as e:
                                logger.debug("Continuous verification failed (sync): %s", e)

                        # fire-and-forget
                        try:
                            # 背景で動かす（ここでは単純に別スレッド起動でもOK）
                            import threading
                            threading.Thread(target=_run_cv_in_thread, daemon=True).start()
                        except Exception as e:
                            logger.debug("CV thread start failed: %s", e)

                except Exception as e:
                    logger.debug("Continuous verification scheduling failed: %s", e)

            return result

        return async_wrapper if is_async else sync_wrapper

    return decorator