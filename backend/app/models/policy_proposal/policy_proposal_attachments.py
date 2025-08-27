# app/models/policy_proposal/policy_proposal_attachment.py
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from datetime import datetime, timezone, timedelta
from urllib.parse import unquote
import uuid

# 日本標準時（JST）
JST = timezone(timedelta(hours=9))

class PolicyProposalAttachment(Base):
    """
    - 政策案に紐づく添付ファイル情報を格納するモデル。
    - 実ファイルの保存はAzure Blobを想定し、ここではメタ情報のみ保持。
    """

    __tablename__ = "policy_proposal_attachments"

    # 主キー：UUID
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 対象の政策案ID（外部キー、CASCADEはDB定義側で付与推奨）
    policy_proposal_id = Column(CHAR(36), ForeignKey("policy_proposals.id"), nullable=False, index=True)

    # 画面表示用のファイル名（例：報告書.pdf）
    file_name = Column(String(255), nullable=False)

    # ストレージ上の保存URL（署名付き/公開URLを想定）
    file_url = Column(String(2048), nullable=False)

    # MIMEタイプ（例：application/pdf） 任意
    file_type = Column(String(50), nullable=True)

    # ファイルサイズ（バイト） 任意
    file_size = Column(Integer, nullable=True)

    # アップロード実行ユーザー（users.id） 任意
    uploaded_by_user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=True, index=True)

    # アップロード日時（JST）
    uploaded_at = Column(DateTime, default=lambda: datetime.now(JST))

    # 親へのリレーション（逆参照）
    proposal = relationship("PolicyProposal", back_populates="attachments")

    def get_blob_name(self) -> str:
        """
        file_urlからblob名を抽出する（既存ファイル対応）
        
        Returns:
            str: blob名（例: policy_proposals/{proposal_id}/{filename}）
        """
        try:
            # local://パスの場合はそのまま返す
            if self.file_url.startswith('local://'):
                return self.file_url
            
            # file_urlの形式: https://blobeastasiafor9th.blob.core.windows.net/agent0/policy_proposals/{proposal_id}/{filename}
            # blob名の形式: policy_proposals/{proposal_id}/{filename}
            url_parts = self.file_url.split('/')
            
            # agent0コンテナのインデックスを探す
            try:
                container_index = url_parts.index('agent0')
                if container_index + 2 < len(url_parts):
                    folder_name = url_parts[container_index + 1]  # policy_proposals
                    proposal_id = url_parts[container_index + 2]  # proposal_id
                    filename = url_parts[container_index + 3]     # filename (URLエンコード済み)
                    
                    # URLデコードして実際のファイル名を取得
                    decoded_filename = unquote(filename)
                    
                    return f"{folder_name}/{proposal_id}/{decoded_filename}"
            except ValueError:
                # agent0が見つからない場合のフォールバック
                pass
            
            # フォールバック: 既存のロジック（ただし重複を避ける）
            if len(url_parts) >= 7:
                # URLの最後の3つの部分を取得（folder/proposal_id/filename）
                folder_name = url_parts[-3]
                proposal_id = url_parts[-2]
                filename = url_parts[-1]  # URLエンコード済み
                
                # URLデコードして実際のファイル名を取得
                decoded_filename = unquote(filename)
                
                return f"{folder_name}/{proposal_id}/{decoded_filename}"
            elif len(url_parts) >= 3:
                # 最後の2つの部分を取得（proposal_id/filename）
                proposal_id = url_parts[-2]
                filename = url_parts[-1]  # URLエンコード済み
                
                # URLデコードして実際のファイル名を取得
                decoded_filename = unquote(filename)
                
                return f"{proposal_id}/{decoded_filename}"
            else:
                return self.file_url
                
        except Exception:
            # エラーが発生した場合はfile_urlをそのまま返す
            return self.file_url