"""
MFAサービス - ビジネスロジック
"""

import pyotp
import secrets
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.services.qr_code import QRCodeService
from .config import mfa_config

class MFAService:
    """MFAサービスクラス"""
    
    @staticmethod
    def generate_totp_secret() -> str:
        """TOTP秘密鍵を生成"""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_backup_codes() -> List[str]:
        """バックアップコードを生成"""
        return [
            secrets.token_hex(mfa_config.backup_code_length // 2).upper() 
            for _ in range(mfa_config.backup_code_count)
        ]
    
    @staticmethod
    def verify_totp_code(secret: str, code: str) -> bool:
        """TOTPコードを検証"""
        totp = pyotp.TOTP(secret)
        return totp.verify(code)
    
    @staticmethod
    def generate_qr_code(secret: str, email: str, issuer: str = "Agent0") -> Dict:
        """TOTP用QRコードを生成"""
        return QRCodeService.generate_totp_qr(
            secret=secret,
            email=email,
            issuer=issuer
        )
    
    @staticmethod
    def get_totp_uri(secret: str, email: str, issuer: str = "Agent0") -> str:
        """TOTP URIを生成"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=email,
            issuer_name=issuer
        )
