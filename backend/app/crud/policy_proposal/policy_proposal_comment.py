# app/crud/policy_proposal/policy_proposal_comment.py
"""
 - 政策案コメントに関するDB操作（CRUD）を定義するモジュール。
 - 主に SQLAlchemy を通じて PolicyProposalComment モデルとやり取りする。
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.policy_proposal.policy_proposal_comment import PolicyProposalComment
from app.models.policy_proposal.policy_proposal import PolicyProposal
from app.models.user.user import User
from app.models.expert import Expert
from app.schemas.policy_proposal_comment import (
    PolicyProposalCommentCreate,
    PolicyWithComments
)
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from typing import Optional, List

# 日本標準時（JST）
JST = timezone(timedelta(hours=9))

# 有効な投稿者タイプ一覧
VALID_AUTHOR_TYPES = ["admin", "staff", "contributor", "viewer"]

def create_comment(db: Session, comment_in: PolicyProposalCommentCreate) -> PolicyProposalComment:
    """
    新規コメントをDBに登録する処理。
    """

    # 1. 投稿者タイプのバリデーション
    if comment_in.author_type not in VALID_AUTHOR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"author_type は {VALID_AUTHOR_TYPES} のいずれかである必要があります。"
        )

    # 2. 閲覧専用ユーザー（viewer）は投稿禁止
    if comment_in.author_type == "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="閲覧専用ユーザー（viewer）はコメントを投稿できません。"
        )

    # 3. PolicyProposalComment モデルのインスタンスを作成
    comment = PolicyProposalComment(
        id=str(uuid4()),
        policy_proposal_id=str(comment_in.policy_proposal_id),
        author_type=comment_in.author_type,
        author_id=str(comment_in.author_id),
        comment_text=comment_in.comment_text,
        parent_comment_id=str(comment_in.parent_comment_id) if comment_in.parent_comment_id else None,
        posted_at=datetime.now(JST),
        like_count=0,
        is_deleted=False,
        evaluation=comment_in.evaluation,
        stance=comment_in.stance
    )

    # 4. DBに保存
    db.add(comment)
    db.commit()
    db.refresh(comment)

    # 5. 投稿者名を設定して返却
    comment = get_comment_by_id(db, comment.id)
    return comment

def create_reply(
    db: Session,
    *,
    parent_comment_id: str,
    author_type: str,
    author_id: str,
    comment_text: str,
) -> PolicyProposalComment:
    """
    既存コメントに対する返信を作成する。
    親コメントが論理削除されていても、スレッド履歴のため返信は許可する。
    """
    if author_type not in VALID_AUTHOR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"author_type は {VALID_AUTHOR_TYPES} のいずれかである必要があります。",
        )

    parent = (
        db.query(PolicyProposalComment)
        .filter(PolicyProposalComment.id == parent_comment_id)
        .first()
    )
    if parent is None:
        raise HTTPException(status_code=404, detail="Parent comment not found")

    reply = PolicyProposalComment(
        id=str(uuid4()),
        policy_proposal_id=str(parent.policy_proposal_id),
        author_type=author_type,
        author_id=str(author_id),
        comment_text=comment_text,
        parent_comment_id=str(parent_comment_id),
        posted_at=datetime.now(JST),
        like_count=0,
        is_deleted=False,
        evaluation=None,  # 返信には評価は含めない
        stance=None
    )

    db.add(reply)
    db.commit()
    db.refresh(reply)
    
    # 投稿者名を設定して返却
    reply = get_comment_by_id(db, reply.id)
    return reply

def get_comment_by_id(db: Session, comment_id: str) -> Optional[PolicyProposalComment]:
    """
    コメントID（UUID文字列）で単一取得。論理削除は除外。
    投稿者名（author_name）も含めて取得。
    """
    from sqlalchemy import case, func
    from app.models.user.user import User
    from app.models.expert import Expert
    
    # 投稿者名を取得するためのサブクエリ
    author_name_subquery = (
        db.query(
            PolicyProposalComment.id,
            case(
                (PolicyProposalComment.author_type.in_(['admin', 'staff']), 
                 func.concat(User.last_name, ' ', User.first_name)),
                (PolicyProposalComment.author_type == 'contributor', 
                 func.concat(Expert.last_name, ' ', Expert.first_name)),
                else_=None
            ).label('author_name')
        )
        .outerjoin(User, 
                   (PolicyProposalComment.author_id == User.id) & 
                   (PolicyProposalComment.author_type.in_(['admin', 'staff'])))
        .outerjoin(Expert, 
                   (PolicyProposalComment.author_id == Expert.id) & 
                   (PolicyProposalComment.author_type == 'contributor'))
        .subquery()
    )
    
    # メインクエリ：コメントと投稿者名を結合
    result = (
        db.query(
            PolicyProposalComment,
            author_name_subquery.c.author_name
        )
        .join(author_name_subquery, PolicyProposalComment.id == author_name_subquery.c.id)
        .filter(
            PolicyProposalComment.id == comment_id,
            PolicyProposalComment.is_deleted == False,
        )
        .first()
    )
    
    if result:
        comment, author_name = result
        comment.author_name = author_name
        return comment
    
    return None

def list_comments_by_policy_proposal_id(
    db: Session,
    policy_proposal_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
) -> List[PolicyProposalComment]:
    """
    政策案ID（文字列）に紐づくコメント一覧を新しい順で取得。
    論理削除は除外。簡易ページング対応。
    投稿者名（author_name）も含めて取得。
    """
    from sqlalchemy import case, func
    from app.models.user.user import User
    from app.models.expert import Expert
    
    # 投稿者名を取得するためのサブクエリ
    author_name_subquery = (
        db.query(
            PolicyProposalComment.id,
            case(
                (PolicyProposalComment.author_type.in_(['admin', 'staff']), 
                 func.concat(User.last_name, ' ', User.first_name)),
                (PolicyProposalComment.author_type == 'contributor', 
                 func.concat(Expert.last_name, ' ', Expert.first_name)),
                else_=None
            ).label('author_name')
        )
        .outerjoin(User, 
                   (PolicyProposalComment.author_id == User.id) & 
                   (PolicyProposalComment.author_type.in_(['admin', 'staff'])))
        .outerjoin(Expert, 
                   (PolicyProposalComment.author_id == Expert.id) & 
                   (PolicyProposalComment.author_type == 'contributor'))
        .subquery()
    )
    
    # メインクエリ：コメントと投稿者名を結合
    comments = (
        db.query(
            PolicyProposalComment,
            author_name_subquery.c.author_name
        )
        .join(author_name_subquery, PolicyProposalComment.id == author_name_subquery.c.id)
        .filter(
            PolicyProposalComment.policy_proposal_id == policy_proposal_id,
            PolicyProposalComment.is_deleted == False,
        )
        .order_by(PolicyProposalComment.posted_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    # 結果をPolicyProposalCommentオブジェクトに変換し、author_nameを設定
    result = []
    for comment, author_name in comments:
        comment.author_name = author_name
        result.append(comment)
    
    return result

# 追加機能：指定ユーザーが投稿した政策案に紐づくコメント一覧を取得
def list_comments_for_policies_by_user(
    db: Session,
    user_id: str,
    *,
    limit: int = 20,
    offset: int = 0
) -> List[PolicyWithComments]:
    """
    指定ユーザーが作成した政策案ごとに、
    そこに投稿されたコメント一覧を返す。
    """

    # 1. ユーザーが作成した政策案を取得（ページングあり）
    policies = (
        db.query(PolicyProposal)
        .filter(PolicyProposal.published_by_user_id == user_id)
        .order_by(PolicyProposal.published_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    results: List[PolicyWithComments] = []

    # 2. 各政策案に紐づくコメントを取得（投稿者名付き）
    for policy in policies:
        # 投稿者名を取得するためのサブクエリ
        author_name_subquery = (
            db.query(
                PolicyProposalComment.id,
                case(
                    (PolicyProposalComment.author_type.in_(['admin', 'staff']), 
                     func.concat(User.last_name, ' ', User.first_name)),
                    (PolicyProposalComment.author_type == 'contributor', 
                     func.concat(Expert.last_name, ' ', Expert.first_name)),
                    else_=None
                ).label('author_name')
            )
            .outerjoin(User, 
                       (PolicyProposalComment.author_id == User.id) & 
                       (PolicyProposalComment.author_type.in_(['admin', 'staff'])))
            .outerjoin(Expert, 
                       (PolicyProposalComment.author_id == Expert.id) & 
                       (PolicyProposalComment.author_type == 'contributor'))
            .subquery()
        )
        
        # メインクエリ：コメントと投稿者名を結合
        comments_with_names = (
            db.query(
                PolicyProposalComment,
                author_name_subquery.c.author_name
            )
            .join(author_name_subquery, PolicyProposalComment.id == author_name_subquery.c.id)
            .filter(
                PolicyProposalComment.policy_proposal_id == str(policy.id),
                PolicyProposalComment.is_deleted == False,
            )
            .order_by(PolicyProposalComment.posted_at.desc())
            .all()
        )
        
        # 結果をPolicyProposalCommentオブジェクトに変換し、author_nameを設定
        comments = []
        for comment, author_name in comments_with_names:
            comment.author_name = author_name
            comments.append(comment)

        # 3. 最新コメント日時の取得
        latest_commented_at = (
            db.query(func.max(PolicyProposalComment.posted_at))
            .filter(
                PolicyProposalComment.policy_proposal_id == str(policy.id),
                PolicyProposalComment.is_deleted == False,
            )
            .scalar()
        )

        # 4. スキーマ形式に変換して追加
        results.append(PolicyWithComments(
            policy_proposal_id=policy.id,
            title=policy.title,
            status=policy.status,
            published_at=policy.published_at,
            latest_commented_at=latest_commented_at,
            total_comments=len(comments),
            comments=comments
        ))

    return results


def update_comment_rating(
    db: Session,
    comment_id: str,
    evaluation: Optional[int] = None,
    stance: Optional[int] = None,
) -> Optional[PolicyProposalComment]:
    """
    コメントの評価を更新する。
    評価値の範囲チェックも行う。
    """
    # 評価値の範囲チェック
    if evaluation is not None and (evaluation < 1 or evaluation > 5):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="evaluation は 1-5 の範囲で指定してください。"
        )
    
    if stance is not None and (stance < 1 or stance > 5):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="stance は 1-5 の範囲で指定してください。"
        )
    
    # コメントの存在確認
    comment = get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # 評価を更新
    if evaluation is not None:
        comment.evaluation = evaluation
    if stance is not None:
        comment.stance = stance
    
    # 更新日時を設定 - 一時的にコメントアウト（DBマイグレーション後有効化）
    # comment.updated_at = datetime.now(JST)
    
    db.commit()
    db.refresh(comment)
    
    # 投稿者名を設定して返却
    comment = get_comment_by_id(db, comment.id)
    return comment

# コメント数取得関数
def get_comment_count_by_policy_proposal(db: Session, policy_proposal_id: str) -> int:
    """
    特定の政策提案に対するPolicyProposalComments数を取得する。
    
    Args:
        db: Database session
        policy_proposal_id: 政策提案ID
        
    Returns:
        int: その政策提案に対するコメント数
    """
    # コメント数（論理削除を除く）
    comment_count = (
        db.query(func.count(PolicyProposalComment.id))
        .filter(
            PolicyProposalComment.policy_proposal_id == policy_proposal_id,
            PolicyProposalComment.is_deleted == False
        )
        .scalar()
    ) or 0
    
    return comment_count

def get_replies_by_parent_comment_id(
    db: Session, 
    parent_comment_id: str, 
    limit: int = 20, 
    offset: int = 0
) -> List[PolicyProposalComment]:
    """
    指定された親コメントに対する返信コメント一覧を取得する。
    
    Args:
        db: Database session
        parent_comment_id: 親コメントID
        limit: 取得件数制限（デフォルト: 20）
        offset: オフセット（デフォルト: 0）
        
    Returns:
        List[PolicyProposalComment]: 返信コメント一覧
    """
    # 親コメントの存在確認
    parent_comment = get_comment_by_id(db, parent_comment_id)
    if not parent_comment:
        raise HTTPException(status_code=404, detail="Parent comment not found")
    
    # 返信コメントを取得（投稿日時の昇順でソート）
    replies = (
        db.query(PolicyProposalComment)
        .filter(
            PolicyProposalComment.parent_comment_id == parent_comment_id,
            PolicyProposalComment.is_deleted == False
        )
        .order_by(PolicyProposalComment.posted_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    # 投稿者名を設定（効率的な方法）
    for reply in replies:
        if reply.author_type == "user":
            # ユーザーの場合
            user = db.query(User).filter(User.id == reply.author_id).first()
            if user:
                reply.author_name = f"{user.last_name} {user.first_name}"
        elif reply.author_type == "expert":
            # 有識者の場合
            expert = db.query(Expert).filter(Expert.id == reply.author_id).first()
            if expert:
                reply.author_name = f"{expert.last_name} {expert.first_name}"
        else:
            # その他の場合
            reply.author_name = f"{reply.author_type} user"
    
    return replies

def get_reply_count_by_parent_comment_id(db: Session, parent_comment_id: str) -> int:
    """
    指定された親コメントに対する返信コメント数を取得する。
    
    Args:
        db: Database session
        parent_comment_id: 親コメントID
        
    Returns:
        int: 返信コメント数
    """
    # 親コメントの存在確認
    parent_comment = get_comment_by_id(db, parent_comment_id)
    if not parent_comment:
        raise HTTPException(status_code=404, detail="Parent comment not found")
    
    # 返信コメント数を取得
    reply_count = (
        db.query(func.count(PolicyProposalComment.id))
        .filter(
            PolicyProposalComment.parent_comment_id == parent_comment_id,
            PolicyProposalComment.is_deleted == False
        )
        .scalar()
    ) or 0
    
    return reply_count