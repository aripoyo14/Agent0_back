# Policy Tags ベクトル化機能

この機能は、MySQLの`policy_tags`テーブルからデータを取得し、OpenAIのembeddingモデルを使用してベクトル化し、Pineconeに保存する機能を提供します。

## 機能概要

- MySQLの`policy_tags`テーブルから`id`と`name`を取得
- OpenAIの`text-embedding-ada-002`モデルを使用してベクトル化
- Pineconeにベクトルデータを保存
- 類似検索機能
- 統計情報の取得

## 必要な環境変数

`.env`ファイルに以下の設定が必要です：

```env
# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Pinecone
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=your-pinecone-environment
PINECONE_INDEX=your-pinecone-index-name

# Database
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=your-database-name
DATABASE_USERNAME=your-username
DATABASE_PASSWORD=your-password
```

## API エンドポイント

### 1. 全タグベクトル化実行
```http
POST /api/policy-tags/vectorize
```

MySQLの`policy_tags`テーブルから全てのデータを取得し、ベクトル化してPineconeに保存します。

### 2. 個別タグベクトル化実行
```http
POST /api/policy-tags/vectorize/{tag_id}
```

指定されたIDの政策タグをベクトル化してPineconeに保存します。

**レスポンス例：**
```json
{
  "status": "success",
  "message": "10個の政策タグをベクトル化してPineconeに保存しました",
  "processed_count": 10,
  "namespace": "policy_tags"
}
```

### 3. 類似検索
```http
GET /api/policy-tags/search?query=検索クエリ&top_k=5
```

**パラメータ：**
- `query`: 検索クエリ（必須）
- `top_k`: 返す結果の数（デフォルト: 5）

**レスポンス例：**
```json
[
  {
    "tag_id": 1,
    "tag_name": "AI政策",
    "score": 0.85,
    "created_at": "2024-01-01T00:00:00"
  },
  {
    "tag_id": 2,
    "tag_name": "デジタル政策",
    "score": 0.78,
    "created_at": "2024-01-01T00:00:00"
  }
]
```

### 4. 全政策タグ取得
```http
GET /api/policy-tags/list
```

MySQLの`policy_tags`テーブルから全てのデータを取得します。

**レスポンス例：**
```json
[
  {
    "id": 1,
    "name": "AI政策",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  },
  {
    "id": 2,
    "name": "デジタル政策",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

### 5. 政策タグ作成
```http
POST /api/policy-tags/create?name=新しいタグ名
```

新しい政策タグを作成します。

**レスポンス例：**
```json
{
  "status": "success",
  "message": "政策タグを作成しました",
  "data": {
    "id": 3,
    "name": "新しいタグ名",
    "created_at": "2024-01-01T00:00:00"
  }
}
```

### 6. 政策タグ削除
```http
DELETE /api/policy-tags/delete/{tag_id}
```

指定されたIDの政策タグをMySQLとPineconeの両方から削除します。

**レスポンス例：**
```json
{
  "status": "success",
  "message": "政策タグを削除しました",
  "mysql_deleted": true,
  "vector_deleted": true
}
```

### 7. 統計情報取得
```http
GET /api/policy-tags/statistics
```

Pineconeのベクトル統計情報を取得します。

**レスポンス例：**
```json
{
  "success": true,
  "total_vector_count": 1000,
  "policy_tags_vector_count": 50,
  "dimension": 1536,
  "index_fullness": 0.1,
  "namespaces": ["policy_tags", "other_namespace"]
}
```

## 使用方法

### 1. サーバー起動
```bash
cd backend
uvicorn app.main:app --reload
```

### 2. 全タグベクトル化実行
```bash
curl -X POST "http://localhost:8000/api/policy-tags/vectorize"
```

### 3. 個別タグベクトル化実行
```bash
curl -X POST "http://localhost:8000/api/policy-tags/vectorize/1"
```

### 4. 類似検索
```bash
curl "http://localhost:8000/api/policy-tags/search?query=AI&top_k=3"
```

### 5. 全タグ取得
```bash
curl "http://localhost:8000/api/policy-tags/list"
```

## データベーススキーマ

`policy_tags`テーブルの構造：

```sql
CREATE TABLE policy_tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    embedding TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### embeddingカラムの内容

`embedding`カラムには以下のJSON形式でベクトルデータが保存されます：

```json
{
    "vector": [0.1, 0.2, 0.3, ...],
    "text": "ID: 1, Name: AI政策",
    "metadata": {
        "tag_id": 1,
        "tag_name": "AI政策",
        "type": "policy_tag",
        "created_at": "2024-01-01T00:00:00"
    }
}
```

## 注意事項

1. **OpenAI API キー**: ベクトル化にはOpenAI APIキーが必要です
2. **Pinecone API キー**: ベクトル保存にはPinecone APIキーが必要です
3. **データ量**: 大量のデータをベクトル化する場合は、API制限に注意してください
4. **コスト**: OpenAI APIとPineconeの使用には料金が発生します

## エラーハンドリング

各APIエンドポイントは適切なエラーハンドリングを実装しており、以下のようなエラーが発生した場合に適切なHTTPステータスコードとエラーメッセージを返します：

- 400: リクエストパラメータエラー
- 404: リソースが見つからない
- 500: サーバー内部エラー

## 開発者向け情報

### ファイル構成
```
backend/
├── app/
│   ├── models/
│   │   └── policy_tag.py          # PolicyTagモデル
│   ├── crud/
│   │   └── policy_tag.py          # CRUD操作
│   ├── services/
│   │   └── policy_tag_vector.py   # ベクトル化サービス
│   └── api/routes/
│       └── policy_tag.py          # APIエンドポイント
└── POLICY_TAG_VECTOR_README.md    # このファイル
```

### カスタマイズ

ベクトル化のテキスト形式やメタデータを変更したい場合は、`app/services/policy_tag_vector.py`の`vectorize_policy_tags`メソッドを修正してください。
