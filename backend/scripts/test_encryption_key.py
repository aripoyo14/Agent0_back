#!/usr/bin/env python3
"""
現在の暗号化キーで復号化できるかテストするスクリプト
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.db.session import SessionLocal
from app.models.expert import Expert
from app.models.user import User
from app.core.security.encryption import encryption_service
from app.core.config import settings

def test_encryption_key():
    """現在の暗号化キーで復号化できるかテスト"""
    print("�� 暗号化キーのテストを開始します...")
    print(f"📋 設定されている暗号化キー: {settings.encryption_key}")
    print(f"📋 暗号化キーの長さ: {len(settings.encryption_key)}文字")
    
    # 1. 基本的な暗号化・復号化テスト
    print("\n�� 基本的な暗号化・復号化テスト:")
    test_data = "hiroshimori@hotmail.com"
    try:
        encrypted = encryption_service.encrypt_data(test_data)
        decrypted = encryption_service.decrypt_data(encrypted)
        print(f"✅ テスト成功: '{test_data}' -> '{decrypted}'")
        print(f"   暗号化後: {encrypted[:50]}...")
    except Exception as e:
        print(f"❌ 基本的な暗号化・復号化テスト失敗: {str(e)}")
        return False
    
    # 2. データベース内のExpertデータの復号化テスト
    print("\n�� データベース内のExpertデータの復号化テスト:")
    db = SessionLocal()
    try:
        experts = db.query(Expert).all()
        print(f"�� データベース内のExpert数: {len(experts)}")
        
        if len(experts) == 0:
            print("⚠️  Expertデータが存在しません")
        else:
            for i, expert in enumerate(experts[:5]):  # 最初の5件のみテスト
                print(f"\n📝 Expert {i+1}: {expert.last_name} {expert.first_name}")
                print(f"   メールアドレス: {expert.email}")
                
                if expert.email:
                    try:
                        decrypted_email = expert.get_decrypted_email()
                        print(f"   ✅ 復号化成功: {decrypted_email}")
                    except Exception as e:
                        print(f"   ❌ 復号化失敗: {str(e)}")
                        print(f"   🔍 エラーの詳細: {type(e).__name__}")
                else:
                    print("   ℹ️  メールアドレスが設定されていません")
                
                if expert.mobile:
                    try:
                        decrypted_mobile = expert.get_decrypted_mobile()
                        print(f"   携帯電話: {decrypted_mobile}")
                    except Exception as e:
                        print(f"   ❌ 携帯電話復号化失敗: {str(e)}")
    
    except Exception as e:
        print(f"❌ データベースアクセスエラー: {str(e)}")
    finally:
        db.close()
    
    # 3. データベース内のUserデータの復号化テスト
    print("\n�� データベース内のUserデータの復号化テスト:")
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"📊 データベース内のUser数: {len(users)}")
        
        if len(users) == 0:
            print("⚠️  Userデータが存在しません")
        else:
            for i, user in enumerate(users[:5]):  # 最初の5件のみテスト
                print(f"\n📝 User {i+1}: {user.last_name} {user.first_name}")
                print(f"   メールアドレス: {user.email}")
                
                if user.email:
                    try:
                        decrypted_email = user.get_decrypted_email()
                        print(f"   ✅ 復号化成功: {decrypted_email}")
                    except Exception as e:
                        print(f"   ❌ 復号化失敗: {str(e)}")
                        print(f"   🔍 エラーの詳細: {type(e).__name__}")
                else:
                    print("   ℹ️  メールアドレスが設定されていません")
    
    except Exception as e:
        print(f"❌ データベースアクセスエラー: {str(e)}")
    finally:
        db.close()
    
    print("\n�� 暗号化キーテストが完了しました")
    return True

if __name__ == "__main__":
    test_encryption_key()
