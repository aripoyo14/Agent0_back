#!/usr/bin/env python3
"""
特定のユーザーの機密データのみを暗号化するスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security.encryption import encryption_service

def encrypt_single_user(user_id: str):
    """指定されたユーザーIDの機密データを暗号化"""
    db = SessionLocal()
    
    try:
        # 指定されたユーザーを取得
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            print(f"❌ ユーザーID {user_id} が見つかりません")
            return False
        
        print(f"🔍 ユーザー {user.last_name} {user.first_name} ({user.email}) を暗号化します")
        
        # 現在のデータの状態を確認
        print(f"📝 現在のメールアドレス: {user.email}")
        print(f"📝 現在の内線番号: {user.extension}")
        print(f"📝 現在の直通番号: {user.direct_phone}")
        print(f"📝 現在のMFA秘密鍵: {user.mfa_totp_secret}")
        print(f"📝 現在のバックアップコード: {user.mfa_backup_codes}")
        
        # 機密データを暗号化
        user.encrypt_sensitive_data()
        
        # 暗号化後のデータを確認
        print(f"🔐 暗号化後のメールアドレス: {user.email}")
        print(f"🔐 暗号化後の内線番号: {user.extension}")
        print(f"🔐 暗号化後の直通番号: {user.direct_phone}")
        print(f"🔐 暗号化後のMFA秘密鍵: {user.mfa_totp_secret}")
        print(f"🔐 暗号化後のバックアップコード: {user.mfa_backup_codes}")
        
        # データベースに保存
        db.add(user)
        db.commit()
        
        print(f"✅ ユーザー {user_id} の暗号化が完了しました")
        
        # 復号化テスト
        print("\n🧪 復号化テスト:")
        print(f"復号化されたメールアドレス: {user.get_decrypted_email()}")
        print(f"復号化された内線番号: {user.get_decrypted_extension()}")
        print(f"復号化された直通番号: {user.get_decrypted_direct_phone()}")
        
        return True
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("使用方法: python encrypt_single_user.py <ユーザーID>")
        print("例: python encrypt_single_user.py 7e1503af-7bbe-4aa1-aaee-3f42ad5a7b22")
        sys.exit(1)
    
    user_id = sys.argv[1]
    encrypt_single_user(user_id)
