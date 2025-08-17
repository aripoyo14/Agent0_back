from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
import logging
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.business_card_service import business_card_service

# ログ設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/business-cards", tags=["BusinessCards"])

@router.post("/upload")
async def upload_business_card(
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    logger.info(f"=== 名刺画像アップロード リクエスト受信 ===")
    logger.info(f"リクエストURL: /api/business-cards/upload")
    logger.info(f"ファイル名: {image.filename}")
    logger.info(f"ファイルサイズ: {image.size}")
    logger.info(f"コンテンツタイプ: {image.content_type}")
    
    try:
        result = await business_card_service.upload_business_card(image)
        logger.info(f"アップロード成功: {result}")
        return result
    except HTTPException as he:
        logger.error(f"HTTPException: {he.status_code} - {he.detail}")
        raise
    except Exception as e:
        logger.error(f"予期しないエラー: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"アップロード処理に失敗しました: {str(e)}")
