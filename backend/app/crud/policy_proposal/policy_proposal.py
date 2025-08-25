# app/crud/policy_proposal/policy_proposal.py
"""
 - 政策案に関するDB操作（CRUDのうち作成・取得）を定義するモジュール。
 - 主に SQLAlchemy を通じて PolicyProposal モデルとデータベースをやり取りする。
"""

from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException, status
from datetime import datetime, timezone, timedelta

from app.models.policy_proposal.policy_proposal import PolicyProposal
from app.models.policy_proposal.policy_proposal_comment import PolicyProposalComment
from app.schemas.policy_proposal.policy_proposal import ProposalCreate
from app.models.policy_proposal.policy_proposal_attachments import PolicyProposalAttachment
from app.models.policy_tag import PolicyTag

# 日本時間（JST）のタイムゾーンを定義
JST = timezone(timedelta(hours=9))

# 新規の政策案を登録する関数
def create_proposal(db: Session, data: ProposalCreate) -> PolicyProposal:

    # 1. タイトルの重複チェック
    existing = db.query(PolicyProposal).filter(PolicyProposal.title == data.title).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="同じタイトルの政策案が既に存在します。"
        )

    # 2. PolicyProposalモデルのインスタンスを作成
    proposal = PolicyProposal(
        title=data.title,
        body=data.body,
        status=data.status,  # "draft" | "published" | "archived"
        published_by_user_id=str(data.published_by_user_id),  # CHAR(36) なので文字列化
        published_at=(datetime.now(JST) if data.status == "published" else None),
        created_at=datetime.now(JST),
        updated_at=datetime.now(JST),
    )

    # 3. DBに保存
    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    # 4. 政策タグの関連付け（新規追加）
    if data.policy_tag_ids:
        policy_tags = db.query(PolicyTag).filter(PolicyTag.id.in_(data.policy_tag_ids)).all()
        proposal.policy_tags = policy_tags
        db.commit()
        db.refresh(proposal)

    # 5. 登録した政策案オブジェクトを返す
    return proposal


def create_attachment(
    db: Session,
    *,
    policy_proposal_id: str,
    file_name: str,
    file_url: str,
    file_type: str | None,
    file_size: int | None,
    uploaded_by_user_id: str | None,
) -> PolicyProposalAttachment:
    attachment = PolicyProposalAttachment(
        policy_proposal_id=policy_proposal_id,
        file_name=file_name,
        file_url=file_url,
        file_type=file_type,
        file_size=file_size,
        uploaded_by_user_id=uploaded_by_user_id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def list_attachments_by_policy_proposal_id(
    db: Session,
    *,
    policy_proposal_id: str,
) -> list[PolicyProposalAttachment]:
    """指定した政策案に紐づく添付一覧を返す。"""
    rows = (
        db.query(PolicyProposalAttachment)
        .filter(PolicyProposalAttachment.policy_proposal_id == policy_proposal_id)
        .all()
    )
    return rows


def get_proposal(db: Session, proposal_id: str) -> Optional[PolicyProposal]:
    """
    主キー（UUID文字列）で政策案を1件取得する関数。
    見つからない場合は None を返す。
    政策タグ情報も含めて取得する。
    """
    return (
        db.query(PolicyProposal)
        .options(
            joinedload(PolicyProposal.attachments),
            joinedload(PolicyProposal.policy_tags)
        )
        .filter(PolicyProposal.id == proposal_id)
        .first()
    )


def list_proposals(
    db: Session,
    *,
    status_filter: Optional[str] = None,  # "draft" | "published" | "archived"
    q: Optional[str] = None,              # タイトル/本文の部分一致
    offset: int = 0,
    limit: int = 20,
) -> List[PolicyProposal]:
    """
    政策案の一覧を取得する関数（簡易検索付き）。
     - status でのフィルタ
     - タイトル/本文の部分一致検索
     - 新しい順（created_at DESC）
     - 政策タグ情報も含めて取得する
    """
    qs = db.query(PolicyProposal)

    if status_filter:
        qs = qs.filter(PolicyProposal.status == status_filter)

    if q:
        like = f"%{q}%"
        qs = qs.filter(
            (PolicyProposal.title.ilike(like)) |
            (PolicyProposal.body.ilike(like))
        )

    rows = (
        qs.options(
            joinedload(PolicyProposal.attachments),
            joinedload(PolicyProposal.policy_tags)
        )
        .order_by(PolicyProposal.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows


def get_user_submissions(
    db: Session,
    user_id: str,
    *,
    offset: int = 0,
    limit: int = 20,
) -> List[dict]:
    """
    ログインユーザーが投稿した政策提案の一覧を取得する関数。
    各投稿のコメント数も含めて返す。
    """
    proposals = (
        db.query(PolicyProposal)
        .options(
            joinedload(PolicyProposal.attachments),
            joinedload(PolicyProposal.policy_tags)
        )
        .filter(PolicyProposal.published_by_user_id == user_id)
        .order_by(PolicyProposal.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    results = []
    for proposal in proposals:
        comment_count = (
            db.query(func.count(PolicyProposalComment.id))
            .filter(
                PolicyProposalComment.policy_proposal_id == str(proposal.id),
                PolicyProposalComment.is_deleted == False
            )
            .scalar()
        ) or 0
        
        result = {
            "proposal": proposal,
            "comment_count": comment_count
        }
        results.append(result)
    return results

# ... existing code ...

def get_proposals_by_policy_tag(
    db: Session,
    policy_tag_id: int,
    *,
    status_filter: Optional[str] = None,  # "draft" | "published" | "archived"
    offset: int = 0,
    limit: int = 20,
) -> List[PolicyProposal]:
    """
    指定された政策テーマタグに紐づく政策案を取得する関数。
    - 政策タグIDでのフィルタ
    - status でのフィルタ（オプション）
    - 新しい順（created_at DESC）
    - 政策タグ情報も含めて取得する
    """
    qs = (
        db.query(PolicyProposal)
        .join(PolicyProposal.policy_tags)
        .filter(PolicyProposal.policy_tags.any(id=policy_tag_id))
    )

    if status_filter:
        qs = qs.filter(PolicyProposal.status == status_filter)

    rows = (
        qs.options(
            joinedload(PolicyProposal.attachments),
            joinedload(PolicyProposal.policy_tags)
        )
        .order_by(PolicyProposal.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows


def get_proposals_by_policy_tags(
    db: Session,
    policy_tag_ids: List[int],
    *,
    status_filter: Optional[str] = None,  # "draft" | "published" | "archived"
    offset: int = 0,
    limit: int = 20,
) -> List[PolicyProposal]:
    """
    指定された複数の政策テーマタグに紐づく政策案を取得する関数。
    - 複数の政策タグIDでのフィルタ（OR条件）
    - status でのフィルタ（オプション）
    - 新しい順（created_at DESC）
    - 政策タグ情報も含めて取得する
    """
    print(f" get_proposals_by_policy_tags 呼び出し:")
    print(f"   タグID: {policy_tag_ids}")
    print(f"   ステータスフィルタ: {status_filter}")
    print(f"   オフセット: {offset}")
    print(f"   リミット: {limit}")
    
    qs = (
        db.query(PolicyProposal)
        .join(PolicyProposal.policy_tags)
        .filter(PolicyProposal.policy_tags.any(PolicyTag.id.in_(policy_tag_ids)))
    )

    if status_filter:
        qs = qs.filter(PolicyProposal.status == status_filter)
        print(f"   ステータスフィルタ適用後: {qs}")

    # クエリの実行前にSQLを確認
    print(f"   最終クエリ: {qs}")
    
    rows = (
        qs.options(
            joinedload(PolicyProposal.attachments),
            joinedload(PolicyProposal.policy_tags)
        )
        .order_by(PolicyProposal.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    print(f"   取得結果: {len(rows)}件")
    for i, row in enumerate(rows[:3]):  # 最初の3件のみ表示
        print(f"     {i+1}: {row.title} (ID: {row.id})")
    
    return rows