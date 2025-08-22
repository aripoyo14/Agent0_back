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
# 継続的検証システムのインポートを追加
from app.core.security.continuous_verification.service import ContinuousVerificationService
from app.core.security.session.manager import session_manager
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid

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

# 継続的検証サービスの初期化関数
def get_continuous_verification_service(db: Session):
    return ContinuousVerificationService(db)

# セッションID生成関数
def generate_session_id() -> str:
    return str(uuid.uuid4())

# 新規外部有識者登録用のエンドポイント
@router.post("/register", response_model=ExpertRegisterResponse)
async def register_expert(
    http_request: Request,
    expert_data: ExpertCreate, 
    invitation_code: Optional[str] = None,
    db: Session = Depends(get_db),
    rate_limit_check: bool = Depends(check_expert_register_rate_limit)
):
    """新規エキスパート登録（招待コード対応・MFA必須・継続的検証統合）"""
    
    # 監査サービスと継続的検証サービスの初期化
    audit_service = AuditService(db)
    cv_service = get_continuous_verification_service(db)
    
    # セッションIDを生成（登録プロセス用）
    session_id = generate_session_id()
    
    try:
        # 継続的検証によるリスク評価（登録前）
        async with cv_service.get_session_monitor(session_id):
            # 登録リクエストのリスク監視
            await cv_service.monitor_session(
                session_id=session_id,
                request=http_request,
                user_type="expert_registration"
            )
        
        # 招待コードが提供された場合、検証と使用を行う
        issuer_info = None
        if invitation_code:
            print(f"🔍 招待コード受信: {invitation_code}")
            
            is_valid, code_info, message = InvitationCodeService.validate_code(invitation_code)
            print(f"🔍 招待コード検証結果: {is_valid}, {message}")
            
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"招待コードが無効です: {message}"
                )
            
            print(f"🔍 招待コード情報: {code_info}")
            
            # 発行者情報を取得
            issuer_info = InvitationCodeService.get_issuer_info(
                db, 
                code_info["issuer_id"], 
                code_info["issuer_type"]
            )
            print(f"🔍 発行者情報: {issuer_info}")
            
            if not issuer_info:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="招待コードの発行者情報が取得できません"
                )
            
            # 招待コードを使用（検証成功後）
            InvitationCodeService.use_code(invitation_code, expert_data.email)
            print(f"🔍 招待コード使用完了: {invitation_code}")
        
        # 1. パスワードをハッシュ化
        hashed_password = hash_password(expert_data.password)
        
        # 2. 基本エキスパート作成
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

        
        # 4. MFA設定
        totp_secret = MFAService.generate_totp_secret()
        backup_codes = MFAService.generate_backup_codes()
        
        # 5. MFA関連情報をデータベースに保存
        expert.mfa_totp_secret = totp_secret
        expert.mfa_backup_codes = backup_codes
        expert.mfa_required = True
        expert.account_active = False  # MFA設定完了まで無効
        expert.registration_status = "pending_mfa"  # 登録状態を設定
        
        # 6. データベースに保存（コミット）
        db.commit()  # flush()からcommit()に変更
        
        # 7. 継続的検証による登録後のリスク評価
        await cv_service.monitor_session(
            session_id=session_id,
            request=http_request,
            user_id=str(expert.id),
            user_type="expert"
        )
        
        # 8. 成功時の監査ログ
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
                "invited_by": issuer_info["name"] if issuer_info else None,
                "session_id": session_id,
                "risk_monitoring_enabled": True
            }
        )
        
        # 9. MFA設定用の情報を返す
        return {
            "message": "エキスパート登録完了。MFA設定が必要です。",
            "user_id": str(expert.id),
            "mfa_setup_required": True,
            "totp_secret": totp_secret,
            "backup_codes": backup_codes,
            "qr_code_url": f"/api/mfa/setup/{expert.id}",
            "next_step": "complete_mfa_setup",
            "invitation_code_used": invitation_code is not None,
            "invited_by": issuer_info["name"] if issuer_info else None,
            "session_id": session_id,
            "security_monitoring": "enabled"
        }
        
    except Exception as e:
        # エラー時はロールバック
        db.rollback()
        
        # 継続的検証によるエラー時のリスク記録
        try:
            await cv_service.monitor_session(
                session_id=session_id,
                request=http_request,
                user_type="expert_registration_error"
            )
        except Exception as cv_error:
            # 継続的検証のエラーは記録するが、メイン処理には影響しない
            pass
        
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
                "invitation_code": invitation_code,
                "session_id": session_id
            }
        )
        raise

# 外部有識者ログイン用のエンドポイント
@router.post("/login", response_model=ExpertLoginResponse)
async def login_expert(
    request: ExpertLoginRequest, 
    http_request: Request,
    db: Session = Depends(get_db)
):
    """エキスパートログイン（継続的検証統合）"""
    
    # 継続的検証サービスの初期化（エラーハンドリング強化）
    cv_service = None
    session_id = None
    
    try:
        cv_service = get_continuous_verification_service(db)
        session_id = generate_session_id()
        print(f"🔍 継続的検証サービス初期化完了: {cv_service}")
        print(f"🔍 セッションID生成: {session_id}")
        
    except Exception as cv_init_error:
        print(f"⚠️ 継続的検証サービス初期化エラー: {cv_init_error}")
        import traceback
        traceback.print_exc()
        # 継続的検証が失敗してもログイン処理は続行
    
    try:
        # ログイン前のリスク評価（エラーハンドリング強化）
        if cv_service and session_id:
            try:
                async with cv_service.get_session_monitor(session_id):
                    await cv_service.monitor_session(
                        session_id=session_id,
                        request=http_request,
                        user_type="expert_login_attempt"
                    )
                print(f"🔍 ログイン前リスク評価完了")
            except Exception as cv_monitor_error:
                print(f"⚠️ ログイン前リスク評価エラー: {cv_monitor_error}")
                import traceback
                traceback.print_exc()
        
        # メールでexpertを検索
        expert = get_expert_by_email(db, email=request.email)
        print(f"🔍 エキスパート検索結果: {expert.id if expert else 'Not found'}")
        
        # expertが存在しない or パスワードが間違っている場合はエラー
        if not expert or not verify_password(request.password, expert.password_hash):
            # ログイン失敗時のリスク記録
            if cv_service and session_id:
                try:
                    await cv_service.monitor_session(
                        session_id=session_id,
                        request=http_request,
                        user_type="expert_login_failure"
                    )
                    print(f" ログイン失敗時のリスク記録完了")
                except Exception as cv_error:
                    print(f"⚠️ ログイン失敗時のリスク記録エラー: {cv_error}")
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="メールアドレスまたはパスワードが正しくありません。",
            )

        # ログイン成功時のリスク評価
        if cv_service and session_id:
            try:
                await cv_service.monitor_session(
                    session_id=session_id,
                    request=http_request,
                    user_id=str(expert.id),
                    user_type="expert"
                )
                print(f" ログイン成功時のリスク評価完了")
            except Exception as cv_error:
                print(f"⚠️ ログイン成功時のリスク評価エラー: {cv_error}")
                import traceback
                traceback.print_exc()

        # JWTトークンを発行
        token_data = {
            "sub": str(expert.id),
            "role": expert.role,
            "user_type": "expert"
        }
        
        if session_id:
            token_data["session_id"] = session_id
        
        token = create_access_token(token_data)
        print(f"🔍 JWTトークン発行完了: {token[:20]}...")
        print(f"🔍 トークンに含まれるセッションID: {session_id}")

        # セッション管理に登録（エラーハンドリング強化）
        if session_id:
            try:
                print(f"🔍 セッション管理登録開始: session_id={session_id}")
                print(f"🔍 セッション管理オブジェクト: {session_manager}")
                print(f" セッション管理オブジェクトの型: {type(session_manager)}")
                
                # セッション管理の現在の状態を確認
                print(f"🔍 現在のアクティブセッション数: {len(session_manager.active_sessions)}")
                print(f"🔍 現在のアクティブセッション: {list(session_manager.active_sessions.keys())}")
                
                # セッション作成の詳細情報
                session_create_data = {
                    "user_id": str(expert.id),
                    "user_type": "expert",
                    "permissions": ["read", "write"],  # デフォルト権限
                    "ip_address": cv_service._get_client_ip(http_request) if cv_service else "unknown",
                    "user_agent": http_request.headers.get("user-agent")
                }
                print(f"🔍 セッション作成データ: {session_create_data}")
                
                # セッション管理への登録
                session_manager.create_session(
                    session_id=session_id,
                    user_id=str(expert.id),
                    user_type="expert",
                    metadata={
                        "login_time": datetime.now(timezone.utc).isoformat(),
                        "ip_address": cv_service._get_client_ip(http_request) if cv_service else "unknown",
                        "user_agent": http_request.headers.get("user-agent")
                    }
                )
                print(f"🔍 セッション管理登録完了")
                print(f" 登録後のアクティブセッション数: {len(session_manager.active_sessions)}")
                print(f"🔍 登録後のアクティブセッション: {list(session_manager.active_sessions.keys())}")
                
                # 登録されたセッションの確認
                if session_id in session_manager.active_sessions:
                    print(f"🔍 セッション登録確認: {session_manager.active_sessions[session_id]}")
                else:
                    print(f"⚠️ セッション登録失敗: {session_id} が見つかりません")
                    print(f"⚠️ 利用可能なセッション: {list(session_manager.active_sessions.keys())}")
                
            except Exception as session_error:
                print(f"⚠️ セッション管理エラー: {session_error}")
                import traceback
                traceback.print_exc()
                # セッション管理が失敗してもログイン処理は続行

        # 暗号化されたフィールドを復号化してからレスポンスを返す
        expert_response = ExpertOut(
            id=expert.id,
            last_name=expert.last_name,
            first_name=expert.first_name,
            company_id=expert.company_id,
            department=expert.department,
            email=expert.get_decrypted_email(),  # 暗号化されたメールアドレスを復号化
            created_at=expert.created_at,
            updated_at=expert.updated_at
        )

        # トークンとexpert情報をレスポンスとして返す
        print(f"🔍 ログイン処理完了、レスポンス返却")
        return ExpertLoginResponse(
            access_token=token,
            expert=expert_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ログイン処理エラー詳細: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 予期しないエラー時のリスク記録
        if cv_service and session_id:
            try:
                await cv_service.monitor_session(
                    session_id=session_id,
                    request=http_request,
                    user_type="expert_login_error"
                )
            except Exception as cv_error:
                print(f"⚠️ エラー時のリスク記録エラー: {cv_error}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ログイン処理中にエラーが発生しました: {str(e)}"
        )

# 現在ログイン中の外部有識者のプロフィール情報取得用のエンドポイント
@router.get("/me", response_model=ExpertOut)
async def get_expert_profile(
    token: str = Depends(HTTPBearer()), 
    http_request: Request = None,
    db: Session = Depends(get_db)
):
    """エキスパートプロフィール取得（継続的検証統合）"""
    
    # 継続的検証サービスの初期化
    cv_service = get_continuous_verification_service(db)
    
    try:
        payload = decode_access_token(token.credentials)
        
        # デバッグ用：トークンの内容を詳細にログ出力
        print(f"🔍 トークンペイロード: {payload}")
        print(f"🔍 利用可能なフィールド: {list(payload.keys())}")
        
        expert_id = payload.get("sub")
        role = payload.get("role")
        user_type = payload.get("user_type")
        session_id = payload.get("session_id")
        
        print(f"🔍 抽出された値:")
        print(f"   - expert_id: {expert_id}")
        print(f"   - role: {role}")
        print(f"   - user_type: {user_type}")
        print(f"   - session_id: {session_id}")
        
        # トークン検証の条件を修正
        if not expert_id or user_type != "expert":
            print(f"❌ トークン検証失敗:")
            print(f"   - expert_id存在: {bool(expert_id)}")
            print(f"   - user_type一致: {user_type == 'expert'}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なトークンです。"
            )
        
        print(f"✅ トークン検証成功")
        
        # セッションの有効性確認
        if session_id and not session_manager.is_session_valid(session_id):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="セッションが無効です。再ログインしてください。"
            )
        
        # 継続的検証によるリスク評価
        if session_id and http_request:
            await cv_service.monitor_session(
                session_id=session_id,
                request=http_request,
                user_id=expert_id,
                user_type="expert"
            )
            
        expert = db.query(Expert).filter(Expert.id == expert_id).first()
        if not expert:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザーが見つかりません。"
            )
            
        return expert
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 予期しないエラー: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # エラー時のリスク記録
        if session_id and http_request:
            try:
                await cv_service.monitor_session(
                    session_id=session_id,
                    request=http_request,
                    user_type="expert_profile_error"
                )
            except Exception as cv_error:
                pass
        
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

# 新しいエンドポイント: セッション状態確認
@router.get("/session/status")
async def get_session_status(
    token: str = Depends(HTTPBearer()),
    db: Session = Depends(get_db)
):
    """現在のセッション状態とリスク情報を取得"""
    
    try:
        payload = decode_access_token(token.credentials)
        session_id = payload.get("session_id")
        
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="セッションIDが含まれていません"
            )
        
        # セッション状態確認（本来の実装）
        session_info = session_manager.get_session_info(session_id)
        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="セッションが見つかりません"
            )
        
        # 継続的検証サービスの初期化
        cv_service = get_continuous_verification_service(db)
        
        # 最新のリスク情報を取得（データベースから）
        # 実際の実装では、RiskScoreテーブルから最新の記録を取得
        
        return {
            "session_id": session_id,
            "user_id": session_info.get("user_id"),
            "user_type": session_info.get("user_type"),
            "created_at": session_info.get("created_at"),
            "last_activity": session_info.get("last_activity"),
            "status": "active" if session_manager.is_session_valid(session_id) else "inactive",
            "security_monitoring": "enabled",
            "risk_assessment": "continuous",
            "session_details": session_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"セッション状態取得中にエラー: {str(e)}"
        )

# セッション終了エンドポイント
@router.post("/logout")
async def logout_expert(
    token: str = Depends(HTTPBearer()),
    db: Session = Depends(get_db)
):
    """エキスパートログアウト（セッション終了・継続的検証記録）"""
    
    try:
        payload = decode_access_token(token.credentials)
        session_id = payload.get("session_id")
        
        if session_id:
            # セッションを無効化
            session_manager.invalidate_session(session_id)
            
            # ログアウト時の監査ログ
            audit_service = AuditService(db)
            audit_service.log_event(
                event_type=AuditEventType.USER_LOGOUT,
                resource="auth",
                action="logout",
                success=True,
                details={
                    "session_id": session_id,
                    "user_type": "expert"
                }
            )
        
        return {"message": "ログアウト完了"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ログアウト処理中にエラー: {str(e)}"
        )
