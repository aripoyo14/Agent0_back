from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.api.deps import get_db
from app.services.policy_tag_vector import policy_tag_vector_service
from app.crud.policy_tag import policy_tag_crud
from app.models.policy_tag import PolicyTag

router = APIRouter()

@router.post("/vectorize", response_model=Dict[str, Any])
async def vectorize_policy_tags(db: Session = Depends(get_db)):
    """
    MySQLのpolicy_tagsテーブルから全てのデータを取得し、
    ベクトル化してPineconeに保存する
    """
    try:
        result = policy_tag_vector_service.vectorize_policy_tags(db)
        
        if result["success"]:
            return {
                "status": "success",
                "message": result["message"],
                "processed_count": result["processed_count"],
                "namespace": result["namespace"]
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ベクトル化処理中にエラーが発生しました: {str(e)}"
        )

@router.post("/vectorize/{tag_id}", response_model=Dict[str, Any])
async def vectorize_single_policy_tag(tag_id: int, db: Session = Depends(get_db)):
    """
    指定されたIDの政策タグをベクトル化してPineconeに保存する
    """
    try:
        result = policy_tag_vector_service.vectorize_single_policy_tag(db, tag_id)
        
        if result["success"]:
            return {
                "status": "success",
                "message": result["message"],
                "tag_id": tag_id,
                "namespace": result["namespace"]
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ベクトル化処理中にエラーが発生しました: {str(e)}"
        )

@router.get("/search", response_model=List[Dict[str, Any]])
async def search_similar_policy_tags(
    query: str,
    top_k: int = 5,
    db: Session = Depends(get_db)
):
    """
    クエリに類似した政策タグを検索する
    
    Args:
        query: 検索クエリ
        top_k: 返す結果の数（デフォルト: 5）
    """
    try:
        if not query.strip():
            raise HTTPException(
                status_code=400,
                detail="検索クエリを入力してください"
            )
        
        similar_tags = policy_tag_vector_service.search_similar_policy_tags(query, top_k)
        
        return similar_tags
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"検索処理中にエラーが発生しました: {str(e)}"
        )

@router.get("/list", response_model=List[Dict[str, Any]])
async def get_all_policy_tags(db: Session = Depends(get_db)):
    """
    MySQLのpolicy_tagsテーブルから全てのデータを取得する
    """
    try:
        policy_tags = policy_tag_crud.get_all_policy_tags(db)
        
        return [
            {
                "id": tag.id,
                "name": tag.name,
                "embedding": tag.embedding,
                "created_at": tag.created_at.isoformat() if tag.created_at else None,
                "updated_at": tag.updated_at.isoformat() if tag.updated_at else None
            }
            for tag in policy_tags
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"データ取得中にエラーが発生しました: {str(e)}"
        )

@router.post("/create", response_model=Dict[str, Any])
async def create_policy_tag(
    name: str,
    db: Session = Depends(get_db)
):
    """
    新しい政策タグを作成する
    """
    try:
        if not name.strip():
            raise HTTPException(
                status_code=400,
                detail="タグ名を入力してください"
            )
        
        policy_tag = policy_tag_crud.create_policy_tag(db, name)
        
        return {
            "status": "success",
            "message": "政策タグを作成しました",
            "data": {
                "id": policy_tag.id,
                "name": policy_tag.name,
                "created_at": policy_tag.created_at.isoformat() if policy_tag.created_at else None
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"タグ作成中にエラーが発生しました: {str(e)}"
        )

@router.delete("/delete/{tag_id}", response_model=Dict[str, Any])
async def delete_policy_tag(
    tag_id: int,
    db: Session = Depends(get_db)
):
    """
    指定されたIDの政策タグを削除する（MySQLとPineconeの両方から）
    """
    try:
        # MySQLから削除
        deleted = policy_tag_crud.delete_policy_tag(db, tag_id)
        
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"ID {tag_id} の政策タグが見つかりません"
            )
        
        # Pineconeからも削除
        vector_result = policy_tag_vector_service.delete_policy_tag_vectors([tag_id])
        
        return {
            "status": "success",
            "message": "政策タグを削除しました",
            "mysql_deleted": deleted,
            "vector_deleted": vector_result["success"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"タグ削除中にエラーが発生しました: {str(e)}"
        )

@router.get("/statistics", response_model=Dict[str, Any])
async def get_vector_statistics():
    """
    Pineconeのベクトル統計情報を取得する
    """
    try:
        stats = policy_tag_vector_service.get_vector_statistics()
        
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
