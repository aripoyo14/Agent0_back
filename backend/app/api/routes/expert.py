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
from app.services.invitation_code import InvitationCodeService
from datetime import datetime, timezone, timedelta
from typing import Optional

# 日本標準時間取得
JST = timezone(timedelta(hours=9))

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
async def register_expert(
    http_request: Request,
    expert_data: ExpertCreate, 
    invitation_code: Optional[str] = None,  # 招待コードを追加
    db: Session = Depends(get_db),
    rate_limit_check: bool = Depends(check_expert_register_rate_limit)
):
    """新規エキスパート登録（招待コード対応・MFA必須）"""
    
    # 監査サービスの初期化
    audit_service = AuditService(db)
    
    try:
        # 招待コードが提供された場合、検証と使用を行う
        issuer_info = None
        if invitation_code:
            is_valid, code_info, message = InvitationCodeService.validate_code(invitation_code)
            
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"招待コードが無効です: {message}"
                )
            
            # 招待コードを使用
            InvitationCodeService.use_code(invitation_code, expert_data.email)
            
            # 発行者情報を取得
            issuer_info = InvitationCodeService.get_issuer_info(
                db, 
                code_info["issuer_id"], 
                code_info["issuer_type"]
            )
        
        # 1. パスワードをハッシュ化
        hashed_password = hash_password(expert_data.password)
        
        # 2. 基本エキスパート作成（パスワードハッシュを渡す）
        expert = create_expert(db, expert_data, hashed_password)
        
        # business_card_image_urlを明示的に設定
        if expert_data.business_card_image_url:
            expert.business_card_image_url = expert_data.business_card_image_url
        
        # 3. 招待コード情報を保存（招待コード経由の場合）
        if invitation_code and issuer_info:
            if issuer_info["type"] == "user":
                expert.invited_by_user_id = issuer_info["id"]
            elif issuer_info["type"] == "expert":
                expert.invited_by_expert_id = issuer_info["id"]
            
            expert.invitation_code = invitation_code
            expert.invited_at = datetime.now(JST)
        
        # 4. MFA設定用の秘密鍵・バックアップコード生成
        totp_secret = MFAService.generate_totp_secret()
        backup_codes = MFAService.generate_backup_codes()
        
        # 5. MFA関連情報をデータベースに保存
        expert.mfa_totp_secret = totp_secret
        expert.mfa_backup_codes = backup_codes
        expert.mfa_required = True
        expert.account_active = False  # MFA設定完了まで無効
        expert.registration_status = "pending_mfa"  # 登録状態を設定
        
        # 6. 一時的な保存（MFA設定完了まで正式登録ではない）
        db.flush()  # コミットせずにフラッシュ
        
        # 7. 成功時の監査ログ
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
                "account_status": "pending_mfa",
                "invitation_code": invitation_code,
                "invited_by": issuer_info["name"] if issuer_info else None
            }
        )
        
        # 8. MFA設定用の情報を返す
        return {
            "message": "エキスパート登録完了。MFA設定が必要です。",
            "user_id": str(expert.id),
            "mfa_setup_required": True,
            "totp_secret": totp_secret,
            "backup_codes": backup_codes,
            "qr_code_url": f"/api/mfa/setup/{expert.id}",
            "next_step": "complete_mfa_setup",
            "invitation_code_used": invitation_code is not None,
            "invited_by": issuer_info["name"] if issuer_info else None
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
                "error": str(e),
                "invitation_code": invitation_code
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
        # 事前にエキスパートの存在を確認し、存在しない場合は404
        expert_exists = db.query(Expert).filter(Expert.id == expert_id).first()
        if not expert_exists:
            raise HTTPException(status_code=404, detail="対象の外部有識者データが見つかりません")

        data = get_expert_insights(db, expert_id)
        if not data:
            raise HTTPException(status_code=404, detail="対象の外部有識者データが見つかりません")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"インサイト取得中にエラー: {str(e)}")


@router.post("/validate-invitation-code")
def validate_invitation_code_for_registration(
    invitation_code: str,
    db: Session = Depends(get_db)
):
    """エキスパート登録用の招待コード検証"""
    
    try:
        is_valid, code_info, message = InvitationCodeService.validate_code(invitation_code)
        
        if not is_valid:
            return {
                "is_valid": False,
                "message": message
            }
        
        # 発行者情報を取得
        issuer_info = InvitationCodeService.get_issuer_info(
            db, 
            code_info["issuer_id"], 
            code_info["issuer_type"]
        )
        
        return {
            "is_valid": True,
            "message": "有効な招待コードです",
            "code_type": code_info["code_type"],
            "issuer_info": issuer_info,
            "expires_at": code_info["expires_at"].isoformat()
        }
        
    except Exception as e:
        return {
            "is_valid": False,
            "message": f"検証中にエラーが発生しました: {str(e)}"
        }
