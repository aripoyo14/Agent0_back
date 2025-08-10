import os
import json
from typing import Dict, Any, List, Union, Tuple
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from langchain_openai import OpenAIEmbeddings
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.crud.policy_tag import policy_tag_crud
from app.models.policy_tag import PolicyTag
from app.crud.experts_policy_tags import experts_policy_tags_crud
from app.models.experts_policy_tags import ExpertsPolicyTag

# 日本標準時（JST）
JST = timezone(timedelta(hours=9))

class CosmosVectorService:
    """Azure Cosmos DB for MongoDB vCoreを使用したベクトル検索サービス"""

    def __init__(self):
        # 設定を取得
        settings = get_settings()
        self.cosmos_connection_string = settings.cosmos_connection_string
        self.database_name = settings.cosmos_database_name
        self.collection_name = settings.cosmos_collection_name
        
        if not self.cosmos_connection_string:
            raise RuntimeError("COSMOS_CONNECTION_STRING is missing in environment variables")
        
        # MongoDBクライアントの初期化
        self.client = MongoClient(self.cosmos_connection_string)
        self.database: Database = self.client[self.database_name]
        self.collection: Collection = self.database[self.collection_name]
        
        # Embeddingモデルの初期化（最新の小型モデルに更新）
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        # ベクトル次元数（text-embedding-3-small は 1536 次元）
        self.vector_dimension = 1536

    def vectorize_summary(
        self, 
        summary_title: str, 
        summary_content: str, 
        expert_id: str, 
        tag_ids: Union[int, List[int], str],
        summary_id: str = None
    ) -> Dict[str, Any]:
        """
        要約内容をベクトル化してCosmos DBに保存する
        
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
            
            # ベクトル化するテキストを作成（内容のみを対象にする）
            text_to_embed = f"{summary_title}\n{summary_content}"
            
            # テキストをベクトル化
            print(f"🔍 要約内容をベクトル化中...")
            embedding = self.embeddings.embed_query(text_to_embed)
            
            # ドキュメントを準備
            document = {
                "_id": summary_id,
                "summary_id": summary_id,
                "title": summary_title,
                "summary": summary_content,
                    "expert_id": expert_id,
                "tag_ids": tag_ids_str,  # カンマ区切りの文字列
                "type": "summary",
                "vector": embedding,
                "created_at": datetime.now(JST).isoformat(),
                "updated_at": datetime.now(JST).isoformat()
            }
            
            # Cosmos DBにドキュメントを保存
            print(f"💾 Cosmos DBに要約ベクトルを保存中...")
            result = self.collection.insert_one(document)
            
            if result.inserted_id:
                return {
                    "success": True,
                    "message": f"要約内容をベクトル化してCosmos DBに保存しました",
                    "summary_id": summary_id,
                    "document_id": str(result.inserted_id),
                    "vector": embedding,
                }
            else:
                return {
                    "success": False,
                    "message": "ドキュメントの保存に失敗しました"
                }

        except Exception as e:
            print(f"❌ 要約ベクトル化エラー: {str(e)}")
            return {
                "success": False,
                "message": f"ベクトル化処理中にエラーが発生しました: {str(e)}"
            }

    # ===== 追加: 類似度計算ユーティリティと登録処理 =====

    @staticmethod
    def _cosine_similarity(vector_a: List[float], vector_b: List[float]) -> float:
        """コサイン類似度を計算"""
        if not vector_a or not vector_b:
            return 0.0
        # 長さが異なる場合は安全側で短い方に合わせる
        dim = min(len(vector_a), len(vector_b))
        a = vector_a[:dim]
        b = vector_b[:dim]
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    def register_expert_tag_similarities(
        self,
        db: Session,
        *,
        summary_vector: List[float],
        expert_id: str,
        tag_ids: List[int],
    ) -> Dict[str, Any]:
        """
        - 渡されたsummary_vectorと、MySQLのpolicy_tags.embedding（JSON）に入っているベクトルのコサイン類似度を計算
        - 結果をexperts_policy_tagsに登録
        """
        try:
            # 同一 expert × 指定タグ群 の既存レコードを削除
            experts_policy_tags_crud.delete_by_expert_and_tags(db, expert_id=expert_id, tag_ids=tag_ids)

            # タグを取得
            policy_tags = policy_tag_crud.get_policy_tags_by_ids(db, tag_ids)
            records: List[ExpertsPolicyTag] = []

            for tag in policy_tags:
                if not tag.embedding:
                    # 埋め込み未生成はスキップ
                    continue
                try:
                    payload = json.loads(tag.embedding)
                    tag_vector = payload.get("vector")
                    if not isinstance(tag_vector, list):
                        continue
                except Exception:
                    continue

                sim = self._cosine_similarity(summary_vector, tag_vector)
                # DECIMAL(3,2)に丸める
                relation_score = round(sim, 2)
                record = ExpertsPolicyTag(expert_id=expert_id, policy_tag_id=tag.id, relation_score=relation_score)
                records.append(record)

            if records:
                experts_policy_tags_crud.bulk_create(db, records)

            return {
                "success": True,
                "inserted_count": len(records),
            }
        except Exception as e:
            print(f"❌ 類似度登録エラー: {str(e)}")
            return {
                "success": False,
                "message": f"類似度登録中にエラーが発生しました: {str(e)}",
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
            query_embedding = self.embeddings.embed_query(query)
            
            # 検索パイプラインを構築
            pipeline = [
                {
                    "$search": {
                        "vectorSearch": {
                            "queryVector": query_embedding,
                            "path": "vector",
                            "numCandidates": top_k * 10,  # より多くの候補を取得
                            "limit": top_k
                        }
                    }
                }
            ]
            
            # フィルター条件を追加
            if expert_id is not None:
                pipeline.append({"$match": {"expert_id": expert_id}})
            
            # 検索実行
            results = list(self.collection.aggregate(pipeline))
            
            # 結果を整形
            similar_summaries = []
            for result in results:
                # メタデータからタグIDを取得
                tag_ids_str = result.get("tag_ids", "")
                tag_ids_list = self._parse_tag_ids(tag_ids_str)
                
                # タグIDフィルターが指定されている場合は絞り込み
                if tag_ids is not None:
                    search_tag_ids = self._parse_tag_ids(self._normalize_tag_ids(tag_ids))
                    # 共通のタグIDがあるかチェック
                    if not any(tag_id in tag_ids_list for tag_id in search_tag_ids):
                        continue
                
                similar_summaries.append({
                    "summary_id": result.get("summary_id"),
                    "title": result.get("title"),
                    "summary": result.get("summary"),
                    "expert_id": result.get("expert_id"),
                    "tag_ids": tag_ids_list,  # 整数リストとして返す
                    "tag_ids_str": tag_ids_str,  # 元の文字列も保持
                    "score": result.get("score", 0.0),
                    "created_at": result.get("created_at")
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
            # Cosmos DBからドキュメントを削除
            result = self.collection.delete_one({"_id": summary_id})
            
            if result.deleted_count > 0:
                return {
                    "success": True,
                    "message": f"要約ベクトル (ID: {summary_id}) を削除しました",
                    "summary_id": summary_id
                }
            else:
                return {
                    "success": False,
                    "message": f"要約ベクトル (ID: {summary_id}) が見つかりませんでした"
                }

        except Exception as e:
            print(f"❌ 要約ベクトル削除エラー: {str(e)}")
            return {
                "success": False,
                "message": f"ベクトル削除中にエラーが発生しました: {str(e)}"
            }

    def get_vector_statistics(self) -> Dict[str, Any]:
        """
        Cosmos DBのベクトル統計情報を取得する
        
        Returns:
            Dict[str, Any]: 統計情報
        """
        try:
            # 総ドキュメント数を取得
            total_count = self.collection.count_documents({})
            
            # 要約タイプのドキュメント数を取得
            summary_count = self.collection.count_documents({"type": "summary"})
            
            # エキスパート別の統計を取得
            expert_stats = list(self.collection.aggregate([
                {"$match": {"type": "summary"}},
                {"$group": {"_id": "$expert_id", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]))
            
            return {
                "success": True,
                "total_document_count": total_count,
                "summary_document_count": summary_count,
                "vector_dimension": self.vector_dimension,
                "expert_statistics": expert_stats,
                "database_name": self.database_name,
                "collection_name": self.collection_name
            }

        except Exception as e:
            print(f"❌ 統計情報取得エラー: {str(e)}")
            return {
                "success": False,
                "message": f"統計情報取得中にエラーが発生しました: {str(e)}"
            }

    def close_connection(self):
        """データベース接続を閉じる"""
        if self.client:
            self.client.close()

    # ========== 政策タグ関連のメソッド ==========

    def vectorize_policy_tags(self, db: Session) -> Dict[str, Any]:
        """
        MySQLのpolicy_tagsテーブルから全てのデータを取得し、
        ベクトル化してCosmos DBに保存する
        
        Args:
            db: データベースセッション
            
        Returns:
            Dict[str, Any]: 処理結果の詳細
        """
        try:
            # MySQLから全てのpolicy_tagsを取得
            policy_tags = policy_tag_crud.get_all_policy_tags(db)
            
            if not policy_tags:
                return {
                    "success": False,
                    "message": "政策タグが見つかりませんでした",
                    "processed_count": 0
                }

            print(f"📋 {len(policy_tags)}個の政策タグを処理中...")

            # ベクトル化するテキストのリストを作成
            texts_to_embed = []
            documents_to_insert = []

            for tag in policy_tags:
                # name + description + keywords を結合して表現力を強化
                parts = [tag.name or ""]
                if getattr(tag, "description", None):
                    parts.append(str(tag.description))
                if getattr(tag, "keywords", None):
                    parts.append(str(tag.keywords))
                text = "\n".join([p for p in parts if p])
                texts_to_embed.append(text)
                
                # ドキュメントのベースを準備（vectorは後で追加）
                document = {
                    "_id": f"policy_tag_{tag.id}",
                    "policy_tag_id": tag.id,
                    "name": tag.name,
                    "type": "policy_tag",
                    "text": text,
                    "created_at": tag.created_at.isoformat() if tag.created_at else datetime.now(JST).isoformat(),
                    "updated_at": datetime.now(JST).isoformat()
                }
                documents_to_insert.append(document)

            # 一括でベクトル化
            print(f"🔍 {len(texts_to_embed)}個のテキストをベクトル化中...")
            embeddings_list = self.embeddings.embed_documents(texts_to_embed)
            
            # ベクトルをドキュメントに追加
            for i, embedding in enumerate(embeddings_list):
                documents_to_insert[i]["vector"] = embedding
                
                # MySQLのembeddingカラムにも保存
                tag = policy_tags[i]
                embedding_data = {
                    "vector": embedding,
                    "text": texts_to_embed[i],
                    "metadata": {
                        "tag_id": tag.id,
                        "tag_name": tag.name,
                        "type": "policy_tag",
                        "created_at": tag.created_at.isoformat() if tag.created_at else None
                    }
                }
                tag.embedding = json.dumps(embedding_data, ensure_ascii=False)
            
            # MySQLの変更をコミット
            db.commit()

            # Cosmos DBにドキュメントを一括挿入
            print(f"💾 Cosmos DBに{len(documents_to_insert)}個のドキュメントを保存中...")
            
            # 既存のドキュメントを削除（重複を避けるため）
            self.collection.delete_many({"type": "policy_tag"})
            
            # 新しいドキュメントを挿入
            result = self.collection.insert_many(documents_to_insert)

            return {
                "success": True,
                "message": f"{len(result.inserted_ids)}個の政策タグをベクトル化してCosmos DBに保存しました",
                "processed_count": len(result.inserted_ids),
                "inserted_ids": [str(id) for id in result.inserted_ids]
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
        指定されたIDの政策タグをベクトル化してCosmos DBに保存する
        
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
            
            # テキストをベクトル化（name + description + keywords）
            print(f"🔍 政策タグ (ID: {tag_id}) をベクトル化中...")
            parts = [policy_tag.name or ""]
            if getattr(policy_tag, "description", None):
                parts.append(str(policy_tag.description))
            if getattr(policy_tag, "keywords", None):
                parts.append(str(policy_tag.keywords))
            text = "\n".join([p for p in parts if p])
            embedding = self.embeddings.embed_query(text)
            
            # ドキュメントを準備
            document = {
                "_id": f"policy_tag_{policy_tag.id}",
                "policy_tag_id": policy_tag.id,
                "name": policy_tag.name,
                "type": "policy_tag",
                "text": text,
                "vector": embedding,
                "created_at": policy_tag.created_at.isoformat() if policy_tag.created_at else datetime.now(JST).isoformat(),
                "updated_at": datetime.now(JST).isoformat()
            }
            
            # MySQLのembeddingカラムにベクトルデータを保存
            embedding_data = {
                "vector": embedding,
                "text": text,
                "metadata": {
                    "tag_id": policy_tag.id,
                    "tag_name": policy_tag.name,
                    "type": "policy_tag",
                    "created_at": policy_tag.created_at.isoformat() if policy_tag.created_at else None
                }
            }
            policy_tag.embedding = json.dumps(embedding_data, ensure_ascii=False)
            db.commit()
            
            # Cosmos DBにドキュメントを保存
            print(f"💾 Cosmos DBに政策タグ (ID: {tag_id}) を保存中...")
            result = self.collection.replace_one(
                {"_id": f"policy_tag_{policy_tag.id}"},
                document,
                upsert=True
            )
            
            return {
                "success": True,
                "message": f"政策タグ (ID: {tag_id}) をベクトル化してCosmos DBに保存しました",
                "processed_count": 1,
                "tag_id": tag_id,
                "tag_name": policy_tag.name
            }

        except Exception as e:
            print(f"❌ 政策タグベクトル化エラー: {str(e)}")
            return {
                "success": False,
                "message": f"ベクトル化処理中にエラーが発生しました: {str(e)}",
                "processed_count": 0
            }

    def search_similar_policy_tags(
        self, 
        query: str, 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
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
            query_embedding = self.embeddings.embed_query(query)
            
            # 検索パイプラインを構築
            pipeline = [
                {
                    "$search": {
                        "vectorSearch": {
                            "queryVector": query_embedding,
                            "path": "vector",
                            "numCandidates": top_k * 10,  # より多くの候補を取得
                            "limit": top_k
                        }
                    }
                },
                {"$match": {"type": "policy_tag"}}
            ]
            
            # 検索実行
            results = list(self.collection.aggregate(pipeline))
            
            # 結果を整形
            similar_tags = []
            for result in results:
                similar_tags.append({
                    "policy_tag_id": result.get("policy_tag_id"),
                    "name": result.get("name"),
                    "text": result.get("text"),
                    "score": result.get("score", 0.0),
                    "created_at": result.get("created_at")
                })
            
            return similar_tags

        except Exception as e:
            print(f"❌ 政策タグ検索エラー: {str(e)}")
            return []

    def delete_policy_tag_vector(self, tag_id: int) -> Dict[str, Any]:
        """
        指定された政策タグIDのベクトルを削除する
        
        Args:
            tag_id: 削除する政策タグのID
            
        Returns:
            Dict[str, Any]: 処理結果の詳細
        """
        try:
            # Cosmos DBからドキュメントを削除
            result = self.collection.delete_one({"_id": f"policy_tag_{tag_id}"})
            
            if result.deleted_count > 0:
                return {
                    "success": True,
                    "message": f"政策タグベクトル (ID: {tag_id}) を削除しました",
                    "tag_id": tag_id
                }
            else:
                return {
                    "success": False,
                    "message": f"政策タグベクトル (ID: {tag_id}) が見つかりませんでした"
                }

        except Exception as e:
            print(f"❌ 政策タグベクトル削除エラー: {str(e)}")
            return {
                "success": False,
                "message": f"ベクトル削除中にエラーが発生しました: {str(e)}"
            }

# サービスインスタンスを作成
cosmos_vector_service = CosmosVectorService()
