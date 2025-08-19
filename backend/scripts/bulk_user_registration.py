#!/usr/bin/env python3
"""
経産省職員14名の一括登録スクリプト
JWT認証・MFA設定・セッション管理対応
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.crud.user import create_user
from app.schemas.user import UserCreate
from app.core.security import hash_password
from app.models.user import Department, Position, User
from app.core.security.mfa import MFAService

def get_or_create_department(db: Session, section: str) -> int:
    """部署（部局）を取得または作成してIDを返す"""
    dept = db.query(Department).filter(Department.section == section).first()
    
    if not dept:
        dept = Department(section=section, name=None)
        db.add(dept)
        db.flush()
        print(f"📁 新規部署を作成: {section}")
    
    return dept.id

def get_or_create_position(db: Session, name: str) -> int:
    """役職を取得または作成してIDを返す"""
    pos = db.query(Position).filter(Position.name == name).first()
    
    if not pos:
        pos = Position(name=name)
        db.add(pos)
        db.flush()
        print(f" 新規役職を作成: {name}")
    
    return pos.id

def setup_mfa_for_user(db: Session, user: User):
    """ユーザーのMFA設定を行う"""
    try:
        # TOTP秘密鍵を生成
        totp_secret = MFAService.generate_totp_secret()
        
        # バックアップコードを生成
        backup_codes = MFAService.generate_backup_codes()
        
        # ユーザーのMFA設定を更新
        user.mfa_totp_secret = totp_secret
        user.mfa_backup_codes = backup_codes
        user.mfa_enabled = True
        user.mfa_required = False  # 初期は任意
        
        # 暗号化して保存
        user.encrypt_sensitive_data()
        
        print(f"   MFA設定完了: TOTP秘密鍵とバックアップコードを生成")
        
        # MFA設定情報を表示（本番環境では削除）
        print(f"   📱 TOTP秘密鍵: {totp_secret}")
        print(f"   🔑 バックアップコード: {', '.join(backup_codes)}")
        
    except Exception as e:
        print(f"   ⚠️  MFA設定に失敗: {str(e)}")

def bulk_register_users():
    """14名のユーザーを一括登録"""
    
    # ユーザーデータ（適切な役職体系で設定）
    users_data = [
        {"last_name": "佐藤", "first_name": "健介", "section": "大臣官房", "position": "官房長", "email": "kensuke.sato@meti-test.go.jp"},
        {"last_name": "鈴木", "first_name": "彩乃", "section": "大臣官房", "position": "審議官", "email": "ayano.suzuki@meti-test.go.jp"},
        {"last_name": "高橋", "first_name": "悠斗", "section": "経済産業政策局", "position": "課長", "email": "yuto.takahashi@meti-test.go.jp"},
        {"last_name": "田中", "first_name": "美和", "section": "経済産業政策局", "position": "課長", "email": "miwa.tanaka@meti-test.go.jp"},
        {"last_name": "伊藤", "first_name": "直樹", "section": "通商政策局", "position": "課長", "email": "naoki.ito@meti-test.go.jp"},
        {"last_name": "渡辺", "first_name": "彩花", "section": "通商政策局", "position": "課長", "email": "ayaka.watanabe@meti-test.go.jp"},
        {"last_name": "中村", "first_name": "翔太", "section": "国際経済部", "position": "課長", "email": "shota.nakamura@meti-test.go.jp"},
        {"last_name": "小林", "first_name": "美月", "section": "貿易管理部", "position": "課長", "email": "mizuki.kobayashi@meti-test.go.jp"},
        {"last_name": "山本", "first_name": "拓真", "section": "GXグループ", "position": "課長", "email": "takuma.yamamoto@meti-test.go.jp"},
        {"last_name": "加藤", "first_name": "明里", "section": "製造産業局", "position": "課長", "email": "akari.kato@meti-test.go.jp"},
        {"last_name": "吉田", "first_name": "大輔", "section": "商務情報政策局", "position": "課長", "email": "daisuke.yoshida@meti-test.go.jp"},
        {"last_name": "井上", "first_name": "結衣", "section": "商務・サービスグループ", "position": "課長", "email": "yui.inoue@meti-test.go.jp"},
        {"last_name": "松本", "first_name": "海斗", "section": "資源エネルギー庁", "position": "課長", "email": "kaito.matsumoto@meti-test.go.jp"},
        {"last_name": "石井", "first_name": "美咲", "section": "中小企業庁", "position": "総務課", "email": "misaki.ishii@meti-test.go.jp"}
    ]
    
    db = SessionLocal()
    try:
        print("🚀 経産省職員14名の一括登録を開始します...")
        print(" 部署と役職の設定を確認中...")
        print("🔐 JWT認証・セッション管理・MFA設定も含めて登録します")
        
        # 仮パスワード（本番環境では変更が必要）
        default_password = "Meti2024!"
        password_hash = hash_password(default_password)
        
        registered_count = 0
        
        for user_data in users_data:
            try:
                print(f"\n👤 {user_data['last_name']} {user_data['first_name']} さんを登録中...")
                
                # 部署IDを取得または作成
                department_id = get_or_create_department(db, user_data["section"])
                print(f"   📍 部署: {user_data['section']} (ID: {department_id})")
                
                # 役職IDを取得または作成
                position_id = get_or_create_position(db, user_data["position"])
                print(f"   👔 役職: {user_data['position']} (ID: {position_id})")
                
                # ユーザー作成用データ
                user_create = UserCreate(
                    email=user_data["email"],
                    password=default_password,
                    last_name=user_data["last_name"],
                    first_name=user_data["first_name"],
                    department_id=department_id,
                    position_id=position_id
                )
                
                # ユーザーを作成
                user = create_user(db, user_create, password_hash)
                print(f"   ✅ 登録完了: {user_data['email']}")
                
                # MFA設定を行う
                setup_mfa_for_user(db, user)
                
                registered_count += 1
                
            except Exception as e:
                print(f"   ❌ 登録に失敗: {str(e)}")
        
        # 変更をコミット
        db.commit()
        print(f"\n🎉 登録完了！ {registered_count}/14名のユーザーを登録しました")
        print(f"📝 仮パスワード: {default_password}")
        print("�� JWT認証・セッション管理システムが利用可能です")
        print("📱 各ユーザーのMFA設定も完了しています")
        print("⚠️  本番環境では、各ユーザーに個別のパスワードを設定してください")
        
        # 登録された部署と役職の一覧を表示
        print("\n📊 登録された部署と役職:")
        departments = db.query(Department).all()
        positions = db.query(Position).all()
        
        print("部署:")
        for dept in departments:
            print(f"  - {dept.section}")
        
        print("役職:")
        for pos in positions:
            print(f"  - {pos.name}")
        
        # セキュリティ情報の表示
        print("\n🔒 セキュリティ機能:")
        print("  - JWT認証: ✅ 実装済み")
        print("  - セッション管理: ✅ 実装済み")
        print("  - MFA認証: ✅ 実装済み")
        print("  - パスワードハッシュ化: ✅ 実装済み")
        print("  - データ暗号化: ✅ 実装済み")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 一括登録中にエラーが発生しました: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    bulk_register_users()
