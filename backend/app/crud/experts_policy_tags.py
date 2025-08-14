from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.experts_policy_tags import ExpertsPolicyTag
from app.models.expert import Expert
from app.models.company import Company


class ExpertsPolicyTagsCRUD:
    """experts_policy_tags テーブルのCRUD"""

    def create(self, db: Session, *, expert_id: str, policy_tag_id: int, relation_score: float) -> ExpertsPolicyTag:
        record = ExpertsPolicyTag(expert_id=expert_id, policy_tag_id=policy_tag_id, relation_score=relation_score)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def bulk_create(self, db: Session, records: List[ExpertsPolicyTag]) -> None:
        if not records:
            return
        db.add_all(records)
        db.commit()

    def delete_by_expert_and_tags(self, db: Session, *, expert_id: str, tag_ids: List[int]) -> int:
        q = db.query(ExpertsPolicyTag).filter(
            ExpertsPolicyTag.expert_id == expert_id,
            ExpertsPolicyTag.policy_tag_id.in_(tag_ids),
        )
        count = q.count()
        q.delete(synchronize_session=False)
        db.commit()
        return count

    def get_by_expert_and_tags(self, db: Session, *, expert_id: str, tag_ids: List[int]) -> List[ExpertsPolicyTag]:
        if not tag_ids:
            return []
        return (
            db.query(ExpertsPolicyTag)
            .filter(
                ExpertsPolicyTag.expert_id == expert_id,
                ExpertsPolicyTag.policy_tag_id.in_(tag_ids),
            )
            .all()
        )

    def upsert_ewma(
        self,
        db: Session,
        *,
        expert_id: str,
        tag_scores: Dict[int, float],
        alpha: float,
    ) -> int:
        if not tag_scores:
            return 0

        # 既存レコードを一括取得
        existing = self.get_by_expert_and_tags(db, expert_id=expert_id, tag_ids=list(tag_scores.keys()))
        existing_by_tag: Dict[int, ExpertsPolicyTag] = {rec.policy_tag_id: rec for rec in existing}

        upsert_count = 0
        new_records: List[ExpertsPolicyTag] = []

        for tag_id, score_now in tag_scores.items():
            score_now = float(score_now)
            if tag_id in existing_by_tag:
                rec = existing_by_tag[tag_id]
                old = float(rec.relation_score)
                ewma = (1.0 - alpha) * old + alpha * score_now
                # DECIMAL(3,2)に丸めて保存
                rec.relation_score = round(ewma, 2)
                upsert_count += 1
            else:
                new_records.append(
                    ExpertsPolicyTag(
                        expert_id=expert_id,
                        policy_tag_id=tag_id,
                        relation_score=round(score_now, 2),
                    )
                )
                upsert_count += 1

        if new_records:
            db.add_all(new_records)
        db.commit()
        return upsert_count

    def get_top_experts_grouped_by_tag(
        self,
        db: Session,
        *,
        tag_ids: List[int],
        limit_per_tag: int = 100,
    ) -> Dict[int, List[Dict]]:
        """
        指定したタグごとに、relation_score の降順で最大 limit_per_tag 件の専門家情報を取得して返す。

        Returns:
            Dict[int, List[Dict]]: { policy_tag_id: [ { expert_id, last_name, first_name, department, title, company_id, company_name, relation_score }, ... ] }
        """
        if not tag_ids:
            return {}

        results: Dict[int, List[Dict]] = {}
        for tag_id in tag_ids:
            # JOIN: experts_policy_tags -> experts -> companies(optional)
            q = (
                db.query(
                    ExpertsPolicyTag.policy_tag_id,
                    ExpertsPolicyTag.relation_score,
                    Expert.id.label("expert_id"),
                    Expert.last_name,
                    Expert.first_name,
                    Expert.department,
                    Expert.title,
                    Expert.company_id,
                )
                .join(Expert, Expert.id == ExpertsPolicyTag.expert_id)
                .filter(ExpertsPolicyTag.policy_tag_id == tag_id)
                .order_by(ExpertsPolicyTag.relation_score.desc())
                .limit(limit_per_tag)
            )

            rows = q.all()
            experts_list: List[Dict] = []
            # 会社名解決（必要な company_id のみに絞って1回の SELECT で取得）
            company_ids = [row.company_id for row in rows if row.company_id]
            company_map: Dict[str, Company] = {}
            if company_ids:
                companies = db.query(Company).filter(Company.id.in_(company_ids)).all()
                company_map = {c.id: c for c in companies}

            for row in rows:
                company_name = None
                if row.company_id and row.company_id in company_map:
                    company_name = company_map[row.company_id].name
                experts_list.append(
                    {
                        "expert_id": row.expert_id,
                        "last_name": row.last_name,
                        "first_name": row.first_name,
                        "department": row.department,
                        "title": row.title,
                        "company_id": row.company_id,
                        "company_name": company_name,
                        "relation_score": float(row.relation_score) if row.relation_score is not None else None,
                    }
                )

            results[tag_id] = experts_list

        return results


experts_policy_tags_crud = ExpertsPolicyTagsCRUD()


