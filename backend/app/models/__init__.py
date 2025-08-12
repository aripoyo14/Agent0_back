# app/models/__init__.py

"""
このファイルは、SQLAlchemyのメタデータに全てのモデルを登録するための初期化モジュールです。
"""

# ユーザーモデル（経産省職員など）
from .user import User
from .company import Company
from .expert import Expert
from .expert_activity import ExpertActivity

# 政策案本体（タイトル・本文・ステータスなど）
from .policy_proposal import PolicyProposal

# 政策案コメント（投稿・返信など）
from .policy_proposal.policy_proposal_comment import PolicyProposalComment

# 政策案添付ファイル
from .policy_proposal.policy_proposal_attachments import PolicyProposalAttachment