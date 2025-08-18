#!/usr/bin/env python3
"""
既存のUserデータを暗号化するマイグレーションスクリプト
"""
import sys
import os
import json
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import SessionLocal
from app.models.user import User
from app.core.security.encryption import encryption_service

def update_user_database_schema():
    """Userテーブルのデータベーススキーマを更新して暗号化後のデータサイズに対応"""
    db = SessionLocal()
    
    try:
        print("🔧 Userテーブルのデータベーススキーマを更新しています...")
        
        # カラムサイズを拡張
        schema_updates = [
            "ALTER TABLE users MODIFY COLUMN email VARCHAR(500)",
            "ALTER TABLE users MODIFY COLUMN extension VARCHAR(100)",
            "ALTER TABLE users MODIFY COLUMN direct_phone VARCHAR(100)",
            "ALTER TABLE users MODIFY COLUMN mfa_totp_secret VARCHAR(500)"
        ]
        
        for update_sql in schema_updates:
            try:
                db.execute(text(update_sql))
                print(f"✅ {update_sql}")
            except Exception as e:
                print(f"⚠️  {update_sql} - {str(e)}")
                # 既に更新済みの場合などは続行
        
        db.commit()
        print("✅ Userテーブルのデータベーススキーマの更新が完了しました")
        
    except Exception as e:
        print(f"❌ スキーマ更新中にエラーが発生: {str(e)}")
        db.rollback()
    finally:
        db.close()

def migrate_user_encryption():
    """既存のUserデータを暗号化する"""
    db = SessionLocal()
    
    try:
        print("🔐 Userデータの暗号化マイグレーションを開始します...")
        
        # 全ユーザーを取得
        users = db.query(User).all()
        print(f"📊 対象ユーザー数: {len(users)}")
        
        migrated_count = 0
        error_count = 0
        
        for user in users:
            try:
                print(f" ユーザー {user.id} を処理中...")
                
                # 既に暗号化されているかチェック
                if is_user_already_encrypted(user):
                    print(f"✅ {user.id}: 既に暗号化済み")
                    continue
                
                # 機密データを暗号化
                encrypt_user_data(user)
                
                # データベースを更新
                db.add(user)
                migrated_count += 1
                
                print(f"🔒 {user.id}: 暗号化完了")
                
            except Exception as e:
                error_count += 1
                print(f"❌ {user.id}: 暗号化エラー - {str(e)}")
                print(f"   エラーの詳細: {type(e).__name__}")
                continue
        
        # 変更をコミット
        db.commit()
        
        print(f"\n Userマイグレーション完了!")
        print(f"✅ 成功: {migrated_count}件")
        print(f"❌ エラー: {error_count}件")
        
    except Exception as e:
        print(f"❌ マイグレーション中にエラーが発生: {str(e)}")
        print(f"   エラーの詳細: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

def is_user_already_encrypted(user: User) -> bool:
    """既に暗号化されているかチェック"""
    try:
        # メールアドレスが暗号化されているかチェック
        if user.email and not user.email.startswith('gAAAAA'):
            return False
        return True
    except:
        return False

def encrypt_user_data(user: User):
    """ユーザーの機密データを暗号化"""
    try:
        # メールアドレス
        if user.email and not user.email.startswith('gAAAAA'):
            print(f"   メールアドレスを暗号化中: {user.email[:20]}...")
            user.email = encryption_service.encrypt_data(user.email)
        
        # 内線番号
        if user.extension and not user.extension.startswith('gAAAAA'):
            print(f"   内線番号を暗号化中: {user.extension}")
            user.extension = encryption_service.encrypt_data(user.extension)
        
        # 直通番号
        if user.direct_phone and not user.direct_phone.startswith('gAAAAA'):
            print(f"   直通番号を暗号化中: {user.direct_phone}")
            user.direct_phone = encryption_service.encrypt_data(user.direct_phone)
        
        # MFA秘密鍵
        if user.mfa_totp_secret and not user.mfa_totp_secret.startswith('gAAAAA'):
            print(f"   MFA秘密鍵を暗号化中: {user.mfa_totp_secret[:20]}...")
            user.mfa_totp_secret = encryption_service.encrypt_data(user.mfa_totp_secret)
        
        # MFAバックアップコード（安全な処理）
        if user.mfa_backup_codes:
            print(f"   MFAバックアップコードを処理中...")
            try:
                # JSONデータの安全な処理
                if isinstance(user.mfa_backup_codes, str):
                    # 文字列の場合はJSONとして解析を試行
                    try:
                        codes = json.loads(user.mfa_backup_codes)
                        if isinstance(codes, list):
                            encrypted_codes = []
                            for code in codes:
                                if isinstance(code, str) and not code.startswith('gAAAAA'):
                                    encrypted_codes.append(encryption_service.encrypt_data(code))
                                else:
                                    encrypted_codes.append(str(code))
                            user.mfa_backup_codes = encrypted_codes
                    except json.JSONDecodeError:
                        # JSONとして解析できない場合は、そのまま暗号化
                        user.mfa_backup_codes = encryption_service.encrypt_data(user.mfa_backup_codes)
                elif isinstance(user.mfa_backup_codes, list):
                    # リストの場合は個別に暗号化
                    encrypted_codes = []
                    for code in user.mfa_backup_codes:
                        if isinstance(code, str) and not code.startswith('gAAAAA'):
                            encrypted_codes.append(encryption_service.encrypt_data(code))
                        else:
                            encrypted_codes.append(str(code))
                    user.mfa_backup_codes = encrypted_codes
                else:
                    # その他の型の場合は文字列に変換して暗号化
                    user.mfa_backup_codes = encryption_service.encrypt_data(str(user.mfa_backup_codes))
            except Exception as e:
                print(f"     MFAバックアップコード処理エラー: {str(e)}")
                # エラーが発生した場合は、元のデータをそのまま保持
                pass
                
    except Exception as e:
        print(f"   暗号化処理エラー: {str(e)}")
        raise

if __name__ == "__main__":
    # 1. まずデータベーススキーマを更新
    update_user_database_schema()
    
    # 2. 次にデータの暗号化を実行
    migrate_user_encryption()
