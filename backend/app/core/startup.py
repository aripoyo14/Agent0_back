import os
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings

pc: Pinecone
index = None
embeddings: OpenAIEmbeddings
_client: OpenAI = None

__all__ = ["pc", "index", "embeddings", "get_client", "init_external_services"]

def get_client() -> OpenAI:
    """OpenAI clientを取得する。初期化されていない場合はエラーを発生させる。"""
    if _client is None:
        raise RuntimeError("OpenAI client is not initialized. Call init_external_services() first.")
    return _client

async def init_external_services():
    global pc, index, embeddings, _client

    # OpenAI client
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is missing")
    _client = OpenAI(api_key=settings.openai_api_key)

    # Pinecone client
    if not all([settings.pinecone_api_key, settings.pinecone_env, settings.pinecone_index]):
        raise RuntimeError("Pinecone configuration missing")
    pc = Pinecone(api_key=settings.pinecone_api_key)

    # インデックス確認・作成
    if settings.pinecone_index not in pc.list_indexes().names():
        pc.create_index(
            name=settings.pinecone_index,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region=settings.pinecone_env)
        )
    index = pc.Index(settings.pinecone_index)

    # Embeddingモデル
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")