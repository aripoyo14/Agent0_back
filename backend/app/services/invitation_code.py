import secrets
import string
import qrcode
import base64
import io
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple
from app.schemas.invitation_code import InvitationCodeCreate, InvitationCodeType
from sqlalchemy.orm import Session
from app.models.user.user import User
from app.models.expert import Expert

# 日本標準時間取得
JST = timezone(timedelta(hours=9))

class InvitationCodeService:
    """招待QRコード生成・管理サービス"""
    
    # メモリ内で招待コードを管理（永続化はしない）
    _codes: Dict[str, Dict] = {}
    
    # フロントエンドのベースURL
    FRONTEND_BASE_URL = "https://aps-agent0-02-afawambwf2bxd2fv.italynorth-01.azurewebsites.net"
    
    @classmethod
    def generate_code(cls, length: int = 8) -> str:
        """ランダムな招待コードを生成"""
        # 数字と大文字のアルファベットを使用
        characters = string.ascii_uppercase + string.digits
        # 0とO、1とIが混同されやすいので除外
        characters = characters.replace('0', '').replace('O', '').replace('1', '').replace('I', '')
        
        while True:
            code = ''.join(secrets.choice(characters) for _ in range(length))
            # 生成されたコードが既存のコードと重複しないかチェック
            if code not in cls._codes:
                return code
    
    @classmethod
    def generate_qr_code(cls, data: str) -> str:
        """QRコードを生成してBase64エンコードして返す"""
        # QRコードを生成
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # PILイメージを作成
        img = qr.make_image(fill_color="black", back_color="white")
        
        # バイトストリームに保存
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Base64エンコード
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return img_str
    
    @classmethod
    def create_invitation_code(
        cls, 
        issuer_id: str, 
        issuer_type: str,
        invitation_data: InvitationCodeCreate
    ) -> Dict:
        """招待QRコードを作成"""
        
        # 有効期限を計算
        expires_at = datetime.now(JST) + timedelta(hours=invitation_data.expires_in_hours)
        
        # 招待コードを生成
        code = cls.generate_code()
        
        # 招待リンクを生成
        invitation_link = f"{cls.FRONTEND_BASE_URL}/expert/registration?code={code}"
        
        # QRコードを生成
        qr_code_data = cls.generate_qr_code(invitation_link)
        
        # コード情報を保存
        code_info = {
            "code": code,
            "invitation_link": invitation_link,
            "qr_code_data": qr_code_data,
            "issuer_id": issuer_id,
            "issuer_type": issuer_type,
            "code_type": invitation_data.code_type,
            "max_uses": invitation_data.max_uses,
            "current_uses": 0,
            "expires_at": expires_at,
            "description": invitation_data.description,
            "created_at": datetime.now(JST),
            "is_active": True
        }
        
        cls._codes[code] = code_info
        
        return code_info
    
    @classmethod
    def validate_code(cls, code: str) -> Tuple[bool, Optional[Dict], str]:
        """招待コードの有効性を検証"""
        if code not in cls._codes:
            return False, None, "招待コードが見つかりません"
        
        code_info = cls._codes[code]
        
        if not code_info["is_active"]:
            return False, code_info, "この招待コードは無効化されています"
        
        if code_info["current_uses"] >= code_info["max_uses"]:
            return False, code_info, "この招待コードは使用回数上限に達しています"
        
        if datetime.now(JST) > code_info["expires_at"]:
            return False, code_info, "この招待コードは有効期限が切れています"
        
        return True, code_info, "有効な招待コードです"
    
    @classmethod
    def use_code(cls, code: str, user_email: str) -> bool:
        """招待コードを使用"""
        is_valid, code_info, message = cls.validate_code(code)
        
        if not is_valid:
            return False
        
        # 使用回数を増加
        code_info["current_uses"] += 1
        
        # 使用上限に達した場合は無効化
        if code_info["current_uses"] >= code_info["max_uses"]:
            code_info["is_active"] = False
        
        return True
    
    @classmethod
    def get_codes_by_issuer(cls, issuer_id: str) -> list[Dict]:
        """発行者が発行した招待コード一覧を取得"""
        return [
            code_info for code_info in cls._codes.values()
            if code_info["issuer_id"] == issuer_id
        ]
    
    @classmethod
    def deactivate_code(cls, code: str, issuer_id: str) -> bool:
        """招待コードを無効化"""
        if code in cls._codes:
            code_info = cls._codes[code]
            if code_info["issuer_id"] == issuer_id:
                code_info["is_active"] = False
                return True
        return False
    
    @classmethod
    def get_issuer_info(cls, db: Session, issuer_id: str, issuer_type: str) -> Optional[Dict]:
        """発行者の情報を取得"""
        try:
            if issuer_type == "user":
                issuer = db.query(User).filter(User.id == issuer_id).first()
                if issuer:
                    return {
                        "id": issuer.id,
                        "name": f"{issuer.last_name} {issuer.first_name}",
                        "type": "user"
                    }
            elif issuer_type == "expert":
                issuer = db.query(Expert).filter(Expert.id == issuer_id).first()
                if issuer:
                    return {
                        "id": issuer.id,
                        "name": f"{issuer.last_name} {issuer.first_name}",
                        "type": "expert"
                    }
        except Exception:
            pass
        return None
