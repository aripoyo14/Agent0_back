"""
MFA（Multi-Factor Authentication）関連のCRUD操作を定義するモジュール
"""

from sqlalchemy.orm import Session
from app.models.user import User
from fastapi import HTTPException, status
from datetime import datetime, timezone, timedelta
import pyotp
from app.models.expert import Expert

JST = timezone(timedelta(hours=9))

def enable_mfa(db: Session, user_id: str, totp_secret: str, backup_codes: list[str]) -> dict:
    """
    MFAを有効化し、TOTP秘密鍵とバックアップコードを設定する（User/Expert両対応）
    """
    # 1. まずUserテーブルで検索
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        # UserテーブルにMFA設定
        user.mfa_enabled = True
        user.mfa_totp_secret = totp_secret
        user.mfa_backup_codes = ",".join(backup_codes)
        user.updated_at = datetime.now(JST)
        db.commit()
        db.refresh(user)
        return {"user_type": "user", "user": user}
    
    # 2. Userで見つからない場合はExpertテーブルで検索
    expert = db.query(Expert).filter(Expert.id == user_id).first()
    if expert:
        # ExpertテーブルにMFA設定
        expert.mfa_enabled = True
        expert.mfa_totp_secret = totp_secret
        expert.mfa_backup_codes = backup_codes  # ExpertはJSONフィールド
        expert.updated_at = datetime.now(JST)
        db.commit()
        db.refresh(expert)
        return {"user_type": "expert", "user": expert}
    
    # 3. どちらも見つからない場合
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="ユーザーまたはエキスパートが見つかりません。"
    )

def disable_mfa(db: Session, user_id: str) -> User:
    """
    MFAを無効化し、関連する設定をクリアする
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません。"
        )
    
    # MFA設定をクリア
    user.mfa_enabled = False
    user.mfa_totp_secret = None
    user.mfa_backup_codes = None
    user.updated_at = datetime.now(JST)
    
    db.commit()
    db.refresh(user)
    return user

def update_mfa_backup_codes(db: Session, user_id: str, backup_codes: list[str]) -> User:
    """
    バックアップコードを更新する
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません。"
        )
    
    user.mfa_backup_codes = ",".join(backup_codes)
    user.updated_at = datetime.now(JST)
    
    db.commit()
    db.refresh(user)
    return user

def get_mfa_status(db: Session, user_id: str) -> dict:
    """
    ユーザーのMFA設定状況を取得する（セキュリティ上、秘密鍵は返さない）
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません。"
        )
    
    return {
        "mfa_enabled": user.mfa_enabled,
        "has_backup_codes": bool(user.mfa_backup_codes)
    }

def verify_mfa_totp(db: Session, user_id: str, totp_code: str) -> bool:
    """
    TOTPコードを検証する（実際のTOTP検証ロジックは別途実装が必要）
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません。"
        )
    
    if not user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFAが有効化されていません。"
        )
    
    if not user.mfa_totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP秘密鍵が設定されていません。"
        )
    
    # TOTP検証
    totp = pyotp.TOTP(user.mfa_totp_secret)
    is_valid = totp.verify(totp_code)
    return is_valid

def verify_mfa_backup_code(db: Session, user_id: str, backup_code: str) -> bool:
    """
    バックアップコードを検証し、使用済みにする
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません。"
        )
    
    if not user.mfa_enabled or not user.mfa_backup_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFAが有効化されていないか、バックアップコードが設定されていません。"
        )
    
    # バックアップコードの検証
    backup_codes_list = user.mfa_backup_codes.split(",")
    if backup_code in backup_codes_list:
        # 使用済みのコードを削除
        backup_codes_list.remove(backup_code)
        user.mfa_backup_codes = ",".join(backup_codes_list) if backup_codes_list else None
        user.updated_at = datetime.now(JST)
        
        db.commit()
        return True
    
    return False