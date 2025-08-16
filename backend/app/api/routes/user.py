# app/api/routes/user.py
"""
 - ユーザー登録APIルートを定義するモジュール。
 - 主に FastAPI を通じて HTTP リクエスト（POST /register）を受け取り、
   バリデーション、パスワードのハッシュ化、DB登録処理などを行う。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserOut, UserLoginRequest, UserLoginResponse, RoleUpdateRequest
from app.crud.user import create_user, get_user_by_email
from app.core.security import hash_password, verify_password
from app.core.security.jwt import create_access_token, decode_access_token
from fastapi.security import HTTPBearer
from app.db.session import SessionLocal
from app.services.qr_code import QRCodeService
from app.models.user import User

# RBAC関連のインポート
from app.core.security.rbac.decorators import require_user_permissions
from app.core.security.rbac.permissions import Permission
from app.core.security.rbac.service import RBACService


# FastAPIのルーターを初期化
router = APIRouter(prefix="/users", tags=["Users"])

# DBセッションをリクエストごとに生成・提供する関数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # リクエスト処理が終わると、自動的にセッションをクローズ


""" ------------------------
 ユーザー関連エンドポイント
------------------------ """

# 新規ユーザー登録用のエンドポイント
@router.post("/register", response_model=UserOut)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):

    # パスワードをハッシュ化
    hashed_pw = hash_password(user_in.password)

    # CRUD層の関数を使ってDBにユーザー情報を保存
    user = create_user(db=db, user_in=user_in, password_hash=hashed_pw)

    # 保存された ユーザー情報 （UserOut） を返す
    return user

# ユーザーログイン用のエンドポイント
@router.post("/login", response_model=UserLoginResponse)
def login_user(request: UserLoginRequest, db: Session = Depends(get_db)):

    # メールでユーザーを検索
    user = get_user_by_email(db, email=request.email)
    
    # ユーザーが存在しない or パスワードが間違っている場合はエラー
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません。",
        )

    # JWTトークンを発行
    token = create_access_token({
        "sub": str(user.id),
        "role": "user",
        "user_type": "user"
    })

    # トークンとユーザー情報をレスポンスとして返す
    return UserLoginResponse(
        access_token=token,
        user=user
    )

# 現在ログイン中のユーザーのプロフィール情報取得用のエンドポイント
@router.get("/me", response_model=UserOut)
def get_user_profile(token: str = Depends(HTTPBearer()), db: Session = Depends(get_db)):

    try:
        payload = decode_access_token(token.credentials)
        user_id = payload.get("sub")
        role = payload.get("role")
        token_type = payload.get("user_type")

        # デバッグログを追加
        print(f"=== デバッグ情報 ===")
        print(f"Token payload: {payload}")
        print(f"user_id: {user_id}")
        print(f"role: {role}")
        print(f"token_type: {token_type}")
        print(f"==================")
        
        if not user_id or not role or not token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なトークンです。"
            )
            
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザーが見つかりません。"
            )
            
        return user
        
    except Exception as e:
        print(f"エラー詳細: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証に失敗しました。"
        )

# QRコード生成エンドポイント
@router.get("/users/{user_id}/profile-qr")
def generate_profile_qr(user_id: str):
    """ユーザープロフィール用のQRコードを生成"""
    profile_url = f"https://agent0.com/profile/{user_id}"
    qr_code = QRCodeService.generate_custom_qr(
        data=profile_url,
        box_size=8,
        border=3
    )
    return {"qr_code": qr_code, "profile_url": profile_url}

# ユーザーロール変更エンドポイント
@router.put("/{user_id}/role", response_model=UserOut)
def change_user_role(
    user_id: str,
    role_update: RoleUpdateRequest,
    current_user: User = Depends(require_user_permissions(Permission.USER_ROLE_CHANGE)),
    db: Session = Depends(get_db)   
):
    """ユーザーのロールを変更（管理者のみ）"""
    
    # 対象ユーザーを取得
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません"
        )
    
    # ロール階層チェック（自分より上位のロールには変更不可）
    if not RBACService.can_manage_user(current_user, target_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このユーザーのロールを変更する権限がありません"
        )
    
    # ロール変更
    target_user.role = role_update.role
    db.commit()
    db.refresh(target_user)
    
    return target_user