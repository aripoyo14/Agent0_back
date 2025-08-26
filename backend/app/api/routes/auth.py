# app/api/routes/auth.py
"""
 - ユーザーのログイン認証用APIルートを定義するモジュール。
 - 入力されたメールアドレス・パスワードを検証し、
   有効であればJWTトークンを返す。
"""

import inspect
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.schemas.auth import LoginRequest, TokenResponse
from app.core.security import verify_password
from app.core.security.jwt import create_access_token
from app.core.security.audit import AuditService, AuditEventType
from app.core.security.audit.decorators import continuous_verification_audit
from app.core.security.session import session_manager, SessionCreate
from app.db.session import get_db
from app.models.user import User
from app.models.expert import Expert
from app.core.security.rbac.service import RBACService
from app.core.security.rate_limit.dependencies import check_auth_login_rate_limit

# ロガーの設定
logger = logging.getLogger(__name__)

# 既存のインポートに追加
import uuid
from app.crud.user import get_user_by_email
from app.crud.expert import get_expert_by_email
from sqlalchemy import text

# アクセストークンの有効期限を設定から取得
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])

# User/ExpertログインAPI (ユーザー認証を行い、アクセストークン（JWT）を発行して返す)
# 一時的に監査ログデコレーターを無効化
# @continuous_verification_audit(
#     event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
#     resource="auth",
#     action="login",
#     user_type="user",
#     session_id_key="session_id"
# )
@router.post("/login")
@continuous_verification_audit(
    event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
    resource="auth",
    action="login",
    user_type="user",
    session_id_key="session_id"
)
async def login_user(
    http_request: Request, 
    request: LoginRequest, 
    db: Session = Depends(get_db),
    rate_limit_check: bool = Depends(check_auth_login_rate_limit)
):
    
    # 詳細なデバッグログを追加
    logger.debug("ログイン関数が呼び出されました")
    logger.debug(f"リクエストIP: {http_request.client.host if http_request.client else 'unknown'}")
    logger.debug(f"リクエストメール: {request.email}")
    logger.debug(f"データベースセッション: {db}")
    
    # 監査サービスの初期化
    audit_service = AuditService(db)

    try:
        # データベース接続テスト
        logger.debug("データベース接続をテスト中...")
        test_result = db.execute(text("SELECT 1"))
        logger.debug("データベース接続成功")

        # 修正：暗号化されたメールアドレスでユーザーを検索
        logger.debug("ユーザー検索中...")
        user = get_user_by_email(db, request.email)
        logger.debug(f"ユーザー検索結果: {user}")

        # ユーザーが存在して、パスワードが正しい場合
        if user and verify_password(request.password, user.password_hash):
                logger.debug(f"ユーザー認証成功: {user.email}")

                # ユーザーの権限を取得
                user_permissions = RBACService.get_user_permissions(user)

                # セッションIDを生成
                session_id = str(uuid.uuid4())

                # セッション管理を使用してログイン（修正版）
                session_created = session_manager.create_session(
                    session_id=session_id,
                    user_id=str(user.id),
                    user_type="user",
                    role=user.role,  # roleを追加
                    metadata={
                        "ip_address": http_request.client.host if http_request.client else None,
                        "user_agent": http_request.headers.get("user-agent")
                    }
                )

                if not session_created:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="セッションの作成に失敗しました"
                    )

                # 継続的検証システム用にsession_idをrequest.stateに設定
                http_request.state.session_id = session_id
                http_request.state.user_id = str(user.id)
                http_request.state.user_type = "user"
                
                logger.debug(f"継続的検証用情報設定完了: session_id={session_id}, user_id={user.id}, user_type=user")
                
                # アクセストークンとリフレッシュトークンを作成
                access_token = session_manager._create_access_token(
                    str(user.id), "user", list(user_permissions), session_id, user.role
                )
                refresh_token = session_manager._create_refresh_token(session_id)
                
                # 継続的検証システム用のsession_idを明示的に設定
                # デコレータがkwargsからsession_idを取得できるようにする
                try:
                    import inspect
                    current_frame = inspect.currentframe()
                    if current_frame and current_frame.f_back:
                        # 呼び出し元のフレームのkwargsにsession_idを追加
                        caller_frame = current_frame.f_back
                        if 'kwargs' in caller_frame.f_locals:
                            caller_frame.f_locals['kwargs']['session_id'] = session_id
                            logger.debug(f"継続的検証用session_id設定完了: {session_id}")
                        else:
                            logger.warning("継続的検証用session_id設定失敗: kwargsが見つかりません")
                    else:
                        logger.warning("継続的検証用session_id設定失敗: フレーム情報が取得できません")
                except Exception as e:
                    logger.warning(f"継続的検証用session_id設定でエラー: {e}")
                    pass
                
                # 成功時の監査ログ
                try:
                    audit_service.log_event(
                        event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
                        user_id=str(user.id),
                        user_type="user",
                        resource="auth",
                        action="login",
                        success=True,
                        request=http_request,
                        details={
                            "email": request.email,
                            "role": user.role,
                            "permissions_count": len(user_permissions),
                            "session_id": session_id
                        }
                    )
                    logger.debug("監査ログの保存に成功")
                except Exception as audit_error:
                    logger.warning(f"監査ログの保存に失敗: {audit_error}")
                    # 監査ログの保存に失敗しても認証処理は継続
                    pass
                
                # アクセストークンの有効期限を設定から取得
                return {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "session_id": session_id,
                    "expires_in": settings.access_token_expire_minutes * 60,  # 秒単位に変換
                    "token_type": "Bearer",
                    "user_type": "user",
                    "role": user.role
                }
        else:
            # 修正: userがNoneの場合を考慮
            if user:
                logger.warning(f"ユーザーパスワード検証失敗: {user.email}")
            else:
                logger.warning(f"ユーザーが見つかりません: {request.email}")
        
        # Userで見つからない場合、Expertテーブルで検索
        if not user:
            expert = get_expert_by_email(db, request.email)
            if expert and verify_password(request.password, expert.password_hash):

                # デバッグログを追加
                logger.debug(f"Expert認証成功: {expert.email}")
                logger.debug(f"Expert role: {expert.role}")
                logger.debug(f"Expert role type: {type(expert.role)}")

                try:
                    # Expertの権限を取得
                    expert_permissions = RBACService.get_expert_permissions(expert)
                    logger.debug(f"Expert permissions: {expert_permissions}")
                except Exception as e:
                    logger.error(f"Expert権限取得エラー: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Expert権限の取得に失敗しました: {str(e)}"
                    )

                # セッションIDを生成
                session_id = str(uuid.uuid4())

                # セッション管理を使用してログイン（修正版）
                session_created = session_manager.create_session(
                    session_id=session_id,
                    user_id=str(expert.id),
                    user_type="expert",
                    role=expert.role,  # roleを追加
                    metadata={
                        "ip_address": http_request.client.host if http_request.client else None,
                        "user_agent": http_request.headers.get("user-agent")
                    }
                )

                if not session_created:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="セッションの作成に失敗しました"
                    )

                # 継続的検証システム用にsession_idをrequest.stateに設定
                http_request.state.session_id = session_id
                http_request.state.user_id = str(expert.id)
                http_request.state.user_type = "expert"
                
                logger.debug(f"継続的検証用情報設定完了: session_id={session_id}, user_id={expert.id}, user_type=expert")

                # アクセストークンとリフレッシュトークンを作成
                access_token = session_manager._create_access_token(
                    str(expert.id), "expert", list(expert_permissions), session_id, expert.role
                )
                refresh_token = session_manager._create_refresh_token(session_id)
                
                # 継続的検証システム用のsession_idを明示的に設定
                # デコレータがkwargsからsession_idを取得できるようにする
                try:
                    import inspect
                    current_frame = inspect.currentframe()
                    if current_frame and current_frame.f_back:
                        # 呼び出し元のフレームのkwargsにsession_idを追加
                        caller_frame = current_frame.f_back
                        if 'kwargs' in caller_frame.f_locals:
                            caller_frame.f_locals['kwargs']['session_id'] = session_id
                            logger.debug(f"継続的検証用session_id設定完了: {session_id}")
                        else:
                            logger.warning("継続的検証用session_id設定失敗: kwargsが見つかりません")
                    else:
                        logger.warning("継続的検証用session_id設定失敗: フレーム情報が取得できません")
                except Exception as e:
                    logger.warning(f"継続的検証用session_id設定でエラー: {e}")
                    pass
                
                # 継続的検証システム用のsession_idを明示的に設定
                # デコレータがkwargsからsession_idを取得できるようにする
                import inspect
                current_frame = inspect.currentframe()
                if current_frame and current_frame.f_back:
                    # 呼び出し元のフレームのkwargsにsession_idを追加
                    caller_frame = current_frame.f_back
                    if 'kwargs' in caller_frame.f_locals:
                        caller_frame.f_locals['kwargs']['session_id'] = session_id
                        logger.debug(f"継続的検証用session_id設定完了: {session_id}")
                    else:
                        logger.warning("継続的検証用session_id設定失敗: kwargsが見つかりません")
                else:
                    logger.warning("継続的検証用session_id設定失敗: フレーム情報が取得できません")
                
                # 成功時の監査ログ
                try:
                    audit_service.log_event(
                        event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
                        user_id=str(expert.id),
                        user_type="expert",
                        resource="auth",
                        action="login",
                        success=True,
                        request=http_request,
                        details={
                            "email": request.email,
                            "role": expert.role,
                            "permissions_count": len(expert_permissions),
                            "session_id": session_id
                        }
                    )
                    logger.debug("監査ログの保存に成功")
                except Exception as audit_error:
                    logger.warning(f"監査ログの保存に失敗: {audit_error}")
                    # 監査ログの保存に失敗しても認証処理は継続
                    pass
                
                # アクセストークンの有効期限を設定から取得
                return {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "session_id": session_id,
                    "expires_in": settings.access_token_expire_minutes * 60,  # 秒単位に変換
                    "token_type": "Bearer",
                    "user_type": "expert",
                    "role": expert.role
                }
            else:
                # 修正: expertがNoneの場合を考慮
                if expert:
                    logger.warning(f"Expertパスワード検証失敗: {expert.email}")
                else:
                    logger.warning(f"Expertが見つかりません: {request.email}")
        
        # どちらでも認証失敗
        logger.warning(f"認証失敗: {request.email}")
        
        # 認証失敗時の監査ログ
        try:
            audit_service.log_event(
                event_type=AuditEventType.AUTH_LOGIN_FAILURE,
                resource="auth",
                action="login",
                success=False,
                request=http_request,
                details={
                    "email": request.email,
                    "reason": "invalid_credentials"
                }
            )
            logger.debug("認証失敗の監査ログ保存完了")
        except Exception as audit_error:
            logger.warning(f"認証失敗時の監査ログ保存に失敗: {audit_error}")
            pass
    
        # どちらでも認証失敗
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません。",
        )

    except HTTPException:
        # HTTPExceptionは再発生させる（認証失敗など）
        raise
    except Exception as e:
        # 予期しないエラーのみ監査ログに記録
        logger.error(f"認証処理で予期しないエラー: {e}")
        logger.error(f"エラーの型: {type(e)}")
        
        # 予期しないエラーの監査ログ（エラーハンドリングを追加）
        try:
            audit_service.log_event(
                event_type=AuditEventType.AUTH_LOGIN_FAILURE,
                resource="auth",
                action="login",
                success=False,
                request=http_request,
                details={
                    "email": request.email,
                    "reason": "unexpected_error",
                    "error": str(e)
                }
            )
        except Exception as audit_error:
            logger.warning(f"エラー時の監査ログ保存に失敗: {audit_error}")
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="認証処理中にエラーが発生しました。"
        )


# リフレッシュトークン用のリクエストモデルを追加
class RefreshTokenRequest(BaseModel):
    refresh_token: str

# リフレッシュトークンを使用してアクセストークンを更新
@router.post("/refresh")
@continuous_verification_audit(
    event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
    resource="auth",
    action="refresh"
)
async def refresh_token(request: RefreshTokenRequest):
    """リフレッシュトークンを使用してアクセストークンを更新"""

    refresh_token = request.refresh_token  # 直接アクセス
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="リフレッシュトークンが必要です"
        )
    
    # セッション管理サービスでトークンを更新
    try:
        session_response = session_manager.refresh_access_token(refresh_token)
        logger.debug(f"session_response: {session_response}")
        
        if session_response is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なリフレッシュトークンです"
            )
    
        return {
                "access_token": session_response.access_token,
                "expires_in": session_response.expires_in,
                "token_type": session_response.token_type
            }
        
    except Exception as e:
        logger.error(f"セッション更新エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="トークンの更新に失敗しました"
        )

# ログアウト（セッション無効化）
@router.post("/logout")
@continuous_verification_audit(
    event_type=AuditEventType.AUTH_LOGOUT,
    resource="auth",
    action="logout"
)
def logout(
    session_id: str,
    http_request: Request = None
):
    """セッションを無効化してログアウト"""
    
    success = session_manager.invalidate_session(session_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なセッションIDです"
        )
    
    return {"message": "ログアウトしました"}
