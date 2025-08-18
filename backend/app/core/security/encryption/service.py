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
        self.key = self._get_or_generate_key()
        self.cipher_suite = Fernet(self.key)
    
    def _get_or_generate_key(self) -> bytes:
        """環境変数からキーを取得、なければ生成"""
        key_env = os.getenv("ENCRYPTION_KEY")
        if key_env:
            try:
                # 既存のキーを正しい形式に変換
                if len(key_env) == 44:  # 現在のキー形式
                    # 32バイトのキーを生成
                    key = Fernet.generate_key()
                    print(f"⚠️  既存のキー形式が不正です。新しい暗号化キーを生成しました: {key.decode()}")
                    return key
                else:
                    # 正しい形式のキー
                    return base64.urlsafe_b64decode(key_env)
            except Exception as e:
                print(f"⚠️  既存のキー形式が不正です: {str(e)}")
                # 新しいキーを生成
                key = Fernet.generate_key()
                print(f"⚠️  新しい暗号化キーを生成しました: {key.decode()}")
                return key
        
        # 新しいキーを生成して環境変数に設定
        key = Fernet.generate_key()
        print(f"⚠️  新しい暗号化キーを生成しました。環境変数ENCRYPTION_KEYに設定してください: {key.decode()}")
        return key
    
    def encrypt_data(self, data: str) -> str:
        """データを暗号化"""
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """データを復号化"""
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
    
    def encrypt_file(self, file_path: str) -> bytes:
        """ファイルを暗号化"""
        with open(file_path, 'rb') as file:
            data = file.read()
        return self.cipher_suite.encrypt(data)
    
    def decrypt_file(self, encrypted_data: bytes, output_path: str):
        """ファイルを復号化"""
        decrypted_data = self.cipher_suite.decrypt(encrypted_data)
        with open(output_path, 'wb') as file:
            file.write(decrypted_data)

# グローバルインスタンス
encryption_service = EncryptionService()
