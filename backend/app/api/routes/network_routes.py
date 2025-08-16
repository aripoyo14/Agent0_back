from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Tuple
from math import exp

from app.api.deps import get_db
from app.schemas.network import NetworkRouteRequest, NetworkRouteResponse, NetworkRoute, RouteHop, RouteBreakdown


router = APIRouter(prefix="/network_meti", tags=["Network Meti"])


def _decay(days_elapsed: float, half_life_days: float) -> float:
    if days_elapsed <= 0:
        return 1.0
    return exp(-days_elapsed / max(half_life_days, 1.0))


@router.post("/routes", response_model=NetworkRouteResponse)
async def compute_routes(payload: NetworkRouteRequest, db: Session = Depends(get_db)):
    try:
        # 1) Zに紐づく会議→参加職員Xのスコア（時間減衰＋主催=1.5/参加=1.0）
        # window_days 分のみ対象
        sql_xz = text(
            """
            SELECT mu.user_id AS x_user_id,
                   DATEDIFF(CURDATE(), m.meeting_date) AS days_ago,
                   CASE WHEN m.organized_by_user_id = mu.user_id THEN 1.5 ELSE 1.0 END AS role_weight
            FROM meetings m
            JOIN meeting_experts me ON me.meeting_id = m.id
            JOIN meeting_users mu ON mu.meeting_id = m.id
            WHERE me.expert_id = :expert_id
              AND m.meeting_date >= DATE_SUB(CURDATE(), INTERVAL :window_days DAY)
            """
        )

        rows = db.execute(sql_xz, {
            "expert_id": payload.expert_id,
            "window_days": payload.window_days,
        }).mappings().all()

        if not rows:
            return NetworkRouteResponse(routes=[])

        # 計算: X-Z スコア（会議ごとに減衰加算）
        x_to_z_score: Dict[str, float] = {}
        for r in rows:
            x_id = r["x_user_id"]
            days_ago = float(r["days_ago"] or 0)
            decay = _decay(days_ago, payload.half_life_days)
            role_weight = float(r["role_weight"] or 1.0)
            x_to_z_score[x_id] = x_to_z_score.get(x_id, 0.0) + role_weight * decay

        # 2) UとXの関係スコア（直接: U-X, 間接: U-M + M-X）
        # 内部やり取り頻度（O/T）+ 被りスコア(overlap_coef)
        # O/T 種別重み: meeting=1.5, call=1.5, email=1.0, chat=0.7, channel_post=0.7
        sql_ot_pairs = text(
            """
            WITH recent_events AS (
                SELECT id, event_type, started_at
                FROM ot_events
                WHERE started_at >= DATE_SUB(NOW(), INTERVAL :window_days DAY)
            ),
            pair_counts AS (
                SELECT LEAST(ou1.user_id, ou2.user_id) AS user_a,
                       GREATEST(ou1.user_id, ou2.user_id) AS user_b,
                       re.event_type,
                       COUNT(*) AS cnt
                FROM recent_events re
                JOIN ot_event_users ou1 ON ou1.event_id = re.id
                JOIN ot_event_users ou2 ON ou2.event_id = re.id AND ou1.user_id < ou2.user_id
                GROUP BY user_a, user_b, re.event_type
            )
            SELECT user_a, user_b,
                   SUM(
                     CASE event_type
                       WHEN 'meeting' THEN 1.5 * cnt
                       WHEN 'call' THEN 1.5 * cnt
                       WHEN 'email' THEN 1.0 * cnt
                       WHEN 'chat' THEN 0.7 * cnt
                       WHEN 'channel_post' THEN 0.7 * cnt
                       ELSE 0.0
                     END
                   ) AS freq_score
            FROM pair_counts
            GROUP BY user_a, user_b
            """
        )

        ot_pairs = db.execute(sql_ot_pairs, {"window_days": payload.window_days}).mappings().all()
        freq_score_map: Dict[Tuple[str, str], float] = {}
        for r in ot_pairs:
            a = r["user_a"]; b = r["user_b"]; s = float(r["freq_score"] or 0.0)
            freq_score_map[(a, b)] = s

        # 被りスコア
        sql_overlap = text(
            """
            SELECT user_a_id, user_b_id, score_total
            FROM relation_overlap_scores
            WHERE config_id = :config_id
            """
        )
        ov_rows = db.execute(sql_overlap, {"config_id": payload.overlap_config_id}).mappings().all()
        overlap_map: Dict[Tuple[str, str], float] = {}
        for r in ov_rows:
            a = r["user_a_id"]; b = r["user_b_id"]; s = float(r["score_total"] or 0.0)
            overlap_map[(a, b)] = s

        def pair_score(u1: str, u2: str) -> float:
            a = u1 if u1 <= u2 else u2
            b = u2 if u1 <= u2 else u1
            freq = freq_score_map.get((a, b), 0.0)
            ov = overlap_map.get((a, b), 0.0)
            return freq + payload.overlap_coef * ov

        # 3) ルート候補をスコアリング
        routes: List[NetworkRoute] = []

        # 3-1) U -> X -> Z（媒介者なし）
        for x_user_id, xz in x_to_z_score.items():
            ux = pair_score(payload.user_id, x_user_id)
            total = ux + xz
            if total <= 0:
                continue
            routes.append(
                NetworkRoute(
                    path=[
                        RouteHop(id=payload.user_id, type="user"),
                        RouteHop(id=x_user_id, type="user"),
                        RouteHop(id=payload.expert_id, type="expert"),
                    ],
                    score=total,
                    breakdown=RouteBreakdown(ux_score=ux, xz_score=xz),
                )
            )

        # 3-2) U -> M -> X -> Z（媒介者1人）
        # M 候補は O/T と被りスコアから得られる U の隣接ノードとし、X へもスコアがあるものに限定
        # 隣接の抽出
        neighbors: Dict[str, float] = {}
        for (a, b), s in freq_score_map.items():
            if a == payload.user_id:
                neighbors[b] = max(neighbors.get(b, 0.0), s + payload.overlap_coef * overlap_map.get((a, b), 0.0))
            elif b == payload.user_id:
                neighbors[a] = max(neighbors.get(a, 0.0), s + payload.overlap_coef * overlap_map.get((a, b), 0.0))

        for m_user_id, um in neighbors.items():
            if m_user_id == payload.user_id:
                continue
            # M -> X スコアが存在する X を対象
            for x_user_id, xz in x_to_z_score.items():
                if m_user_id == x_user_id:
                    continue
                mx = pair_score(m_user_id, x_user_id)
                if mx <= 0:
                    continue
                total = um + mx + xz
                routes.append(
                    NetworkRoute(
                        path=[
                            RouteHop(id=payload.user_id, type="user"),
                            RouteHop(id=m_user_id, type="user"),
                            RouteHop(id=x_user_id, type="user"),
                            RouteHop(id=payload.expert_id, type="expert"),
                        ],
                        score=total,
                        breakdown=RouteBreakdown(um_score=um, mx_score=mx, xz_score=xz),
                    )
                )

        # 4) 上位 N を返す
        routes.sort(key=lambda r: r.score, reverse=True)
        top = routes[: payload.max_results]
        return NetworkRouteResponse(routes=top)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ルート計算中にエラー: {str(e)}")


