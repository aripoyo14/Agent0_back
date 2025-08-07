from pydantic import BaseModel

# リクエスト用スキーマ（POST /summary で使う）
class SummaryRequest(BaseModel):
    minutes: str

# タイトルと要約返却用スキーマ（レスポンスで使用）
class SummaryResponse(BaseModel):
    title: str
    summary: str
