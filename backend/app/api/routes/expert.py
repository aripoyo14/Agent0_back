from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.expert import ExpertCreate, ExpertOut, ExpertLoginRequest, ExpertLoginResponse
from app.crud.expert import create_expert
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.core.jwt import create_access_token, decode_access_token
from fastapi.security import HTTPBearer
from app.models.expert import Expert
from app.crud.expert import get_expert_by_email
from app.core.security import verify_password


# FastAPIのルーターを初期化
router = APIRouter(prefix="/experts", tags=["Experts"])

# DBセッションをリクエストごとに生成・提供する関数
def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()  # リクエスト処理が終わると、自動的にセッションをクローズ


""" ------------------------
 外部有識者関連エンドポイント
------------------------ """            

# 新規外部有識者登録用のエンドポイント
@router.post("/register", response_model=ExpertOut)
def register_expert(expert_in: ExpertCreate, db: Session = Depends(get_db)):

    # パスワードをハッシュ化
    hashed_pw = hash_password(expert_in.password)

    # CRUD層の関数を使ってDBに外部有識者情報を保存
    expert = create_expert(db=db, expert_in=expert_in, password_hash=hashed_pw)

    # 保存された 外部有識者情報 （ExpertOut） を返す
    return expert

# 外部有識者ログイン用のエンドポイント
@router.post("/login", response_model=ExpertLoginResponse)
def login_expert(request: ExpertLoginRequest, db: Session = Depends(get_db)):
    
    # メールでexpertを検索
    expert = get_expert_by_email(db, email=request.email)
    
    # expertが存在しない or パスワードが間違っている場合はエラー
    if not expert or not verify_password(request.password, expert.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません。",
        )

    # JWTトークンを発行（ペイロードに expert.id と expert.role を含める）
    token = create_access_token({
        "sub": str(expert.id),
        "role": expert.role,
        "type": "expert"
    })

    # トークンとexpert情報をレスポンスとして返す
    return ExpertLoginResponse(
        access_token=token,
        expert=expert
    )

# 現在ログイン中の外部有識者のプロフィール情報取得用のエンドポイント
@router.get("/me", response_model=ExpertOut)
def get_expert_profile(token: str = Depends(HTTPBearer()), db: Session = Depends(get_db)):

    try:
        payload = decode_access_token(token.credentials)
        expert_id = payload.get("sub")
        role = payload.get("role")
        token_type = payload.get("type")
        
        if not expert_id or role != "expert" or token_type != "expert":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なトークンです。"
            )
            
        expert = db.query(Expert).filter(Expert.id == expert_id).first()
        if not expert:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザーが見つかりません。"
            )
            
        return expert
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証に失敗しました。"
        )
