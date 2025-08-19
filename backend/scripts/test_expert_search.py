#!/usr/bin/env python3
"""
Expertデータの検索と認証処理をテストするスクリプト
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.db.session import SessionLocal
from app.models.expert import Expert
from app.crud.expert import get_expert_by_email
from app.core.security import verify_password

def test_expert_search():
    """Expertデータの検索をテスト"""
    print("�� Expertデータの検索テストを開始します...")
    
    db = SessionLocal()
    try:
        # 1. データベース内のExpertデータの確認
        print("\n📊 データベース内のExpertデータ:")
        experts = db.query(Expert).all()
        print(f"   総数: {len(experts)}件")
        
        for i, expert in enumerate(experts):
            print(f"\n📝 Expert {i+1}:")
            print(f"   ID: {expert.id}")
            print(f"   名前: {expert.last_name} {expert.first_name}")
            print(f"   メールアドレス: {expert.email}")
            print(f"   パスワードハッシュ: {expert.password_hash[:50]}..." if expert.password_hash else "   パスワードハッシュ: なし")
            print(f"   アカウント状態: {expert.account_active}")
            print(f"   登録状態: {expert.registration_status}")
        
        # 2. 特定のメールアドレスでの検索テスト
        print("\n🔍 特定のメールアドレスでの検索テスト:")
        test_email = "hiroshimori@hotmail.com"
        print(f"   検索対象: {test_email}")
        
        found_expert = get_expert_by_email(db, test_email)
        
        if found_expert:
            print(f"   ✅ Expertが見つかりました:")
            print(f"      ID: {found_expert.id}")
            print(f"      名前: {found_expert.last_name} {found_expert.first_name}")
            print(f"      メールアドレス: {found_expert.email}")
            print(f"      パスワードハッシュ: {found_expert.password_hash[:50]}..." if found_expert.password_hash else "      パスワードハッシュ: なし")
            
            # 3. 復号化テスト
            print(f"\n🔐 復号化テスト:")
            try:
                decrypted_email = found_expert.get_decrypted_email()
                print(f"   復号化されたメールアドレス: {decrypted_email}")
                
                if decrypted_email == test_email:
                    print("   ✅ メールアドレスの復号化と比較が成功")
                else:
                    print(f"   ❌ メールアドレスの比較が失敗: 期待値={test_email}, 実際={decrypted_email}")
                    
            except Exception as e:
                print(f"   ❌ 復号化エラー: {str(e)}")
                print(f"   エラーの型: {type(e)}")
            
            # 4. オブジェクトの属性確認
            print(f"\n🔍 Expertオブジェクトの属性確認:")
            print(f"   hasattr(expert, 'email'): {hasattr(found_expert, 'email')}")
            print(f"   expert.email is None: {found_expert.email is None}")
            print(f"   type(expert.email): {type(found_expert.email)}")
            
            if hasattr(found_expert, 'email') and found_expert.email is not None:
                print("   ✅ email属性は正常に存在します")
            else:
                print("   ❌ email属性に問題があります")
                
        else:
            print(f"   ❌ Expertが見つかりませんでした")
            
            # 5. 検索処理の詳細確認
            print(f"\n🔍 検索処理の詳細確認:")
            all_experts = db.query(Expert).all()
            for expert in all_experts:
                try:
                    decrypted_email = expert.get_decrypted_email()
                    print(f"   Expert {expert.last_name} {expert.first_name}: {decrypted_email}")
                    if decrypted_email == test_email:
                        print(f"   ✅ このExpertが対象です！")
                except Exception as e:
                    print(f"   Expert {expert.last_name} {expert.first_name}: 復号化エラー - {str(e)}")
    
    except Exception as e:
        print(f"❌ テスト中にエラーが発生: {str(e)}")
        print(f"エラーの型: {type(e)}")
    finally:
        db.close()
    
    print("\n�� Expertデータの検索テストが完了しました")

if __name__ == "__main__":
    test_expert_search()
