# app/core/security/mfa/config.py
"""
MFA（多要素認証）設定管理
  - このファイルでは、TOTPやバックアップコード、ロックアウト時間などのMFA関連の設定を集中管理する。
  - すべての値は環境変数（.env）で上書き可能。
  - 環境変数の接頭辞は "MFA_"。
"""

from pydantic_settings import BaseSettings
from typing import Literal

class MFAConfig(BaseSettings):
    """MFA設定クラス"""
    
    # TOTP（ワンタイムパスワード）設定
    totp_algorithm: Literal["SHA1", "SHA256", "SHA512"] = "SHA1"    # ハッシュアルゴリズム（デフォルトはSHA1）
    totp_digits: Literal[6, 8] = 6    # ワンタイムパスワードの桁数（デフォルトは6桁）
    totp_period: int = 30   # ワンタイムパスワードの有効秒数（デフォルトは30秒）
    
    # バックアップコード設定
    backup_code_count: int = 10    # 発行するバックアップコードの数（デフォルトは10個）
    backup_code_length: int = 8    # バックアップコード1つあたりの桁数（デフォルトは8桁）
    
    # セキュリティ設定
    max_attempts: int = 3    # ロックアウトまでの最大試行回数（デフォルトは3回）
    lockout_duration: int = 300  # ロックアウト時間（デフォルトは5分）
    
    class Config:
        env_prefix = "MFA_"    # 環境変数の接頭辞（デフォルトは"MFA_"）
        env_file = ".env"    # 環境変数ファイルのパス（デフォルトは".env"）
        env_file_encoding = "utf-8"    # 環境変数ファイルのエンコーディング（デフォルトは"utf-8"）
        extra = "ignore"    # 未定義のキーは無視（StrictModeじゃない）
        
# グローバル設定インスタンス
mfa_config = MFAConfig()    # MFA設定インスタンスを作成
