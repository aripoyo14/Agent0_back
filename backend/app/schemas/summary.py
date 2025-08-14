from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Union, List

# リクエスト用スキーマ（POST /summary で使う）
class SummaryRequest(BaseModel):
    minutes: str
    expert_id: str  # UUID（36文字）を想定
    tag_ids: Union[int, List[int], str]  # 単一のint、リスト、またはカンマ区切りの文字列

# タイトルと要約返却用スキーマ（レスポンスで使用）
class SummaryResponse(BaseModel):
    title: str
    summary: str
    expert_id: str
    tag_ids: List[int]  # 整数リストとして返す
    summary_id: str
    vectorization_result: Optional[Dict[str, Any]] = None


class MatchRequest(BaseModel):
    """
    政策タグ名（単一 or 複数）と自由記述テキストを受け取る入力。
    """
    policy_tag: Union[str, List[str]]
    free_text: str


class SimilarMeetingOut(BaseModel):
    user_id: str
    user_name: str
    similarity: float
    meeting_summary: Optional[str] = None


class MatchResponse(BaseModel):
    experts_by_tag: Dict[int, List[Dict[str, Any]]]
    similar_meetings: List[SimilarMeetingOut]


# ========== Network Map DTOs ==========

class PolicyThemeDTO(BaseModel):
    id: str
    title: str
    color: Optional[str] = None


class ExpertDTO(BaseModel):
    id: str
    name: str
    department: Optional[str] = None
    title: Optional[str] = None


class RelationDTO(BaseModel):
    policy_id: str
    expert_id: str
    relation_score: float


class NetworkMapResponseDTO(BaseModel):
    policy_themes: List[PolicyThemeDTO]
    experts: List[ExpertDTO]
    relations: List[RelationDTO]
