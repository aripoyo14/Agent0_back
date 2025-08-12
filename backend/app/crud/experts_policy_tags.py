from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.experts_policy_tags import ExpertsPolicyTag


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


experts_policy_tags_crud = ExpertsPolicyTagsCRUD()


