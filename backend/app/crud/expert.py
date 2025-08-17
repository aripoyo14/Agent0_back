from __future__ import annotations
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from uuid import uuid4
from typing import Optional

from app.models.expert import Expert
from app.models.company import Company
from app.models.meeting import Meeting, MeetingUser, MeetingExpert
from app.models.user.user import User
from app.models.user.users_departments import UsersDepartments
from app.models.user.department import Department
from app.models.policy_proposal.policy_proposal_comment import PolicyProposalComment
from app.models.policy_proposal.policy_proposal import PolicyProposal
from app.models.expert_career import ExpertCareer
from app.schemas.expert import ExpertCreate
from sqlalchemy import func, and_, or_, cast, Date, Integer
from app.crud.company import get_or_create_company_by_name


def get_company_by_name(db: Session, company_name: str) -> Optional[Company]:
    return db.query(Company).filter(Company.name == company_name).first()


def get_expert_by_name_and_company(db: Session, last_name: str, first_name: str, company_id: Optional[str]) -> Optional[Expert]:
    q = db.query(Expert).filter(Expert.last_name == last_name, Expert.first_name == first_name)
    if company_id:
        q = q.filter(Expert.company_id == company_id)
    return q.first()


def create_expert(db: Session, expert_in: ExpertCreate, password_hash: str):
    """新規エキスパート作成"""
    
    # 会社名からcompany_idを解決
    company = db.query(Company).filter(Company.name == expert_in.company_name).first()
    if not company:
        # 会社が存在しない場合は新規作成
        company = Company(
            id=str(uuid4()),
            name=expert_in.company_name,
        )
        db.add(company)
        # 会社の作成はコミットする（エキスパートとは独立）
        db.commit()
        db.refresh(company)
    
    expert = Expert(
        id=str(uuid4()),
        sansan_person_id=None,
        last_name=expert_in.last_name,
        first_name=expert_in.first_name,
        company_id=company.id,
        department=expert_in.department,
        email=expert_in.email,
        password_hash=password_hash,
    )

    db.add(expert)
    # ここでコミットしない！
    # db.commit()  # ← この行を削除
    # db.refresh(expert)  # ← この行も削除
    return expert

# メールアドレスでexpertを検索する関数
def get_expert_by_email(db: Session, email: str):
    return db.query(Expert).filter(Expert.email == email).first()


def get_expert_insights(db: Session, expert_id: str):
    """
    指定 expert_id をキーに、要件に合わせて meetings 関連・policy_proposal_comments 関連の情報を集約して返す。

    集計要件:
      - evaluation: 平均（小数第1位）
      - stance: 平均（整数丸め）
    """

    # (1) meetings 関連
    # meeting_experts -> meeting_id を抽出
    meeting_ids_subq = (
        db.query(MeetingExpert.meeting_id)
        .filter(MeetingExpert.expert_id == expert_id)
        .subquery()
    )

    # 会議本体情報
    meetings = (
        db.query(
            Meeting.id.label("meeting_id"),
            Meeting.meeting_date,
            Meeting.title,
            Meeting.summary,
            Meeting.minutes_url,
            MeetingUser.user_id,
            User.last_name,
            User.first_name,
            # Meeting に evaluation/stance が存在しない場合を考慮し NULL とする
            cast(None, Integer).label("evaluation"),
            cast(None, Integer).label("stance"),
        )
        .join(meeting_ids_subq, meeting_ids_subq.c.meeting_id == Meeting.id)
        .join(MeetingUser, MeetingUser.meeting_id == Meeting.id)
        .join(User, User.id == MeetingUser.user_id)
        .order_by(Meeting.meeting_date.desc())
        .all()
    )

    # 参加ユーザーの部局（meeting_date 時点で有効なレコード）
    # 現在の users_departments は is_active のみのため、meeting_date 時点の有効レコードに最も近い定義として is_active=True を採用
    user_ids = list({m.user_id for m in meetings})
    departments_map = {}
    if user_ids:
        ud_rows = (
            db.query(UsersDepartments.user_id, Department.name, Department.section)
            .join(Department, Department.id == UsersDepartments.department_id)
            .filter(UsersDepartments.user_id.in_(user_ids), UsersDepartments.is_active == True)
            .all()
        )
        for r in ud_rows:
            departments_map.setdefault(r.user_id, []).append((r.name, r.section))

    # その会議日時点でのエキスパートの会社・部署・役職を取得するため、meeting_date ごとに career を解決
    # ルール: start_date <= meeting_date <= end_date を優先、なければ start_date<=meeting_date で最も近いもの、
    # いずれも無ければ is_current=True を fallback、最終手段として Expert テーブルの直接属性
    career_rows = []
    if meetings:
        distinct_dates = sorted({m.meeting_date for m in meetings})
        for d in distinct_dates:
            career = (
                db.query(ExpertCareer)
                .filter(
                    ExpertCareer.expert_id == expert_id,
                    or_(
                        and_(
                            ExpertCareer.start_date.isnot(None),
                            ExpertCareer.end_date.isnot(None),
                            ExpertCareer.start_date <= d,
                            ExpertCareer.end_date >= d,
                        ),
                        and_(
                            ExpertCareer.start_date.isnot(None),
                            ExpertCareer.end_date.is_(None),
                            ExpertCareer.start_date <= d,
                        ),
                        ExpertCareer.is_current == True,
                    ),
                )
                .order_by(
                    # 区間一致を優先、その後 start_date/end_date のNULLを最後にしつつ新しい順
                    (ExpertCareer.end_date.is_(None)).asc(),
                    ExpertCareer.end_date.desc(),
                    (ExpertCareer.start_date.is_(None)).asc(),
                    ExpertCareer.start_date.desc(),
                )
                .first()
            )
            if career:
                career_rows.append((d, career.company_name, career.department_name, career.title))

    # Expert テーブルからの直接属性（fallback 用）
    expert_row = db.query(Expert).filter(Expert.id == expert_id).first()
    expert_company_name = None
    if expert_row and expert_row.company_id:
        comp = db.query(Company).filter(Company.id == expert_row.company_id).first()
        if comp:
            expert_company_name = comp.name

    date_to_career = {d: {"company": c, "dept": dep, "title": t} for d, c, dep, t in career_rows}

    # meetings を meeting_id ごとにまとめ、participants 配列を構築
    meetings_by_id = {}
    for row in meetings:
        key = row.meeting_id
        if key not in meetings_by_id:
            meetings_by_id[key] = {
                "meeting_id": row.meeting_id,
                "meeting_date": row.meeting_date,
                "title": row.title,
                "summary": row.summary,
                "minutes_url": row.minutes_url,
                "evaluation": row.evaluation,
                "stance": row.stance,
                "participants": [],
                "expert_company_name": None,
                "expert_department_name": None,
                "expert_title": None,
            }
        # その会議日のキャリア情報を付与（なければ Expert テーブルの属性をfallback）
        career_info = date_to_career.get(row.meeting_date)
        if career_info:
            meetings_by_id[key]["expert_company_name"] = career_info["company"]
            meetings_by_id[key]["expert_department_name"] = career_info["dept"]
            meetings_by_id[key]["expert_title"] = career_info["title"]
        elif expert_row:
            meetings_by_id[key]["expert_company_name"] = expert_company_name
            meetings_by_id[key]["expert_department_name"] = expert_row.department
            meetings_by_id[key]["expert_title"] = expert_row.title
        dept = None
        ud = departments_map.get(row.user_id)
        if ud:
            # 同一ユーザーに複数部署が付いている場合は一つ目を採用
            name, section = ud[0]
            dept = {"department_name": name, "department_section": section}
        meetings_by_id[key]["participants"].append({
            "user_id": row.user_id,
            "last_name": row.last_name,
            "first_name": row.first_name,
            "department": dept,
        })

    meetings_out = list(meetings_by_id.values())

    # (2) policy_proposals 関連
    comments = (
        db.query(
            PolicyProposalComment.policy_proposal_id,
            PolicyProposal.title.label("policy_title"),
            PolicyProposalComment.comment_text,
            PolicyProposalComment.posted_at,
            PolicyProposalComment.like_count,
            PolicyProposalComment.evaluation,
            PolicyProposalComment.stance,
        )
        .join(PolicyProposal, PolicyProposal.id == PolicyProposalComment.policy_proposal_id)
        .filter(
            # 既存モデルの制約（admin/staff/contributor/viewer）と要件（experts）を両立
            or_(
                PolicyProposalComment.author_type == 'experts',
                PolicyProposalComment.author_type.in_(['contributor', 'viewer'])
            ),
            PolicyProposalComment.parent_comment_id.is_(None),
            PolicyProposalComment.author_id == expert_id,
            PolicyProposalComment.is_deleted == False,
        )
        .order_by(PolicyProposalComment.posted_at.desc())
        .all()
    )

    # (3) 集計: meetings と comments の evaluation / stance を平均
    eval_values = []
    stance_values = []

    # Meeting 側は現在 None のため将来の拡張に備えて残す
    for m in meetings_out:
        if m.get("evaluation") is not None:
            eval_values.append(float(m["evaluation"]))
        if m.get("stance") is not None:
            stance_values.append(float(m["stance"]))

    for c in comments:
        if c.evaluation is not None:
            eval_values.append(float(c.evaluation))
        if c.stance is not None:
            stance_values.append(float(c.stance))

    evaluation_average = round(sum(eval_values) / len(eval_values), 1) if eval_values else None
    stance_average = int(round(sum(stance_values) / len(stance_values))) if stance_values else None

    return {
        "expert_id": expert_id,
        "meetings": meetings_out,
        "policy_comments": [
            {
                "policy_proposal_id": r.policy_proposal_id,
                "policy_title": r.policy_title,
                "comment_text": r.comment_text,
                "posted_at": r.posted_at,
                "like_count": r.like_count,
                "evaluation": r.evaluation,
                "stance": r.stance,
            }
            for r in comments
        ],
        "evaluation_average": evaluation_average,
        "stance_average": stance_average,
    }