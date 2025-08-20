# app/api/routes/cosmos_summary.py
"""
 - Azure Cosmos DBを使用した面談録（minutes）ベクトル化・検索
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Union
from app.schemas.summary import SummaryRequest, SummaryResponse
from app.db.session import get_db
from app.models.user import User
from app.services.openai import generate_summary
from app.services.cosmos_vector import cosmos_vector_service
from app.core.security.rate_limit.decorators import rate_limit_read_api

# FastAPIのルーターを初期化
router = APIRouter(prefix="/cosmos-minutes", tags=["Cosmos Minutes"])

@router.post("/minutes", summary="Vectorize Minutes", description="面談録（minutes）をベクトル化し、Cosmos DBに保存。関連度も更新")
@rate_limit_read_api
async def minutes(request: SummaryRequest, db: Session = Depends(get_db)):
    try:
        # 要約を生成（レスポンス表示用）。埋め込みはminutesを優先
        summary_result = generate_summary(request.minutes)
        
        # 面談録（minutes）を優先してベクトル化してCosmos DBに保存
        vector_result = cosmos_vector_service.vectorize_minutes(
            summary_title=summary_result["title"],
            summary_content=summary_result["summary"],
            expert_id=request.expert_id,
            tag_ids=request.tag_ids,
            raw_minutes=request.minutes,
        )
        
        # tag_idsを整数リストに変換
        tag_ids_list = cosmos_vector_service._parse_tag_ids(
            cosmos_vector_service._normalize_tag_ids(request.tag_ids)
        )

        # ベクトルとタグの類似度を計算してMySQLに登録
        if vector_result.get("success") and vector_result.get("vector"):
            cosmos_vector_service.register_expert_tag_similarities(
                db,
                summary_vector=vector_result["vector"],
                expert_id=request.expert_id,
                tag_ids=tag_ids_list,
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
            detail=f"ベクトル化処理中にエラーが発生しました: {str(e)}"
        )

@router.get("/search", summary="Search Minutes", description="面談録（minutes）ベクトルの類似検索")
@rate_limit_read_api
async def search_minutes(
    request: Request,
    query: str = Query(..., description="検索クエリ"),
    top_k: int = Query(5, description="返す結果の数"),
    expert_id: Optional[int] = Query(None, description="特定のエキスパートで絞り込み"),
    tag_ids: Optional[str] = Query(None, description="特定のタグで絞り込み（カンマ区切り）")
):
    """
    Cosmos DBを使用した面談録ベクトルの類似検索を行う
    """
    try:
        results = cosmos_vector_service.search_similar_summaries(
            query=query,
            top_k=top_k,
            expert_id=expert_id,
            tag_ids=tag_ids
        )
        
        return {
            "status": "success",
            "query": query,
            "results": results,
            "count": len(results),
            "database": "cosmos_db"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"検索処理中にエラーが発生しました: {str(e)}"
        )

@router.delete("/vector/{minutes_id}", summary="Delete Minutes Vector", description="指定IDのベクトルをCosmos DBから削除")
async def delete_minutes_vector(minutes_id: str):
    """
    指定されたIDのベクトルをCosmos DBから削除する
    """
    try:
        result = cosmos_vector_service.delete_summary_vector(minutes_id)
        
        if result["success"]:
            return {
                "status": "success",
                "message": result["message"],
                "database": "cosmos_db"
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
async def get_cosmos_vector_statistics():
    """
    Cosmos DBのベクトル統計情報を取得する
    """
    try:
        stats = cosmos_vector_service.get_vector_statistics()
        
        if stats["success"]:
            return {
                **stats,
                "database": "cosmos_db"
            }
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

# ========== 政策タグ関連のエンドポイント ==========

@router.post("/policy-tags/vectorize")
async def vectorize_policy_tags(db: Session = Depends(get_db)):
    """
    MySQLの全政策タグをベクトル化してCosmos DBに保存する
    """
    try:
        result = cosmos_vector_service.vectorize_policy_tags(db)
        
        if result["success"]:
            return {
                "status": "success",
                "message": result["message"],
                "processed_count": result["processed_count"],
                "database": "cosmos_db"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"政策タグベクトル化中にエラーが発生しました: {str(e)}"
        )

@router.post("/policy-tags/vectorize/{tag_id}")
async def vectorize_single_policy_tag(tag_id: int, db: Session = Depends(get_db)):
    """
    指定されたIDの政策タグをベクトル化してCosmos DBに保存する
    """
    try:
        result = cosmos_vector_service.vectorize_single_policy_tag(db, tag_id)
        
        if result["success"]:
            return {
                "status": "success",
                "message": result["message"],
                "tag_id": result.get("tag_id"),
                "tag_name": result.get("tag_name"),
                "database": "cosmos_db"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"政策タグベクトル化中にエラーが発生しました: {str(e)}"
        )

@router.get("/policy-tags/search")
async def search_policy_tags(
    query: str = Query(..., description="検索クエリ"),
    top_k: int = Query(5, description="返す結果の数")
):
    """
    Cosmos DBを使用した政策タグの類似検索を行う
    """
    try:
        results = cosmos_vector_service.search_similar_policy_tags(
            query=query,
            top_k=top_k
        )
        
        return {
            "status": "success",
            "query": query,
            "results": results,
            "count": len(results),
            "database": "cosmos_db"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"政策タグ検索中にエラーが発生しました: {str(e)}"
        )


# マッチングAPIは search_network_map へ移設

@router.delete("/policy-tags/vector/{tag_id}")
async def delete_policy_tag_vector(tag_id: int):
    """
    指定された政策タグIDのベクトルをCosmos DBから削除する
    """
    try:
        result = cosmos_vector_service.delete_policy_tag_vector(tag_id)
        
        if result["success"]:
            return {
                "status": "success",
                "message": result["message"],
                "tag_id": result.get("tag_id"),
                "database": "cosmos_db"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"政策タグベクトル削除中にエラーが発生しました: {str(e)}"
        )
