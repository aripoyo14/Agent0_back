# ベクトルデータベース関連のインポート
import os
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

# .env ファイルの読み込み（環境変数を使うため）
load_dotenv()

# 環境変数の取得
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX")

# 環境変数のバリデーション
if not all([PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME]):
    raise RuntimeError("Pinecone configuration is missing in environment variables")

# Pineconeクライアントの初期化
pc = Pinecone(api_key=PINECONE_API_KEY)

# インデックスの確認または作成
try:
    # インデックスが存在するか確認
    if PINECONE_INDEX_NAME not in pc.list_indexes().names():
        # インデックスが存在しない場合は作成
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=1536,  # OpenAI text-embedding-ada-002 の次元数
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region=PINECONE_ENVIRONMENT
            )
        )
    # インデックスの取得
    index = pc.Index(PINECONE_INDEX_NAME)
except Exception as e:
    print(f"❌ Pineconeの初期化エラー: {str(e)}")
    raise RuntimeError(f"Failed to initialize Pinecone: {str(e)}")

# ベクトル生成モデルの初期化
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")