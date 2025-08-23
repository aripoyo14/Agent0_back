# app/api/routes/user.py
"""
ユーザー管理用APIルート
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import logging
from app.schemas.user import UserCreate, UserOut, UserRegisterResponse, RoleUpdateRequest
from app.core.security import verify_password, hash_password
from app.core.security.jwt import decode_access_token 
from app.core.security.encryption import encryption_service
from app.core.security.audit import AuditService, AuditEventType
from app.core.security.rbac.service import RBACService
from app.core.security.mfa import MFAService
from app.core.security.rate_limit.dependencies import check_user_register_rate_limit
from app.crud.user import create_user, get_user_by_email
from app.models.user import User, Department, Position
from app.db.session import get_db
from app.services.qr_code import QRCodeService
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import List
import os

# RBAC関連のインポート
from app.core.security.rbac.decorators import require_user_permissions
from app.core.security.rbac.permissions import Permission

# ロガーの設定
logger = logging.getLogger(__name__)

# ログレベルを設定（開発環境ではDEBUG、本番環境ではINFO）
if os.getenv("ENVIRONMENT", "development") == "development":
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

# FastAPIのルーターを初期化
router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/register", response_model=UserRegisterResponse)
def register_user(
    http_request: Request,
    user_data: UserCreate, 
    db: Session = Depends(get_db),
    rate_limit_check: bool = Depends(check_user_register_rate_limit)
):
    """新規ユーザー登録（MFA必須）"""
    
    # 監査サービスの初期化
    audit_service = AuditService(db)
    
    try:
        # 1. パスワードをハッシュ化
        password_hash = hash_password(user_data.password)
        
        # 2. MFA設定用の秘密鍵・バックアップコード生成
        totp_secret = MFAService.generate_totp_secret()
        backup_codes = MFAService.generate_backup_codes()
        
        # 3. 基本ユーザー作成（パスワードハッシュを渡す）
        user = create_user(db, user_data, password_hash)
        
        # 4. MFA関連フィールドを設定
        user.mfa_totp_secret = totp_secret
        user.mfa_backup_codes = backup_codes
        user.mfa_required = True
        user.account_active = False  # MFA設定完了まで無効

        # 5. すべての変更をコミット
        db.commit()
        
        # 4. 成功時の監査ログ
        audit_service.log_event(
            event_type=AuditEventType.USER_REGISTER_SUCCESS,
            user_id=str(user.id),
            user_type="user",
            resource="auth",
            action="register",
            success=True,
            request=http_request,
            details={
                "email": user_data.email,
                "mfa_required": True,
                "account_status": "pending_mfa_setup"
            }
        )
        
        # 5. MFA設定用の情報を返す
        return {
            "message": "ユーザー登録完了。MFA設定が必要です。",
            "user_id": str(user.id),
            "mfa_setup_required": True,
            "totp_secret": totp_secret,
            "backup_codes": backup_codes,
            "qr_code_url": f"/api/mfa/setup/{user.id}",
            "next_step": "complete_mfa_setup"
        }
        
    except Exception as e:
        # エラー時の監査ログ
        audit_service.log_event(
            event_type=AuditEventType.USER_REGISTER_FAILURE,
            resource="auth",
            action="register",
            success=False,
            request=http_request,
            details={
                "email": user_data.email,
                "error": str(e)
            }
        )
        raise

# ユーザーログイン用のエンドポイント
# @router.post("/login", response_model=UserLoginResponse)
# def login_user(request: UserLoginRequest, db: Session = Depends(get_db)):

#     # メールでユーザーを検索
#     user = get_user_by_email(db, email=request.email)
    
#     # ユーザーが存在しない or パスワードが間違っている場合はエラー
#     if not user or not verify_password(request.password, user.password_hash):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="メールアドレスまたはパスワードが正しくありません。",
#         )

#     # JWTトークンを発行
#     token = create_access_token({
#         "sub": str(user.id),
#         "role": "user",
#         "user_type": "user"
#     })

#     # トークンとユーザー情報をレスポンスとして返す
#     return UserLoginResponse(
#         access_token=token,
#         user=user
#     )

# 現在ログイン中のユーザーのプロフィール情報取得用のエンドポイント
@router.get("/me", response_model=UserOut)
def get_user_profile(token: str = Depends(HTTPBearer()), db: Session = Depends(get_db)):
    """
    現在ログイン中のユーザーのプロフィール情報を取得する。
    
    ## 機能
    - JWTトークンからユーザー情報を取得
    - データベースから最新のユーザー情報を取得
    - 詳細なエラーハンドリングとログ出力
    
    ## レスポンス
    - 成功時: ユーザーのプロフィール情報
    - エラー時: 詳細なエラーメッセージ
    
    ## エラーケース
    - 401: 無効なトークン、トークンデコード失敗、ユーザーが見つからない
    - 500: サーバー内部エラー
    """
    try:
        # JWTトークンをデコード
        payload = decode_access_token(token.credentials)
        
        # デバッグログを追加
        logger.info(f"=== /api/users/me デバッグ情報 ===")
        logger.info(f"Token payload: {payload}")
        
        if not payload:
            logger.error("JWTトークンのデコードに失敗")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なトークンです（デコード失敗）"
            )
        
        user_id = payload.get("sub")
        role = payload.get("role")
        token_type = payload.get("user_type")
        
        logger.info(f"user_id: {user_id}, role: {role}, token_type: {token_type}")
        
        if not user_id or not role or not token_type:
            logger.error(f"トークンペイロードに必要な情報が不足: user_id={user_id}, role={role}, token_type={token_type}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="トークンに必要な情報が不足しています"
            )
        
        # ユーザー情報を取得
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"ユーザーが見つかりません: user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザーが見つかりません"
            )
        
        # メールアドレスを復号化
        try:
            decrypted_email = encryption_service.decrypt_data(user.email) if user.email else None
            logger.info(f"メールアドレス復号化成功: {decrypted_email}")
        except Exception as e:
            logger.warning(f"メールアドレスの復号化に失敗: {e}")
            decrypted_email = None
        
        # UserOutスキーマに合わせてデータを構築
        user_data = {
            "id": user.id,
            "email": decrypted_email,  # 復号化されたメールアドレス
            "last_name": user.last_name,
            "first_name": user.first_name,
            "role": user.role,
            "extension": getattr(user, 'extension', None),
            "direct_phone": getattr(user, 'direct_phone', None),
            "is_active": getattr(user, 'is_active', True),
            "mfa_enabled": getattr(user, 'mfa_enabled', False),
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "last_login_at": user.last_login_at
        }
        
        logger.info(f"ユーザープロフィール取得成功: {user.first_name} {user.last_name}")
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバー内部エラー"
        )

# デバッグ用：トークンの内容を確認（開発環境のみ）
@router.get("/debug-token")
def debug_token(token: str = Depends(HTTPBearer())):
    """
    デバッグ用：トークンの内容を確認（開発環境のみ）
    
    ## 機能
    - JWTトークンの内容を確認
    - トークンの有効性をチェック
    - ペイロードの詳細情報を表示
    
    ## 注意
    - 開発環境でのみ使用してください
    - 本番環境では削除または無効化してください
    """
    try:
        payload = decode_access_token(token.credentials)
        return {
            "token_valid": payload is not None,
            "payload": payload,
            "user_id": payload.get("sub") if payload else None,
            "role": payload.get("role") if payload else None,
            "token_type": payload.get("user_type") if payload else None,
            "exp": payload.get("exp") if payload else None,
            "iat": payload.get("iat") if payload else None
        }
    except Exception as e:
        logger.error(f"トークンデバッグエラー: {e}")
        return {
            "token_valid": False,
            "error": str(e),
            "payload": None
        }

# QRコード生成エンドポイント
@router.get("/users/{user_id}/profile-qr")
def generate_profile_qr(user_id: str):
    """ユーザープロフィール用のQRコードを生成"""
    profile_url = f"https://agent0.com/profile/{user_id}"
    qr_code = QRCodeService.generate_custom_qr(
        data=profile_url,
        box_size=8,
        border=3
    )
    return {"qr_code": qr_code, "profile_url": profile_url}

# 部署一覧取得エンドポイント
@router.get("/departments", response_model=List[dict])
def get_departments(db: Session = Depends(get_db)):
    """利用可能な部署一覧を取得"""
    departments = db.query(Department).filter(Department.is_active == True).all()
    return [
        {
            "id": dept.id,
            "name": dept.name,
            "section": dept.section
        }
        for dept in departments
    ]

# 役職一覧取得エンドポイント
@router.get("/positions", response_model=List[dict])
def get_positions(db: Session = Depends(get_db)):
    """利用可能な役職一覧を取得"""
    positions = db.query(Position).filter(Position.is_active == True).all()
    return [
        {
            "id": pos.id,
            "name": pos.name
        }
        for pos in positions
    ]

# ユーザーロール変更エンドポイント
@router.put("/{user_id}/role", response_model=UserOut)
def change_user_role(
    user_id: str,
    role_update: RoleUpdateRequest,
    current_user: User = Depends(require_user_permissions(Permission.USER_ROLE_CHANGE)),
    db: Session = Depends(get_db)   
):
    """ユーザーのロールを変更（管理者のみ）"""
    
    # 対象ユーザーを取得
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません"
        )
    
    # ロール階層チェック（自分より上位のロールには変更不可）
    if not RBACService.can_manage_user(current_user, target_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このユーザーのロールを変更する権限がありません"
        )
    
    # ロール変更
    target_user.role = role_update.role
    db.commit()
    db.refresh(target_user)
    
    return target_user

# テスト用：認証状態を確認（開発環境のみ）
@router.get("/test-auth")
def test_auth(token: str = Depends(HTTPBearer())):
    """
    テスト用：認証状態を確認（開発環境のみ）
    
    ## 機能
    - 認証処理の各段階をテスト
    - 詳細なデバッグ情報を提供
    - エラーの原因を特定
    
    ## 注意
    - 開発環境でのみ使用してください
    - 本番環境では削除または無効化してください
    """
    try:
        logger.info("=== 認証テスト開始 ===")
        
        # 1. トークンのデコード
        logger.info("1. トークンデコード開始")
        payload = decode_access_token(token.credentials)
        logger.info(f"   デコード結果: {payload is not None}")
        
        if not payload:
            logger.error("   デコード失敗")
            return {
                "status": "failed",
                "step": "token_decode",
                "error": "トークンのデコードに失敗"
            }
        
        # 2. ペイロードの内容確認
        logger.info("2. ペイロード内容確認")
        user_id = payload.get("sub")
        role = payload.get("role")
        token_type = payload.get("user_type")
        
        logger.info(f"   user_id: {user_id}")
        logger.info(f"   role: {role}")
        logger.info(f"   token_type: {token_type}")
        
        if not user_id or not role or not token_type:
            logger.error("   必要な情報が不足")
            return {
                "status": "failed",
                "step": "payload_validation",
                "error": "トークンに必要な情報が不足",
                "user_id": user_id,
                "role": role,
                "token_type": token_type
            }
        
        # 3. データベース接続確認
        logger.info("3. データベース接続確認")
        db = next(get_db())
        
        # 4. ユーザー情報取得
        logger.info("4. ユーザー情報取得")
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            logger.error(f"   ユーザーが見つかりません: {user_id}")
            return {
                "status": "failed",
                "step": "user_lookup",
                "error": "ユーザーが見つかりません",
                "user_id": user_id
            }
        
        logger.info(f"   ユーザー取得成功: {user.first_name} {user.last_name}")
        
        return {
            "status": "success",
            "user": {
                "id": str(user.id),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "role": user.role
            },
            "token_info": {
                "user_id": user_id,
                "role": role,
                "token_type": token_type
            }
        }
        
    except Exception as e:
        logger.error(f"認証テストエラー: {e}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }