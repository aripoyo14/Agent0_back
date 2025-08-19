# app/crud/user.py
"""
 - ユーザーに関するDB操作（CRUD）を定義するモジュール。
 - 主に SQLAlchemy を通じて User モデルとデータベースをやり取りする。
"""

from sqlalchemy.orm import Session
from app.models.user import User, UsersDepartments, UsersPositions
from app.schemas.user import UserCreate
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status


# 日本時間（JST）のタイムゾーンを定義
JST = timezone(timedelta(hours=9))

# 新規ユーザーを登録する関数　（事前にハッシュ化されたパスワードを引数として受け取る)
def create_user(db: Session, user_in: UserCreate, password_hash: str) -> User:

    # 1. メールアドレスの重複チェック（既に存在していたらエラー）
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このメールアドレスは既に登録されています。"
        )
    # 2. Userモデルのインスタンスを作成
    user = User(
        id=str(uuid4()),
        email=user_in.email,
        password_hash=password_hash,
        last_name=user_in.last_name,
        first_name=user_in.first_name,
        extension=user_in.extension,
        direct_phone=user_in.direct_phone,
        created_at=datetime.now(JST),
        updated_at=datetime.now(JST)
    )

    # 3. 機密データを暗号化
    user.encrypt_sensitive_data()

    # 4. ユーザー情報をDBに保存
    db.add(user)
    db.flush()  # user.id を得るため（コミットはしない）

    # 5. 部署との中間テーブルに登録
    db.execute(
        UsersDepartments.__table__.insert().values(
            user_id=user.id,
            department_id=user_in.department_id
        )
    )

    # 6. 役職との中間テーブルに登録
    db.execute(
        UsersPositions.__table__.insert().values(
            user_id=user.id,
            position_id=user_in.position_id
        )
    )
    
    # db.commit() を削除（外側でコミットする）
    db.refresh(user)
    
    return user

# 暗号化されたメールアドレスでユーザーを検索する関数
def get_user_by_email(db: Session, email: str):
    """暗号化されたメールアドレスでユーザーを検索（最適化版）"""
    print(f"🔍 get_user_by_email開始: {email}")
    
    # まず平文のメールアドレスで検索（既存の暗号化されていないデータ）
    user = db.query(User).filter(User.email == email).first()
    if user:
        print(f"✅ 平文メールアドレスでUser発見: {user.id}")
        return user
    
    print(f"⚠️  平文メールアドレスでUser未発見、暗号化データを検索開始")
    
    # 見つからない場合、暗号化されたデータを検索
    batch_size = 100
    offset = 0
    
    while True:
        try:
            print(f"🔍 バッチ処理開始: offset={offset}, batch_size={batch_size}")
            users = db.query(User).offset(offset).limit(batch_size).all()
            print(f"📊 取得されたUser数: {len(users) if users else 0}")
            
            if not users:
                print(f"⚠️  ユーザーが見つかりませんでした")
                break
                
            for i, user in enumerate(users):
                try:
                    print(f"🔍 User {i+1} 処理開始: ID={getattr(user, 'id', 'unknown')}")
                    
                    # userオブジェクトの存在確認
                    if user is None:
                        print(f"❌  UserオブジェクトがNoneです (offset: {offset}, index: {i})")
                        continue
                        
                    # email属性の存在確認
                    if not hasattr(user, 'email'):
                        print(f"❌  User {getattr(user, 'id', 'unknown')}: email属性が存在しません")
                        continue
                        
                    if user.email is None:
                        print(f"❌  User {getattr(user, 'id', 'unknown')}: email属性がNoneです")
                        continue
                    
                    print(f" User {getattr(user, 'id', 'unknown')}: email={user.email[:50]}...")
                    
                    # メールアドレスが暗号化されているかチェック
                    if user.email.startswith('gAAAAA'):
                        try:
                            decrypted_email = user.get_decrypted_email()
                            print(f"🔐 復号化成功: {decrypted_email}")
                            if decrypted_email == email:
                                print(f"✅ 対象User発見: {user.id}")
                                return user
                        except AttributeError as e:
                            print(f"❌  User {getattr(user, 'id', 'unknown')}: email属性アクセスエラー - {str(e)}")
                            continue
                        except Exception as e:
                            print(f"❌  User {getattr(user, 'id', 'unknown')}: 復号化エラー - {str(e)}")
                            continue
                    else:
                        print(f"ℹ️  User {getattr(user, 'id', 'unknown')}: 暗号化されていないメールアドレス")
                            
                except Exception as e:
                    print(f"❌  User処理エラー (ID: {getattr(user, 'id', 'unknown')}): {str(e)}")
                    print(f"   エラーの型: {type(e)}")
                    continue
            
            offset += batch_size
            
        except Exception as e:
            print(f"❌  バッチ処理エラー (offset: {offset}): {str(e)}")
            print(f"   エラーの型: {type(e)}")
            break
    
    print(f"❌  Userが見つかりませんでした")
    return None

# 暗号化されたデータでの検索ヘルパー関数
def search_users_by_encrypted_field(db: Session, field_name: str, search_value: str):
    """暗号化されたフィールドでユーザーを検索"""
    users = db.query(User).all()
    matching_users = []
    
    for user in users:
        try:
            if field_name == "email":
                decrypted_value = user.get_decrypted_email()
            elif field_name == "extension":
                decrypted_value = user.get_decrypted_extension()
            elif field_name == "direct_phone":
                decrypted_value = user.get_decrypted_direct_phone()
            else:
                continue
            
            if search_value.lower() in decrypted_value.lower():
                matching_users.append(user)
                
        except Exception:
            # 復号化に失敗した場合はスキップ
            continue
    
    return matching_users

# 既存ユーザーの機密データを暗号化する関数
def encrypt_existing_user_data(db: Session, user_id: str):
    """既存ユーザーの機密データを暗号化"""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.encrypt_sensitive_data()
        db.add(user)
        db.commit()
        return True
    return False
