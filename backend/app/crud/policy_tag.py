from sqlalchemy.orm import Session
from app.models.policy_tag import PolicyTag
from typing import List, Optional

class PolicyTagCRUD:
    """政策タグのCRUD操作を提供するクラス"""

    def get_all_policy_tags(self, db: Session) -> List[PolicyTag]:
        """全ての政策タグを取得"""
        return db.query(PolicyTag).all()

    def get_policy_tag_by_id(self, db: Session, tag_id: int) -> Optional[PolicyTag]:
        """IDで政策タグを取得"""
        return db.query(PolicyTag).filter(PolicyTag.id == tag_id).first()

    def get_policy_tags_by_ids(self, db: Session, tag_ids: List[int]) -> List[PolicyTag]:
        """複数のIDで政策タグを取得"""
        return db.query(PolicyTag).filter(PolicyTag.id.in_(tag_ids)).all()

    def create_policy_tag(self, db: Session, name: str) -> PolicyTag:
        """新しい政策タグを作成"""
        policy_tag = PolicyTag(name=name)
        db.add(policy_tag)
        db.commit()
        db.refresh(policy_tag)
        return policy_tag

    def update_policy_tag(self, db: Session, tag_id: int, name: str, embedding: str = None) -> Optional[PolicyTag]:
        """政策タグを更新"""
        policy_tag = self.get_policy_tag_by_id(db, tag_id)
        if policy_tag:
            policy_tag.name = name
            if embedding is not None:
                policy_tag.embedding = embedding
            db.commit()
            db.refresh(policy_tag)
        return policy_tag

    def delete_policy_tag(self, db: Session, tag_id: int) -> bool:
        """政策タグを削除"""
        policy_tag = self.get_policy_tag_by_id(db, tag_id)
        if policy_tag:
            db.delete(policy_tag)
            db.commit()
            return True
        return False

# インスタンスを作成
policy_tag_crud = PolicyTagCRUD()
