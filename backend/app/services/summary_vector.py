import json
from typing import Dict, Any, List, Union
from sqlalchemy.orm import Session
from app.services.vector import index, embeddings
from datetime import datetime, timezone, timedelta

# 日本標準時（JST）
JST = timezone(timedelta(hours=9))

class SummaryVectorService:
    """要約内容のベクトル化とPinecone保存を管理するサービス"""

    def __init__(self):
        self.namespace = "summaries"
        self.vector_dimension = 1536  # OpenAI text-embedding-ada-002の次元数

    def vectorize_summary(
        self, 
        summary_title: str, 
        summary_content: str, 
        expert_id: int, 
        tag_ids: Union[int, List[int], str],
        summary_id: str = None
    ) -> Dict[str, Any]:
        """
        要約内容をベクトル化してPineconeに保存する
        
        Args:
            summary_title: 要約のタイトル
            summary_content: 要約の内容
            expert_id: エキスパートID
            tag_ids: タグID（単一のint、リスト、またはカンマ区切りの文字列）
            summary_id: 要約ID（指定されない場合は自動生成）
            
        Returns:
            Dict[str, Any]: 処理結果の詳細
        """
        try:
            # summary_idが指定されていない場合は自動生成
            if summary_id is None:
                summary_id = f"summary_{datetime.now(JST).strftime('%Y%m%d_%H%M%S')}"
            
            # tag_idsを正規化（カンマ区切りの文字列に変換）
            tag_ids_str = self._normalize_tag_ids(tag_ids)
            
            # ベクトル化するテキストを作成
            text_to_embed = f"Title: {summary_title}, Summary: {summary_content}, Expert ID: {expert_id}, Tag IDs: {tag_ids_str}"
            
            # テキストをベクトル化
            print(f"🔍 要約内容をベクトル化中...")
            embedding = embeddings.embed_query(text_to_embed)
            
            # メタデータを準備
            metadata = {
                "summary_id": summary_id,
                "title": summary_title,
                "summary": summary_content,
                "expert_id": expert_id,
                "tag_ids": tag_ids_str,  # カンマ区切りの文字列
                "type": "summary",
                "created_at": datetime.now(JST).isoformat()
            }
            
            # Pineconeにベクトルを保存
            vector_data = {
                "id": summary_id,
                "values": embedding,
                "metadata": metadata
            }
            
            print(f"💾 Pineconeに要約ベクトルを保存中...")
            index.upsert(
                vectors=[vector_data],
                namespace=self.namespace
            )

            return {
                "success": True,
                "message": f"要約内容をベクトル化してPineconeに保存しました",
                "summary_id": summary_id,
                "namespace": self.namespace,
                "metadata": metadata
            }

        except Exception as e:
            print(f"❌ 要約ベクトル化エラー: {str(e)}")
            return {
                "success": False,
                "message": f"ベクトル化処理中にエラーが発生しました: {str(e)}"
            }

    def _normalize_tag_ids(self, tag_ids: Union[int, List[int], str]) -> str:
        """
        tag_idsを正規化してカンマ区切りの文字列に変換する
        
        Args:
            tag_ids: タグID（単一のint、リスト、またはカンマ区切りの文字列）
            
        Returns:
            str: カンマ区切りのタグID文字列
        """
        if isinstance(tag_ids, int):
            return str(tag_ids)
        elif isinstance(tag_ids, list):
            return ",".join(map(str, tag_ids))
        elif isinstance(tag_ids, str):
            # 既にカンマ区切りの文字列の場合はそのまま返す
            return tag_ids
        else:
            raise ValueError(f"Unsupported tag_ids type: {type(tag_ids)}")

    def _parse_tag_ids(self, tag_ids_str: str) -> List[int]:
        """
        カンマ区切りのタグID文字列を整数リストに変換する
        
        Args:
            tag_ids_str: カンマ区切りのタグID文字列
            
        Returns:
            List[int]: タグIDの整数リスト
        """
        if not tag_ids_str:
            return []
        return [int(tag_id.strip()) for tag_id in tag_ids_str.split(",") if tag_id.strip()]

    def search_similar_summaries(
        self, 
        query: str, 
        top_k: int = 5,
        expert_id: int = None,
        tag_ids: Union[int, List[int], str] = None
    ) -> List[Dict[str, Any]]:
        """
        クエリに類似した要約を検索する
        
        Args:
            query (str): 検索クエリ
            top_k (int): 返す結果の数
            expert_id (int, optional): 特定のエキスパートで絞り込み
            tag_ids (Union[int, List[int], str], optional): 特定のタグで絞り込み
            
        Returns:
            List[Dict[str, Any]]: 類似した要約のリスト
        """
        try:
            # クエリをベクトル化
            query_embedding = embeddings.embed_query(query)
            
            # フィルター条件を準備
            filter_dict = {}
            if expert_id is not None:
                filter_dict["expert_id"] = expert_id
            
            # Pineconeで類似検索
            results = index.query(
                vector=query_embedding,
                namespace=self.namespace,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict if filter_dict else None
            )
            
            # 結果を整形
            similar_summaries = []
            for match in results.matches:
                # メタデータからタグIDを取得
                tag_ids_str = match.metadata.get("tag_ids", "")
                tag_ids_list = self._parse_tag_ids(tag_ids_str)
                
                # タグIDフィルターが指定されている場合は絞り込み
                if tag_ids is not None:
                    search_tag_ids = self._parse_tag_ids(self._normalize_tag_ids(tag_ids))
                    # 共通のタグIDがあるかチェック
                    if not any(tag_id in tag_ids_list for tag_id in search_tag_ids):
                        continue
                
                similar_summaries.append({
                    "summary_id": match.metadata.get("summary_id"),
                    "title": match.metadata.get("title"),
                    "summary": match.metadata.get("summary"),
                    "expert_id": match.metadata.get("expert_id"),
                    "tag_ids": tag_ids_list,  # 整数リストとして返す
                    "tag_ids_str": tag_ids_str,  # 元の文字列も保持
                    "score": match.score,
                    "created_at": match.metadata.get("created_at")
                })
            
            return similar_summaries

        except Exception as e:
            print(f"❌ 要約検索エラー: {str(e)}")
            return []

    def delete_summary_vector(self, summary_id: str) -> Dict[str, Any]:
        """
        指定された要約IDのベクトルを削除する
        
        Args:
            summary_id: 削除する要約のID
            
        Returns:
            Dict[str, Any]: 処理結果の詳細
        """
        try:
            # Pineconeからベクトルを削除
            index.delete(
                ids=[summary_id],
                namespace=self.namespace
            )
            
            return {
                "success": True,
                "message": f"要約ベクトル (ID: {summary_id}) を削除しました",
                "summary_id": summary_id
            }

        except Exception as e:
            print(f"❌ 要約ベクトル削除エラー: {str(e)}")
            return {
                "success": False,
                "message": f"ベクトル削除中にエラーが発生しました: {str(e)}"
            }

    def get_summary_vector_statistics(self) -> Dict[str, Any]:
        """
        Pineconeの要約ベクトル統計情報を取得する
        
        Returns:
            Dict[str, Any]: 統計情報
        """
        try:
            # インデックスの統計情報を取得
            stats = index.describe_index_stats()
            
            # summariesネームスペースの情報を取得
            namespace_stats = stats.namespaces.get(self.namespace, {})
            
            return {
                "success": True,
                "total_vector_count": stats.total_vector_count,
                "summaries_vector_count": namespace_stats.get("vector_count", 0),
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": list(stats.namespaces.keys())
            }

        except Exception as e:
            print(f"❌ 統計情報取得エラー: {str(e)}")
            return {
                "success": False,
                "message": f"統計情報取得中にエラーが発生しました: {str(e)}"
            }

# サービスインスタンスを作成
summary_vector_service = SummaryVectorService()
