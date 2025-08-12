from __future__ import annotations

from datetime import date as date_type
from typing import List, Optional

from pydantic import BaseModel, HttpUrl, Field


class OutreachRequest(BaseModel):
    """人物と所属情報から外部発信（書籍/登壇など）を探索するための入力。"""

    last_name: str = Field(..., description="姓")
    first_name: str = Field(..., description="名")
    companies_name: Optional[str] = Field(None, description="会社名")
    department: Optional[str] = Field(None, description="部署名")
    limit: int = Field(10, ge=1, le=50, description="最大取得件数（1-50）")


class OutreachItem(BaseModel):
    """外部発信の単一アイテム。"""

    category: str = Field(..., description="カテゴリ（例: 書籍/登壇/講演/寄稿/インタビュー/論文 など）")
    date: Optional[date_type] = Field(None, description="発表・出版日（不明な場合はnull）")
    title: str = Field(..., description="タイトル")
    details: HttpUrl = Field(..., description="情報リソースのURL")


# レスポンスはアイテム配列
OutreachResponse = List[OutreachItem]


