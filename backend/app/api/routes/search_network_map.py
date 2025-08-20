from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.summary import MatchRequest, NetworkMapResponseDTO
from app.crud.experts_policy_tags import experts_policy_tags_crud
from app.crud.policy_tag import policy_tag_crud
from app.core.security.rate_limit.decorators import rate_limit_read_api
from typing import Optional


router = APIRouter(prefix="/search_network_map", tags=["Search Network Map"])


@router.post("/match", response_model=NetworkMapResponseDTO)
@rate_limit_read_api
async def match(
    request: Request, 
    payload: MatchRequest, 
    db: Session = Depends(get_db)
):
    try:
        # 名前からタグIDを解決（単一/複数）
        if not payload.policy_tag:
            raise HTTPException(status_code=400, detail="policy_tag is required")
        tag_names = payload.policy_tag if isinstance(payload.policy_tag, list) else [payload.policy_tag]
        resolved_tags = []
        not_found = []
        for name in tag_names:
            t = policy_tag_crud.get_policy_tag_by_name(db, name)
            if t:
                resolved_tags.append(t)
            else:
                not_found.append(name)
        if not resolved_tags:
            raise HTTPException(status_code=404, detail=f"policy_tag(s) not found: {', '.join(not_found)}")
        if not_found:
            # 全て必要であれば 404 を返す方針でもよいが、ここでは解決できたものだけで進める
            pass
        tag_ids = [t.id for t in resolved_tags]
        experts_by_tag = experts_policy_tags_crud.get_top_experts_grouped_by_tag(
            db, tag_ids=tag_ids, limit_per_tag=100
        )

        # policy_themes を構築（複数対応）
        policy_themes = [
            {
                "id": str(t.id),
                "title": t.name,
            }
            for t in resolved_tags
        ]

        # experts と relations を構築
        expert_seen = set()
        experts = []
        relations = []
        for tag_id, expert_list in experts_by_tag.items():
            for e in expert_list:
                expert_id = e.get("expert_id")
                if expert_id and expert_id not in expert_seen:
                    expert_seen.add(expert_id)
                    experts.append({
                        "id": expert_id,
                        "name": f"{e.get('last_name','')}{e.get('first_name','')}",
                        "department": e.get("department"),
                        "title": e.get("title"),
                    })
                score = e.get("relation_score")
                if score is None:
                    continue
                # 0..1 にクリップ
                try:
                    s = float(score)
                except Exception:
                    continue
                s = max(0.0, min(1.0, s))
                relations.append({
                    "policy_id": str(tag_id),
                    "expert_id": expert_id,
                    "relation_score": s,
                })

        return NetworkMapResponseDTO(
            policy_themes=policy_themes,
            experts=experts,
            relations=relations,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"マッチング処理中にエラーが発生しました: {str(e)}")


