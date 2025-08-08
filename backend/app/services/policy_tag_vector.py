import os
import json
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.crud.policy_tag import policy_tag_crud
from app.services.vector import index, embeddings
from app.models.policy_tag import PolicyTag

class PolicyTagVectorService:
    """政策タグのベクトル化とPinecone保存を管理するサービス"""

    def __init__(self):
        self.namespace = "policy_tags"
        self.vector_dimension = 1536  # OpenAI text-embedding-ada-002の次元数

    def vectorize_policy_tags(self, db: Session) -> Dict[str, Any]:
        """
        MySQLのpolicy_tagsテーブルから全てのデータを取得し、
        ベクトル化してPineconeに保存する
        
        Returns:
            Dict[str, Any]: 処理結果の詳細
        """
        try:
            # MySQLから全てのpolicy_tagsを取得
            policy_tags = policy_tag_crud.get_all_policy_tags(db)
            
            if not policy_tags:
                return {
                    "success": False,
                    "message": "policy_tagsテーブルにデータが存在しません",
                    "processed_count": 0
                }

            # ベクトル化用のデータを準備
            vectors_to_upsert = []
            texts_to_embed = []
            
            for tag in policy_tags:
                # idとnameを組み合わせたテキストを作成
                text = f"ID: {tag.id}, Name: {tag.name}"
                texts_to_embed.append(text)
                
                # メタデータを準備
                metadata = {
                    "tag_id": tag.id,
                    "tag_name": tag.name,
                    "type": "policy_tag",
                    "created_at": tag.created_at.isoformat() if tag.created_at else None
                }
                
                vectors_to_upsert.append({
                    "id": f"policy_tag_{tag.id}",
                    "metadata": metadata
                })

            # テキストをベクトル化
            print(f"🔍 {len(texts_to_embed)}個の政策タグをベクトル化中...")
            embeddings_list = embeddings.embed_documents(texts_to_embed)
            
            # ベクトルデータを準備し、MySQLとPineconeの両方に保存
            for i, embedding in enumerate(embeddings_list):
                vectors_to_upsert[i]["values"] = embedding
                
                # MySQLのembeddingカラムにベクトルデータを保存
                tag = policy_tags[i]
                embedding_data = {
                    "vector": embedding,
                    "text": texts_to_embed[i],
                    "metadata": vectors_to_upsert[i]["metadata"]
                }
                tag.embedding = json.dumps(embedding_data, ensure_ascii=False)
            
            # MySQLの変更をコミット
            db.commit()

            # Pineconeにベクトルを保存
            print(f"💾 Pineconeに{len(vectors_to_upsert)}個のベクトルを保存中...")
            index.upsert(
                vectors=vectors_to_upsert,
                namespace=self.namespace
            )

            return {
                "success": True,
                "message": f"{len(vectors_to_upsert)}個の政策タグをベクトル化してPineconeに保存しました",
                "processed_count": len(vectors_to_upsert),
                "namespace": self.namespace
            }

        except Exception as e:
            print(f"❌ 政策タグのベクトル化エラー: {str(e)}")
            return {
                "success": False,
                "message": f"ベクトル化処理中にエラーが発生しました: {str(e)}",
                "processed_count": 0
            }

    def vectorize_single_policy_tag(self, db: Session, tag_id: int) -> Dict[str, Any]:
        """
        指定されたIDの政策タグをベクトル化してPineconeに保存する
        
        Args:
            db: データベースセッション
            tag_id: ベクトル化するタグのID
            
        Returns:
            Dict[str, Any]: 処理結果の詳細
        """
        try:
            # 指定されたIDの政策タグを取得
            policy_tag = policy_tag_crud.get_policy_tag_by_id(db, tag_id)
            
            if not policy_tag:
                return {
                    "success": False,
                    "message": f"ID {tag_id} の政策タグが見つかりません",
                    "processed_count": 0
                }

            # idとnameを組み合わせたテキストを作成
            text = f"ID: {policy_tag.id}, Name: {policy_tag.name}"
            
            # テキストをベクトル化
            print(f"🔍 政策タグ (ID: {tag_id}) をベクトル化中...")
            embedding = embeddings.embed_query(text)
            
            # メタデータを準備
            metadata = {
                "tag_id": policy_tag.id,
                "tag_name": policy_tag.name,
                "type": "policy_tag",
                "created_at": policy_tag.created_at.isoformat() if policy_tag.created_at else None
            }
            
            # MySQLのembeddingカラムにベクトルデータを保存
            embedding_data = {
                "vector": embedding,
                "text": text,
                "metadata": metadata
            }
            policy_tag.embedding = json.dumps(embedding_data, ensure_ascii=False)
            db.commit()
            
            # Pineconeにベクトルを保存
            vector_data = {
                "id": f"policy_tag_{policy_tag.id}",
                "values": embedding,
                "metadata": metadata
            }
            
            print(f"💾 Pineconeに政策タグ (ID: {tag_id}) のベクトルを保存中...")
            index.upsert(
                vectors=[vector_data],
                namespace=self.namespace
            )

            return {
                "success": True,
                "message": f"政策タグ (ID: {tag_id}) をベクトル化してPineconeに保存しました",
                "processed_count": 1,
                "namespace": self.namespace
            }

        except Exception as e:
            print(f"❌ 政策タグ (ID: {tag_id}) のベクトル化エラー: {str(e)}")
            return {
                "success": False,
                "message": f"ベクトル化処理中にエラーが発生しました: {str(e)}",
                "processed_count": 0
            }

    def search_similar_policy_tags(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        クエリに類似した政策タグを検索する
        
        Args:
            query (str): 検索クエリ
            top_k (int): 返す結果の数
            
        Returns:
            List[Dict[str, Any]]: 類似した政策タグのリスト
        """
        try:
            # クエリをベクトル化
            query_embedding = embeddings.embed_query(query)
            
            # Pineconeで類似検索
            results = index.query(
                vector=query_embedding,
                namespace=self.namespace,
                top_k=top_k,
                include_metadata=True
            )
            
            # 結果を整形
            similar_tags = []
            for match in results.matches:
                similar_tags.append({
                    "tag_id": match.metadata.get("tag_id"),
                    "tag_name": match.metadata.get("tag_name"),
                    "score": match.score,
                    "created_at": match.metadata.get("created_at")
                })
            
            return similar_tags

        except Exception as e:
            print(f"❌ 政策タグ検索エラー: {str(e)}")
            return []

    def delete_policy_tag_vectors(self, tag_ids: List[int]) -> Dict[str, Any]:
        """
        指定されたIDの政策タグベクトルをPineconeから削除する
        
        Args:
            tag_ids (List[int]): 削除するタグのIDリスト
            
        Returns:
            Dict[str, Any]: 削除結果
        """
        try:
            # 削除するベクトルのIDを準備
            vector_ids = [f"policy_tag_{tag_id}" for tag_id in tag_ids]
            
            # Pineconeから削除
            index.delete(
                ids=vector_ids,
                namespace=self.namespace
            )
            
            return {
                "success": True,
                "message": f"{len(vector_ids)}個の政策タグベクトルを削除しました",
                "deleted_count": len(vector_ids)
            }

        except Exception as e:
            print(f"❌ 政策タグベクトル削除エラー: {str(e)}")
            return {
                "success": False,
                "message": f"ベクトル削除中にエラーが発生しました: {str(e)}",
                "deleted_count": 0
            }

    def get_vector_statistics(self) -> Dict[str, Any]:
        """
        Pineconeのベクトル統計情報を取得する
        
        Returns:
            Dict[str, Any]: 統計情報
        """
        try:
            # インデックスの統計情報を取得
            stats = index.describe_index_stats()
            
            # policy_tagsネームスペースの情報を取得
            namespace_stats = stats.namespaces.get(self.namespace, {})
            
            return {
                "success": True,
                "total_vector_count": stats.total_vector_count,
                "policy_tags_vector_count": namespace_stats.get("vector_count", 0),
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

# インスタンスを作成
policy_tag_vector_service = PolicyTagVectorService()
