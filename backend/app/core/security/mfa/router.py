"""
MFA APIルーター
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.mfa import (
    MFAEnableRequest, MFAVerifyRequest, MFABackupCodeRequest,
    MFAStatusResponse, MFASetupResponse, MFAVerificationResponse
)
from app.crud.mfa import (
    enable_mfa, disable_mfa, update_mfa_backup_codes,
    get_mfa_status, verify_mfa_totp, verify_mfa_backup_code
)
from app.db.session import get_db
from app.models.user import User
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
    """TOTP用のQRコードを生成"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFAが有効化されていません"
        )
    
    try:
        qr_data = MFAService.generate_qr_code(
            secret=user.mfa_totp_secret,
            email=user.email,
            issuer="Agent0"
        )
        return qr_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"QRコード生成エラー: {str(e)}"
        )
