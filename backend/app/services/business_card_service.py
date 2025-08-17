import os
import uuid
from datetime import datetime
from typing import Optional
from fastapi import UploadFile, HTTPException
from app.core.blob import upload_binary_to_blob

class BusinessCardService:
    """名刺画像処理サービス"""

    def __init__(self):
        self.allowed_image_types = {'image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic'}
        self.max_file_size = 5 * 1024 * 1024  # 5MB

    def validate_image(self, file: UploadFile) -> bool:
        """名刺画像の妥当性をチェック"""
        # ファイル名の存在チェック
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="ファイル名が指定されていません"
            )
        
        # ファイルサイズチェック
        if file.size is None:
            raise HTTPException(
                status_code=400,
                detail="ファイルサイズを取得できません"
            )
        
        if file.size > self.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"ファイルサイズが大きすぎます。最大{self.max_file_size // (1024*1024)}MBまで（現在: {file.size // (1024*1024)}MB）"
            )

        # 画像タイプチェック
        if not file.content_type:
            raise HTTPException(
                status_code=400,
                detail="ファイルタイプが指定されていません"
            )
        
        if file.content_type not in self.allowed_image_types:
            raise HTTPException(
                status_code=400,
                detail=f"対応していない画像形式です。対応形式: JPEG, PNG, WebP, HEIC（現在: {file.content_type}）"
            )

        return True

    def generate_filename(self, original_filename: str) -> str:
        """一意のファイル名を生成"""
        if not original_filename:
            raise ValueError("ファイル名が指定されていません")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(original_filename)[1]
        
        # 拡張子が空の場合は.jpgをデフォルトとする
        if not file_extension:
            file_extension = '.jpg'
        
        unique_id = str(uuid.uuid4())[:8]
        
        return f"business_cards/{timestamp}_{unique_id}{file_extension}"

    async def upload_business_card(self, file: UploadFile) -> dict:
        """名刺画像をアップロード"""
        try:
            # 画像の妥当性をチェック
            self.validate_image(file)
            
            # ファイル内容を読み込み
            file_content = await file.read()
            
            # ファイル名を生成
            blob_filename = self.generate_filename(file.filename)
            
            # Azure Blob Storageにアップロード
            image_url = upload_binary_to_blob(file_content, blob_filename)
            
            return {
                "image_url": image_url,
                "filename": file.filename,
                "file_size": file.size,
                "content_type": file.content_type,
                "uploaded_at": datetime.now().isoformat()
            }

        except HTTPException:
            # HTTPExceptionはそのまま再送出
            raise
        except ValueError as e:
            # バリデーションエラー
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            # その他のエラー
            raise HTTPException(
                status_code=500,
                detail=f"名刺画像のアップロード中にエラーが発生しました: {str(e)}"
            )

business_card_service = BusinessCardService()
