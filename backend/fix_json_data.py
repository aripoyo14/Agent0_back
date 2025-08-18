#!/usr/bin/env python3
"""
データベース内の不正なJSONデータを修正するスクリプト
"""
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import SessionLocal

def fix_json_data():
    """データベース内の不正なJSONデータを修正"""
    db = SessionLocal()
    
    try:
        print("�� データベース内の不正なJSONデータを修正しています...")
        
        # 1. 不正なJSONデータを持つレコードを確認
        print("�� 不正なJSONデータを持つレコードを確認中...")
        
        # usersテーブルのmfa_backup_codesフィールドを確認
        result = db.execute(text("SELECT id, mfa_backup_codes FROM users WHERE mfa_backup_codes IS NOT NULL"))
        users_with_backup_codes = result.fetchall()
        
        print(f"�� mfa_backup_codesフィールドを持つユーザー数: {len(users_with_backup_codes)}")
        
        fixed_count = 0
        for user_id, backup_codes in users_with_backup_codes:
            try:
                # JSONとして解析を試行
                if backup_codes:
                    print(f"  ユーザー {user_id}: {backup_codes[:50]}...")
                    
                    # 不正なデータをNULLに設定
                    db.execute(
                        text("UPDATE users SET mfa_backup_codes = NULL WHERE id = :user_id"),
                        {"user_id": user_id}
                    )
                    fixed_count += 1
                    print(f"    ✅ 修正完了")
                    
            except Exception as e:
                print(f"    ❌ 修正エラー: {str(e)}")
        
        # 2. expertsテーブルのmfa_backup_codesフィールドも確認
        result = db.execute(text("SELECT id, mfa_backup_codes FROM experts WHERE mfa_backup_codes IS NOT NULL"))
        experts_with_backup_codes = result.fetchall()
        
        print(f"�� mfa_backup_codesフィールドを持つエキスパート数: {len(experts_with_backup_codes)}")
        
        for expert_id, backup_codes in experts_with_backup_codes:
            try:
                if backup_codes:
                    print(f"  エキスパート {expert_id}: {backup_codes[:50]}...")
                    
                    # 不正なデータをNULLに設定
                    db.execute(
                        text("UPDATE experts SET mfa_backup_codes = NULL WHERE id = :expert_id"),
                        {"expert_id": expert_id}
                    )
                    fixed_count += 1
                    print(f"    ✅ 修正完了")
                    
            except Exception as e:
                print(f"    ❌ 修正エラー: {str(e)}")
        
        # 変更をコミット
        db.commit()
        
        print(f"\n✅ JSONデータ修正完了!")
        print(f"修正されたレコード数: {fixed_count}件")
        
    except Exception as e:
        print(f"❌ JSONデータ修正中にエラーが発生: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_json_data()
