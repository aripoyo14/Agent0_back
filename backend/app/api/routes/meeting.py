from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.models.user import User
from app.core.dependencies import get_current_user
from app.crud.meeting import meeting_crud, meeting_evaluation_crud
from app.services.file_upload import file_upload_service
from app.services.cosmos_vector import cosmos_vector_service
from app.schemas.meeting import (
    MeetingCreate, 
    MeetingUpdate, 
    MeetingResponse, 
    MinutesUploadResponse,
    MeetingEvaluationCreate,
    MeetingEvaluationUpdate,
    MeetingEvaluationResponse
)
from app.schemas.summary import SummaryRequest

router = APIRouter(prefix="/meetings", tags=["Meetings"])

@router.post("/", response_model=MeetingResponse, summary="Create Meeting")
async def create_meeting(
    meeting_data: MeetingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """面談を作成"""
    try:
        meeting = meeting_crud.create(db, meeting_data)
        return meeting
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"面談作成中にエラーが発生しました: {str(e)}"
        )

@router.get("/{meeting_id}", response_model=MeetingResponse, summary="Get Meeting")
async def get_meeting(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """面談を取得"""
    meeting = meeting_crud.get(db, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=404,
            detail="面談が見つかりません"
        )
    return meeting

@router.get("/", response_model=List[MeetingResponse], summary="Get All Meetings")
async def get_all_meetings(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """面談一覧を取得"""
    meetings = meeting_crud.get_all(db, skip=skip, limit=limit)
    return meetings

@router.put("/{meeting_id}", response_model=MeetingResponse, summary="Update Meeting")
async def update_meeting(
    meeting_id: str,
    meeting_data: MeetingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """面談を更新"""
    meeting = meeting_crud.update(db, meeting_id, meeting_data)
    if not meeting:
        raise HTTPException(
            status_code=404,
            detail="面談が見つかりません"
        )
    return meeting

@router.delete("/{meeting_id}", summary="Delete Meeting")
async def delete_meeting(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """面談を削除"""
    success = meeting_crud.delete(db, meeting_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail="面談が見つかりません"
        )
    return {"message": "面談を削除しました"}

@router.post("/{meeting_id}/upload-minutes", response_model=MinutesUploadResponse, summary="Upload Minutes")
async def upload_minutes(
    meeting_id: str,
    file: UploadFile = File(...),
    expert_id: Optional[str] = Form(None),
    tag_ids: Optional[str] = Form(None),  # カンマ区切りの文字列
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """議事録ファイルをアップロードしてベクトル化"""
    try:
        # 面談の存在確認
        meeting = meeting_crud.get(db, meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=404,
                detail="面談が見つかりません"
            )

        # ファイルの妥当性をチェック
        file_upload_service.validate_file(file)
        
        # ファイルを読み込み
        file_content = await file.read()
        
        # ファイルをアップロード
        file_url = await file_upload_service.upload_minutes_file(file_content, file.filename, meeting_id)
        
        # データベースのminutes_urlを更新
        meeting_crud.update_minutes_url(db, meeting_id, file_url)

        # ファイルからテキストを抽出
        minutes_text = file_upload_service.extract_text_from_file(file_content, file.filename)

        # ベクトル化処理
        vectorization_result = None
        if minutes_text and minutes_text != f"[{file.filename}の内容を抽出中...]":
            # tag_idsをリストに変換
            tag_ids_list = []
            if tag_ids:
                tag_ids_list = [int(tag_id.strip()) for tag_id in tag_ids.split(",") if tag_id.strip()]

            # SummaryRequestを作成
            summary_request = SummaryRequest(
                minutes=minutes_text,
                expert_id=expert_id or "",
                tag_ids=tag_ids_list
            )

            # 既存のcosmos-minutesエンドポイントの処理を実行
            summary_result = cosmos_vector_service.vectorize_minutes(
                summary_title=f"面談録: {meeting.title}",
                summary_content=minutes_text[:500] + "..." if len(minutes_text) > 500 else minutes_text,
                expert_id=expert_id,
                tag_ids=tag_ids_list,
                raw_minutes=minutes_text,
            )

            vectorization_result = summary_result

        return MinutesUploadResponse(
            success=True,
            meeting_id=meeting_id,
            minutes_url=file_url,
            message="議事録のアップロードが完了しました",
            vectorization_result=vectorization_result
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"議事録アップロード中にエラーが発生しました: {str(e)}"
        )

# 評価関連エンドポイント
@router.put("/{meeting_id}/evaluate", response_model=MeetingEvaluationResponse, summary="Update Meeting Evaluation")
async def evaluate_meeting(
    meeting_id: str,
    evaluation_data: MeetingEvaluationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """面談の評価を更新（既存カラム使用）"""
    try:
        # 面談の存在確認
        meeting = meeting_crud.get(db, meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=404,
                detail="面談が見つかりません"
            )
        
        # 評価を更新
        updated_meeting = meeting_evaluation_crud.update_meeting_evaluation(db, meeting_id, evaluation_data)
        if not updated_meeting:
            raise HTTPException(
                status_code=404,
                detail="面談が見つかりません"
            )
        
        return updated_meeting
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"面談評価更新中にエラーが発生しました: {str(e)}"
        )

@router.get("/{meeting_id}/evaluation", response_model=MeetingEvaluationResponse, summary="Get Meeting Evaluation")
async def get_meeting_evaluation(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """面談の評価を取得（既存カラム使用）"""
    try:
        # 面談の存在確認
        meeting = meeting_crud.get(db, meeting_id)
        if not meeting:
            raise HTTPException(
                status_code=404,
                detail="面談が見つかりません"
            )
        
        return meeting
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"評価取得中にエラーが発生しました: {str(e)}"
        )




