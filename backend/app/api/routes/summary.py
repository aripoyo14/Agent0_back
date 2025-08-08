# app/api/routes/relation.py
"""
 - 面談録の要約する
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Union
from app.schemas.summary import SummaryRequest, SummaryResponse
from app.db.session import get_db
from app.models.user import User
from app.services.openai import generate_summary
from app.services.summary_vector import summary_vector_service

# FastAPIのルーターを初期化
router = APIRouter(prefix="/summary", tags=["Summary"])

@router.post("/summary")
async def summary(request: SummaryRequest, db: Session = Depends(get_db)):
    try:
        # 要約を生成
        summary_result = generate_summary(request.minutes)
        
        # 要約内容をベクトル化してPineconeに保存
        vector_result = summary_vector_service.vectorize_summary(
            summary_title=summary_result["title"],
            summary_content=summary_result["summary"],
            expert_id=request.expert_id,
            tag_ids=request.tag_ids
        )
        
        # tag_idsを整数リストに変換
        tag_ids_list = summary_vector_service._parse_tag_ids(
            summary_vector_service._normalize_tag_ids(request.tag_ids)
        )
        
        # レスポンスを構築
        response = SummaryResponse(
            title=summary_result["title"],
            summary=summary_result["summary"],
            expert_id=request.expert_id,
            tag_ids=tag_ids_list,
            summary_id=vector_result.get("summary_id", ""),
            vectorization_result=vector_result if vector_result["success"] else None
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"要約処理中にエラーが発生しました: {str(e)}"
        )

@router.get("/search")
async def search_summaries(
    query: str = Query(..., description="検索クエリ"),
    top_k: int = Query(5, description="返す結果の数"),
    expert_id: Optional[int] = Query(None, description="特定のエキスパートで絞り込み"),
    tag_ids: Optional[str] = Query(None, description="特定のタグで絞り込み（カンマ区切り）")
):
    """
    要約内容の類似検索を行う
    """
    try:
        results = summary_vector_service.search_similar_summaries(
            query=query,
            top_k=top_k,
            expert_id=expert_id,
            tag_ids=tag_ids
        )
        
        return {
            "status": "success",
            "query": query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"検索処理中にエラーが発生しました: {str(e)}"
        )

@router.delete("/vector/{summary_id}")
async def delete_summary_vector(summary_id: str):
    """
    指定された要約IDのベクトルを削除する
    """
    try:
        result = summary_vector_service.delete_summary_vector(summary_id)
        
        if result["success"]:
            return {
                "status": "success",
                "message": result["message"]
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ベクトル削除中にエラーが発生しました: {str(e)}"
        )

@router.get("/statistics")
async def get_summary_vector_statistics():
    """
    要約ベクトルの統計情報を取得する
    """
    try:
        stats = summary_vector_service.get_summary_vector_statistics()
        
        if stats["success"]:
            return stats
        else:
            raise HTTPException(
                status_code=400,
                detail=stats["message"]
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"統計情報取得中にエラーが発生しました: {str(e)}"
        )

