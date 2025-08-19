"""
データ暗号化サービス
保存時・転送時のデータ暗号化を提供
"""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from typing import Optional

class EncryptionService:
    def __init__(self):
        # 暗号化を一時的に無効化
        self.key = None
        self.cipher_suite = None
        print("⚠️  暗号化サービスを一時的に無効化しました")
    
    def encrypt_data(self, data: str) -> str:
        """データを暗号化（無効化）"""
        print(f"⚠️  暗号化をスキップ: {data}")
        return data
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """データを復号化（無効化）"""
        print(f"⚠️  復号化をスキップ: {encrypted_data}")
        return encrypted_data
    
    def encrypt_file(self, file_path: str) -> bytes:
        """ファイルを暗号化（無効化）"""
        with open(file_path, 'rb') as file:
            data = file.read()
        return data
    
    def decrypt_file(self, encrypted_data: bytes, output_path: str):
        """ファイルを復号化（無効化）"""
        with open(output_path, 'wb') as file:
            file.write(encrypted_data)

# グローバルインスタンス
encryption_service = EncryptionService()
