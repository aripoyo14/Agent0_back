from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx
import re

from app.core.dependencies import get_current_user
from app.core.security.audit import AuditService, AuditEventType
from app.core.security.audit.decorators import audit_log
from app.crud.meeting import meeting_crud, meeting_evaluation_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.meeting import (
    MeetingCreate, MeetingUpdate, MeetingResponse,
    MeetingEvaluationCreate, MeetingEvaluationUpdate, MeetingEvaluationResponse,
    MinutesUploadResponse
)
from app.schemas.summary import SummaryRequest
from app.services.file_upload import file_upload_service
from app.services.cosmos_vector import cosmos_vector_service

def clean_text_for_api(text: str) -> str:
    """API送信用にテキストを整形"""
    if not text:
        return ""
    
    # 改行文字を適切に処理
    cleaned_text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 連続する改行を単一の改行に
    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
    
    # 前後の空白を削除
    cleaned_text = cleaned_text.strip()
    
    return cleaned_text

router = APIRouter(prefix="/meetings", tags=["Meetings"])

@router.post("/", response_model=MeetingResponse, summary="Create Meeting")
@audit_log(
    event_type=AuditEventType.DATA_CREATE,
    resource="meeting",
    action="create"
)
async def create_meeting(
    meeting_data: MeetingCreate,
    http_request: Request,
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
@audit_log(
    event_type=AuditEventType.READ_MEETING_DETAILS,
    resource="meeting",
    action="read"
)
async def get_meeting(
    meeting_id: str,
    http_request: Request,
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
@audit_log(
    event_type=AuditEventType.READ_MEETING_DETAILS,
    resource="meeting",
    action="list"
)
async def get_all_meetings(
    http_request: Request,  # 最初に配置
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """面談一覧を取得"""
    meetings = meeting_crud.get_all(db, skip=skip, limit=limit)
    return meetings

@router.put("/{meeting_id}", response_model=MeetingResponse, summary="Update Meeting")
@audit_log(
    event_type=AuditEventType.DATA_UPDATE,
    resource="meeting",
    action="update"
)
async def update_meeting(
    meeting_id: str,
    meeting_data: MeetingUpdate,
    http_request: Request,
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
@audit_log(
    event_type=AuditEventType.DATA_DELETE,
    resource="meeting",
    action="delete"
)
async def delete_meeting(
    meeting_id: str,
    http_request: Request,
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
@audit_log(
    event_type=AuditEventType.FILE_UPLOAD,
    resource="meeting_minutes",
    action="upload"
)
async def upload_minutes(
    http_request: Request,  # 最初に配置
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
        summary_data = None
        
        if minutes_text and minutes_text != f"[{file.filename}の内容を抽出中...]":
            # tag_idsをリストに変換
            tag_ids_list = []
            if tag_ids:
                tag_ids_list = [int(tag_id.strip()) for tag_id in tag_ids.split(",") if tag_id.strip()]

            # テキストを整形
            cleaned_minutes = clean_text_for_api(minutes_text)
            
            # POST /api/cosmos-minutes/minutes エンドポイントを呼び出し
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"http://localhost:8000/api/cosmos-minutes/minutes",
                        json={
                            "minutes": cleaned_minutes,
                            "expert_id": expert_id or "",
                            "tag_ids": tag_ids_list
                        },
                        timeout=30.0  # 30秒のタイムアウト
                    )
                    
                    if response.status_code == 200:
                        summary_data = response.json()
                        vectorization_result = summary_data.get("vectorization_result")
                        
                        # 要約をMTGデータに保存
                        if summary_data.get("summary"):
                            meeting_crud.update_summary(db, meeting_id, summary_data["summary"])
                    else:
                        # API呼び出しが失敗した場合のフォールバック処理
                        print(f"Warning: cosmos-minutes API call failed with status {response.status_code}")
                        vectorization_result = {
                            "success": False,
                            "message": f"要約生成API呼び出しに失敗しました: {response.status_code}"
                        }
                        
            except Exception as e:
                print(f"Error calling cosmos-minutes API: {str(e)}")
                # エラーが発生した場合のフォールバック処理
                vectorization_result = {
                    "success": False,
                    "message": f"要約生成API呼び出し中にエラーが発生しました: {str(e)}"
                }

        # レスポンスメッセージを構築
        message = "議事録のアップロードが完了しました"
        if summary_data and summary_data.get("summary"):
            message += f"。要約: {summary_data['summary'][:100]}..."
        elif vectorization_result and not vectorization_result.get("success"):
            message += f"。注意: {vectorization_result.get('message', '要約生成に失敗しました')}"
        
        return MinutesUploadResponse(
            success=True,
            meeting_id=meeting_id,
            minutes_url=file_url,
            message=message,
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
@audit_log(
    event_type=AuditEventType.DATA_UPDATE,
    resource="meeting_evaluation",
    action="update"
)
async def evaluate_meeting(
    http_request: Request,  # 最初に配置
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
@audit_log(
    event_type=AuditEventType.DATA_READ,
    resource="meeting_evaluation",
    action="read"
)
async def get_meeting_evaluation(
    meeting_id: str,
    http_request: Request,
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




