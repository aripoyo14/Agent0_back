"""
QRコード生成サービス
"""

import pyotp
import qrcode
import base64
from io import BytesIO
from typing import Dict, Any

class QRCodeService:
    """QRコード生成を担当するサービスクラス"""
    
    @staticmethod
    def generate_totp_qr(
        secret: str, 
        email: str, 
        issuer: str = "Agent0",
        box_size: int = 10,
        border: int = 5
    ) -> Dict[str, Any]:
        """
        TOTP用のQRコードを生成
        
        Args:
            secret: TOTP秘密鍵
            email: ユーザーのメールアドレス
            issuer: サービス名
            box_size: QRコードのボックスサイズ
            border: ボーダーサイズ
            
        Returns:
            QRコードのbase64データと関連情報
        """
        try:
            # TOTP URIを生成
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(
                name=email,
                issuer_name=issuer
            )
            
            # QRコードを生成
            qr = qrcode.QRCode(
                version=1, 
                box_size=box_size, 
                border=border
            )
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            # 画像を生成
            img = qr.make_image(fill_color="black", back_color="white")
            
            # base64エンコード
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return {
                "qr_code": f"data:image/png;base64,{img_str}",
                "provisioning_uri": provisioning_uri,
                "secret": secret,
                "email": email,
                "issuer": issuer
            }
            
        except Exception as e:
            raise Exception(f"QRコード生成エラー: {str(e)}")
    
    @staticmethod
    def generate_custom_qr(
        data: str,
        box_size: int = 10,
        border: int = 5,
        fill_color: str = "black",
        back_color: str = "white"
    ) -> str:
        """
        カスタムデータ用のQRコードを生成
        
        Args:
            data: QRコードに含めるデータ
            box_size: QRコードのボックスサイズ
            border: ボーダーサイズ
            fill_color: 塗りつぶし色
            back_color: 背景色
            
        Returns:
            QRコードのbase64データ
        """
        try:
            qr = qrcode.QRCode(
                version=1, 
                box_size=box_size, 
                border=border
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            img = qr.make_image(
                fill_color=fill_color, 
                back_color=back_color
            )
            
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            raise Exception(f"カスタムQRコード生成エラー: {str(e)}")
