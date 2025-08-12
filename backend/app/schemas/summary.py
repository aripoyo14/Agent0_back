from pydantic import BaseModel
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
