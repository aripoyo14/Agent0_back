from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.schemas.expert import ExpertCreate, ExpertOut, ExpertLoginRequest, ExpertLoginResponse, ExpertInsightsOut, ExpertRegisterResponse
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.core.security.jwt import create_access_token, decode_access_token
from fastapi.security import HTTPBearer
from app.models.expert import Expert
from app.crud.expert import get_expert_by_email, get_expert_insights, create_expert
from app.core.security import verify_password
from app.core.security.audit import AuditService, AuditEventType
from app.core.security.rbac.service import RBACService
from app.core.security.mfa import MFAService
from app.core.security.rate_limit.dependencies import check_expert_register_rate_limit



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
@router.post("/register", response_model=ExpertRegisterResponse)
def register_expert(
    http_request: Request,
    expert_data: ExpertCreate, 
    db: Session = Depends(get_db),
    rate_limit_check: bool = Depends(check_expert_register_rate_limit)
):
    """新規エキスパート登録（MFA必須）"""
    
    # 監査サービスの初期化
    audit_service = AuditService(db)
    
    try:
        # 1. パスワードをハッシュ化
        hashed_password = hash_password(expert_data.password)
        
        # 2. 基本エキスパート作成（パスワードハッシュを渡す）
        expert = create_expert(db, expert_data, hashed_password)
        
        # 3. MFA設定用の秘密鍵・バックアップコード生成
        totp_secret = MFAService.generate_totp_secret()
        backup_codes = MFAService.generate_backup_codes()
        
        # 4. MFA関連情報をデータベースに保存
        expert.mfa_totp_secret = totp_secret
        expert.mfa_backup_codes = backup_codes
        expert.mfa_required = True
        expert.account_active = False  # MFA設定完了まで無効
        expert.registration_status = "pending_mfa"  # 登録状態を設定
        
        # 5. 一時的な保存（MFA設定完了まで正式登録ではない）
        db.flush()  # コミットせずにフラッシュ
        
        # 6. 成功時の監査ログ
        audit_service.log_event(
            event_type=AuditEventType.EXPERT_REGISTER_SUCCESS,
            user_id=str(expert.id),
            user_type="expert",
            resource="auth",
            action="register",
            success=True,
            request=http_request,
            details={
                "email": expert_data.email,
                "mfa_required": True,
                "account_status": "pending_mfa"
            }
        )
        
        # 7. MFA設定用の情報を返す
        return {
            "message": "エキスパート登録完了。MFA設定が必要です。",
            "user_id": str(expert.id),
            "mfa_setup_required": True,
            "totp_secret": totp_secret,
            "backup_codes": backup_codes,
            "qr_code_url": f"/api/mfa/setup/{expert.id}",
            "next_step": "complete_mfa_setup"
        }
        
    except Exception as e:
        # エラー時はロールバック
        db.rollback()
        
        # エラー時の監査ログ
        audit_service.log_event(
            event_type=AuditEventType.EXPERT_REGISTER_FAILURE,
            resource="auth",
            action="register",
            success=False,
            request=http_request,
            details={
                "email": expert_data.email,
                "error": str(e)
            }
        )
        raise

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
        "user_type": "expert"
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


# エキスパートの活動インサイト取得
@router.get("/{expert_id}/insights", response_model=ExpertInsightsOut)
def get_insights(expert_id: str, db: Session = Depends(get_db)):
    try:
        data = get_expert_insights(db, expert_id)
        if not data:
            raise HTTPException(status_code=404, detail="対象の外部有識者データが見つかりません")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"インサイト取得中にエラー: {str(e)}")
