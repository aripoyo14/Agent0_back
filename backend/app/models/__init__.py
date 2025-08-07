# app/models/__init__.py

"""
このファイルは、SQLAlchemyのメタデータに全てのモデルを登録するための初期化モジュールです。
"""

# ユーザーモデル（経産省職員など）
from .user import User

# 政策案本体（タイトル・本文・ステータスなど）
from .policy_proposal import PolicyProposal

# 政策案コメント（投稿・返信など）
from .policy_proposal.policy_proposal_comment import PolicyProposalComment