from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from app.schemas.invitation_code import (
    InvitationCodeCreate, 
    InvitationCodeResponse,
    InvitationCodeValidation,
    InvitationCodeValidationResponse
)
from app.services.invitation_code import InvitationCodeService
from app.core.security.audit import AuditService, AuditEventType
from app.db.session import get_db
from app.core.security.jwt import decode_access_token
from fastapi.security import HTTPBearer
from app.core.security.audit import audit_log

router = APIRouter(prefix="/invitation-codes", tags=["Invitation Codes"])

security = HTTPBearer()

@router.post("/generate", response_model=InvitationCodeResponse)
@audit_log(
    event_type=AuditEventType.INVITATION_CODE_GENERATE,
    resource="invitation_code",
    action="generate"
)
def generate_invitation_code(
    http_request: Request,
    invitation_data: InvitationCodeCreate,
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """招待QRコードを発行（ログイン中のユーザー/エキスパート）"""
    
    # 監査サービスの初期化
    audit_service = AuditService(db)
    
    try:
        # JWTトークンからユーザー情報を取得
        payload = decode_access_token(token.credentials)
        issuer_id = payload.get("sub")
        issuer_type = payload.get("user_type", "unknown")
        
        if not issuer_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なトークンです"
            )
        
        # 招待コードを作成
        code_info = InvitationCodeService.create_invitation_code(
            issuer_id, 
            issuer_type, 
            invitation_data
        )
        
        # 成功時の監査ログ
        audit_service.log_event(
            event_type=AuditEventType.INVITATION_CODE_GENERATED,
            user_id=issuer_id,
            user_type=issuer_type,
            resource="invitation_code",
            action="generate",
            success=True,
            request=http_request,
            details={
                "code": code_info["code"],
                "code_type": code_info["code_type"],
                "max_uses": code_info["max_uses"],
                "expires_at": code_info["expires_at"].isoformat()
            }
        )
        
        return InvitationCodeResponse(
            code=code_info["code"],
            invitation_link=code_info["invitation_link"],
            qr_code_data=code_info["qr_code_data"],  # QRコードデータを追加
            code_type=code_info["code_type"],
            max_uses=code_info["max_uses"],
            expires_at=code_info["expires_at"],
            description=code_info["description"],
            message="招待QRコードが正常に発行されました"
        )
        
    except Exception as e:
        # エラー時の監査ログ
        audit_service.log_event(
            event_type=AuditEventType.INVITATION_CODE_GENERATED,
            user_id=issuer_id if 'issuer_id' in locals() else "unknown",
            user_type=issuer_type if 'issuer_type' in locals() else "unknown",
            resource="invitation_code",
            action="generate",
            success=False,
            request=http_request,
            details={"error": str(e)}
        )
        raise

@router.post("/validate", response_model=InvitationCodeValidationResponse)
def validate_invitation_code_endpoint(
    http_request: Request,
    validation_data: InvitationCodeValidation,
    db: Session = Depends(get_db)
):
    """招待コードの有効性を検証（誰でも使用可能）"""
    
    try:
        is_valid, code_info, message = InvitationCodeService.validate_code(validation_data.code)
        
        # 発行者情報を取得
        issuer_info = None
        if code_info:
            issuer_info = InvitationCodeService.get_issuer_info(
                db, 
                code_info["issuer_id"], 
                code_info["issuer_type"]
            )
        
        return InvitationCodeValidationResponse(
            is_valid=is_valid,
            code_type=code_info["code_type"] if code_info else None,
            message=message,
            issuer_info=issuer_info
        )
        
    except Exception as e:
        return InvitationCodeValidationResponse(
            is_valid=False,
            message=f"検証中にエラーが発生しました: {str(e)}"
        )

@router.post("/use/{code}")
def use_invitation_code_endpoint(
    code: str,
    user_email: str,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """招待コードを使用（登録時に呼び出し）"""
    
    try:
        # 招待コードを使用
        success = InvitationCodeService.use_code(code, user_email)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="招待コードの使用に失敗しました"
            )
        
        return {"message": "招待コードが正常に使用されました"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/my-codes")
def get_my_invitation_codes(
    http_request: Request,
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """自分が発行した招待コード一覧を取得"""
    
    try:
        # JWTトークンからユーザー情報を取得
        payload = decode_access_token(token.credentials)
        issuer_id = payload.get("sub")
        
        if not issuer_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なトークンです"
            )
        
        # 発行した招待コード一覧を取得
        codes = InvitationCodeService.get_codes_by_issuer(issuer_id)
        
        return {"codes": codes}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{code}")
@audit_log(
    event_type=AuditEventType.INVITATION_CODE_DEACTIVATE,
    resource="invitation_code",
    action="deactivate"
)
def deactivate_invitation_code(
    code: str,
    http_request: Request,
    db: Session = Depends(get_db),
    token: str = Depends(security)
):
    """招待コードを無効化"""
    
    try:
        # JWTトークンからユーザー情報を取得
        payload = decode_access_token(token.credentials)
        issuer_id = payload.get("sub")
        
        if not issuer_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なトークンです"
            )
        
        # 招待コードを無効化
        success = InvitationCodeService.deactivate_code(code, issuer_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="招待コードが見つからないか、無効化する権限がありません"
            )
        
        return {"message": "招待コードが正常に無効化されました"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
