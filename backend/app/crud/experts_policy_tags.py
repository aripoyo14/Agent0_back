from typing import List
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


experts_policy_tags_crud = ExpertsPolicyTagsCRUD()


