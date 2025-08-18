#!/usr/bin/env python3
"""
既存のExpertデータを暗号化するマイグレーションスクリプト
"""
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import SessionLocal
from app.models.expert import Expert
from app.core.security.encryption import encryption_service

def update_database_schema():
    """データベーススキーマを更新して暗号化後のデータサイズに対応"""
    db = SessionLocal()
    
    try:
        print(" データベーススキーマを更新しています...")
        
        # カラムサイズを拡張
        schema_updates = [
            "ALTER TABLE experts MODIFY COLUMN email VARCHAR(500)",
            "ALTER TABLE experts MODIFY COLUMN mobile VARCHAR(100)", 
            "ALTER TABLE experts MODIFY COLUMN memo TEXT",
            "ALTER TABLE experts MODIFY COLUMN mfa_totp_secret VARCHAR(500)",
            "ALTER TABLE experts MODIFY COLUMN sansan_person_id VARCHAR(200)"
        ]
        
        for update_sql in schema_updates:
            try:
                db.execute(text(update_sql))
                print(f"✅ {update_sql}")
            except Exception as e:
                print(f"⚠️  {update_sql} - {str(e)}")
                # 既に更新済みの場合などは続行
        
        db.commit()
        print("✅ データベーススキーマの更新が完了しました")
        
    except Exception as e:
        print(f"❌ スキーマ更新中にエラーが発生: {str(e)}")
        db.rollback()
    finally:
        db.close()

def migrate_expert_encryption():
    """既存のExpertデータを暗号化する"""
    db = SessionLocal()
    
    try:
        print("🔐 Expertデータの暗号化マイグレーションを開始します...")
        
        # 全エキスパートを取得
        experts = db.query(Expert).all()
        print(f"📊 対象エキスパート数: {len(experts)}")
        
        migrated_count = 0
        error_count = 0
        
        for expert in experts:
            try:
                # 既に暗号化されているかチェック
                if is_already_encrypted(expert):
                    print(f"✅ {expert.id}: 既に暗号化済み")
                    continue
                
                # 機密データを暗号化
                encrypt_expert_data(expert)
                
                # データベースを更新
                db.add(expert)
                migrated_count += 1
                
                print(f" {expert.id}: 暗号化完了")
                
            except Exception as e:
                error_count += 1
                print(f"❌ {expert.id}: 暗号化エラー - {str(e)}")
                continue
        
        # 変更をコミット
        db.commit()
        
        print(f"\n🎉 マイグレーション完了!")
        print(f"✅ 成功: {migrated_count}件")
        print(f"❌ エラー: {error_count}件")
        
    except Exception as e:
        print(f"❌ マイグレーション中にエラーが発生: {str(e)}")
        db.rollback()
    finally:
        db.close()

def is_already_encrypted(expert: Expert) -> bool:
    """既に暗号化されているかチェック"""
    try:
        # メールアドレスが暗号化されているかチェック
        if expert.email and not expert.email.startswith('gAAAAA'):
            return False
        return True
    except:
        return False

def encrypt_expert_data(expert: Expert):
    """エキスパートの機密データを暗号化"""
    # メールアドレス
    if expert.email and not expert.email.startswith('gAAAAA'):
        expert.email = encryption_service.encrypt_data(expert.email)
    
    # 携帯電話番号
    if expert.mobile and not expert.mobile.startswith('gAAAAA'):
        expert.mobile = encryption_service.encrypt_data(expert.mobile)
    
    # メモ
    if expert.memo and not expert.memo.startswith('gAAAAA'):
        expert.memo = encryption_service.encrypt_data(expert.memo)
    
    # MFA秘密鍵
    if expert.mfa_totp_secret and not expert.mfa_totp_secret.startswith('gAAAAA'):
        expert.mfa_totp_secret = encryption_service.encrypt_data(expert.mfa_totp_secret)
    
    # MFAバックアップコード
    if expert.mfa_backup_codes:
        encrypted_codes = []
        for code in expert.mfa_backup_codes:
            if isinstance(code, str) and not code.startswith('gAAAAA'):
                encrypted_codes.append(encryption_service.encrypt_data(code))
            else:
                encrypted_codes.append(str(code))
        expert.mfa_backup_codes = encrypted_codes
    
    # SanSan個人ID
    if expert.sansan_person_id and not expert.sansan_person_id.startswith('gAAAAA'):
        expert.sansan_person_id = encryption_service.encrypt_data(expert.sansan_person_id)

if __name__ == "__main__":
    # 1. まずデータベーススキーマを更新
    update_database_schema()
    
    # 2. 次にデータの暗号化を実行
    migrate_expert_encryption()
