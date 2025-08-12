from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.schemas.outreach import OutreachRequest, OutreachResponse
from app.services.outreach import find_outreach, find_outreach_with_debug
from urllib.parse import urlparse
from app.db.session import get_db
from app.crud.expert import get_company_by_name, get_expert_by_name_and_company
from app.crud.expert_activity import bulk_upsert_expert_activities


router = APIRouter(prefix="/outreach", tags=["Outreach"])


@router.post("", response_model=OutreachResponse, summary="人物の外部発信情報を取得・保存")
async def outreach_search(req: OutreachRequest, db: Session = Depends(get_db)):
    try:
        # 会社ドメイン（siteSearch用）を解決
        company_domain = None
        if req.companies_name:
            company = get_company_by_name(db, req.companies_name)
            if company and company.url:
                try:
                    netloc = urlparse(company.url).netloc
                    company_domain = netloc or None
                except Exception:
                    company_domain = None

        items, debug = find_outreach_with_debug(
            last_name=req.last_name,
            first_name=req.first_name,
            companies_name=req.companies_name,
            department=req.department,
            limit=req.limit,
            company_domain=company_domain,
        )
        # DB解決: company -> expert
        company_id = None
        if req.companies_name:
            company = get_company_by_name(db, req.companies_name)
            if company:
                company_id = company.id

        expert = get_expert_by_name_and_company(db, req.last_name, req.first_name, company_id)
        if expert and items:
            # expert_activitiesに保存（カテゴリ等はdescriptionに含める）
            prepared = []
            for it in items:
                try:
                    prepared.append({
                        "event_date": it.date,
                        "event_url": str(it.details),
                        "title": it.title or "",
                        "description": f"category={getattr(it, 'category', '外部発信')}",
                    })
                except Exception:
                    continue
            bulk_upsert_expert_activities(db, expert.id, prepared)

        # レスポンスヘッダ用に件数などを付与（FastAPIのResponseはDIが必要だが、ここではログ出力のみに留める）
        print({
            "outreach_debug": {
                **debug,
                "saved_for_expert": bool(expert) if 'expert' in locals() else False,
                "company_domain": company_domain,
            }
        })

        return items
    except HTTPException:
        raise
    except Exception as e:
        # LLM応答ぶれなどでキー欠落時にも500にしない
        raise HTTPException(status_code=500, detail=f"Outreach処理でエラー: {e}")


