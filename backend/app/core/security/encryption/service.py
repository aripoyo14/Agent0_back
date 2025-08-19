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
        print("✅ 暗号化サービスが有効化されました")
    
    def _get_or_generate_key(self) -> bytes:
        """環境変数からキーを取得、なければ設定ファイルから取得"""
        # 環境変数から取得を試行
        key_env = os.getenv("ENCRYPTION_KEY")
        
        if key_env:
            # 44文字のFernetキーはそのまま使う（再デコードしない）
            if len(key_env) == 44:
                return key_env.encode()
            try:
                return base64.urlsafe_b64decode(key_env)
            except Exception as e:
                print(f"⚠️  環境変数の暗号化キー形式が不正です: {e}")
        
        # 環境変数がない場合、設定ファイルから取得
        try:
            from app.core.config import settings
            config_key = settings.encryption_key
            if config_key:
                if len(config_key) == 44:
                    return config_key.encode()
                return base64.urlsafe_b64decode(config_key)
        except Exception as e:
            print(f"⚠️  設定ファイルからの暗号化キー取得に失敗: {e}")
        
        # 最後の手段として新しいキーを生成
        key = Fernet.generate_key()
        print(f"⚠️  新しい暗号化キーを生成しました: {key.decode()}")
        return key
    
    def encrypt_data(self, data: str) -> str:
        """データを暗号化"""
        if not data:
            return data
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """データを復号化"""
        if not encrypted_data:
            return encrypted_data
        try:
            return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            print(f"⚠️  復号化に失敗しました: {str(e)}")
            # 復号化に失敗した場合（古いデータなど）はそのまま返す
            return encrypted_data
    
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
