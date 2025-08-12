from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from app.models.expert_activity import ExpertActivity


def bulk_upsert_expert_activities(db: Session, expert_id: str, items: Iterable[dict]) -> int:
    """シンプルにURL重複でスキップするinsert。戻り値は追加件数。"""
    count = 0
    existing_urls = {
        url for (url,) in db.query(ExpertActivity.event_url).filter(ExpertActivity.expert_id == expert_id).all()
    }
    for it in items:
        if it["event_url"] in existing_urls:
            continue
        db.add(ExpertActivity(
            expert_id=expert_id,
            event_date=it.get("event_date"),
            event_url=it["event_url"],
            title=it.get("title"),
            description=it.get("description"),
        ))
        count += 1
    if count:
        db.commit()
    return count


