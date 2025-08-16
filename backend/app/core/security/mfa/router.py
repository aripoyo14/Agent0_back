"""
MFA APIルーター
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.mfa import (
    MFAEnableRequest, MFAVerifyRequest, MFABackupCodeRequest,
    MFAStatusResponse, MFASetupResponse, MFAVerificationResponse
)
from .crud import (  # 相対インポートに変更
    enable_mfa, disable_mfa, update_mfa_backup_codes,
    get_mfa_status, verify_mfa_totp, verify_mfa_backup_code
)
from app.db.session import get_db
from app.models.user import User
from app.models.expert import Expert
from app.services.qr_code import QRCodeService
from .service import MFAService

router = APIRouter(prefix="/mfa", tags=["MFA"])

@router.post("/enable")
def enable_mfa_endpoint(
    user_id: str,
    mfa_data: MFAEnableRequest,
    db: Session = Depends(get_db)
):
    """MFAを有効化"""
    return enable_mfa(db, user_id, mfa_data.totp_secret, mfa_data.backup_codes)

@router.post("/disable")
def disable_mfa_endpoint(
    user_id: str,
    db: Session = Depends(get_db)
):
    """MFAを無効化"""
    return disable_mfa(db, user_id)

@router.get("/status/{user_id}")
def get_mfa_status_endpoint(
    user_id: str,
    db: Session = Depends(get_db)
):
    """MFA設定状況を取得"""
    return get_mfa_status(db, user_id)

@router.post("/verify-totp")
def verify_totp_endpoint(
    user_id: str,
    mfa_data: MFAVerifyRequest,
    db: Session = Depends(get_db)
):
    """TOTPコードを検証"""
    return verify_mfa_totp(db, user_id, mfa_data.totp_code)

@router.post("/verify-backup")
def verify_backup_code_endpoint(
    user_id: str,
    mfa_data: MFABackupCodeRequest,
    db: Session = Depends(get_db)
):
    """バックアップコードを検証"""
    return verify_mfa_backup_code(db, user_id, mfa_data.backup_code)

@router.post("/generate-secret")
def generate_totp_secret():
    """TOTP秘密鍵を生成（テスト用）"""
    secret = MFAService.generate_totp_secret()
    return {"secret": secret}

@router.post("/generate-backup-codes")
def generate_backup_codes():
    """バックアップコードを生成（テスト用）"""
    backup_codes = MFAService.generate_backup_codes()
    return {"backup_codes": backup_codes}


@router.get("/generate-qr/{user_id}")
def generate_qr_code(user_id: str, db: Session = Depends(get_db)):
    """QRコード生成（User/Expert両対応）"""
    
    try:
        # 1. まずUserテーブルで検索
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user_type = "user"
            totp_secret = user.mfa_totp_secret
            email = user.email  # メールアドレスを取得
        else:
            # 2. Userで見つからない場合はExpertテーブルで検索
            expert = db.query(Expert).filter(Expert.id == user_id).first()
            if expert:
                user_type = "expert"
                totp_secret = expert.mfa_totp_secret
                email = expert.email  # メールアドレスを取得
            else:
                raise HTTPException(
                    status_code=404,
                    detail="ユーザーまたはエキスパートが見つかりません"
                )
        
        if not totp_secret:
            raise HTTPException(
                status_code=400,
                detail="MFA秘密鍵が設定されていません"
            )
        
        # 3. QRコード生成（正しいメソッド名を使用）
        qr_service = QRCodeService()
        qr_result = qr_service.generate_totp_qr(
            secret=totp_secret,
            email=email,
            issuer="Agent0"
        )
        
        return {"qr_code": qr_result["qr_code"]}
        
    except Exception as e:
        print(f"QRコード生成エラー: {str(e)}")  # デバッグログ
        raise HTTPException(
            status_code=500,
            detail="QRコード生成に失敗しました"
        )

@router.post("/setup-complete")
def complete_mfa_setup(
    mfa_data: MFAEnableRequest,
    db: Session = Depends(get_db)
):
    """MFA設定完了（正式登録完了）"""
    
    try:
        user_id = mfa_data.user_id
        
        # 1. MFA有効化（User/Expert両対応）
        result = enable_mfa(db, user_id, mfa_data.totp_secret, mfa_data.backup_codes)
        
        # 2. アカウント制限解除と正式登録完了
        if result["user_type"] == "expert":
            expert = result["user"]
            expert.mfa_required = False
            expert.account_active = True
            expert.registration_status = "active"
            db.commit()
            
            return {
                "message": "MFA設定完了！エキスパート登録が完了しました。",
                "user_id": user_id,
                "mfa_enabled": True,
                "account_active": True,
                "registration_status": "active",
                "next_step": "login"
            }
        else:
            # Userの場合
            user = result["user"]
            user.mfa_required = False
            user.account_active = True
            db.commit()
            
            return {
                "message": "MFA設定完了！ユーザー登録が完了しました。",
                "user_id": user_id,
                "mfa_enabled": True,
                "account_active": True,
                "next_step": "login"
            }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MFA設定完了処理に失敗しました: {str(e)}"
        )