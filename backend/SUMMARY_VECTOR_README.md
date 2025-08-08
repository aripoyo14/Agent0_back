# 要約ベクトル化機能

この機能は、面談録の要約内容をOpenAIのembeddingモデルを使用してベクトル化し、Pineconeに保存する機能を提供します。

## 機能概要

- 面談録の要約生成
- 要約内容のベクトル化（タイトル、内容、エキスパートID、複数のタグIDを含む）
- Pineconeへのベクトルデータ保存
- 類似検索機能（エキスパートやタグでの絞り込み対応）
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
```

## API エンドポイント

### 1. 要約生成とベクトル化
```http
POST /api/summary/summary
```

**リクエスト例：**
```json
{
  "minutes": "面談録の内容...",
  "expert_id": 1,
  "tag_ids": [1, 2, 3]
}
```

**複数のtag_ids指定方法：**
```json
// リスト形式
{
  "minutes": "面談録の内容...",
  "expert_id": 1,
  "tag_ids": [1, 2, 3]
}

// カンマ区切り文字列
{
  "minutes": "面談録の内容...",
  "expert_id": 1,
  "tag_ids": "1,2,3"
}

// 単一のタグID
{
  "minutes": "面談録の内容...",
  "expert_id": 1,
  "tag_ids": 1
}
```

**レスポンス例：**
```json
{
  "title": "会議タイトル",
  "summary": "会議要約",
  "expert_id": 1,
  "tag_ids": [1, 2, 3],
  "summary_id": "summary_20241201_143022",
  "vectorization_result": {
    "success": true,
    "message": "要約内容をベクトル化してPineconeに保存しました",
    "summary_id": "summary_20241201_143022",
    "namespace": "summaries",
    "metadata": {
      "summary_id": "summary_20241201_143022",
      "title": "会議タイトル",
      "summary": "会議要約",
      "expert_id": 1,
      "tag_ids": "1,2,3",
      "type": "summary",
      "created_at": "2024-12-01T14:30:22+09:00"
    }
  }
}
```

### 2. 要約内容の類似検索
```http
GET /api/summary/search?query=検索クエリ&top_k=5&expert_id=1&tag_ids=1,2,3
```

**パラメータ：**
- `query`: 検索クエリ（必須）
- `top_k`: 返す結果の数（デフォルト: 5）
- `expert_id`: 特定のエキスパートで絞り込み（オプション）
- `tag_ids`: 特定のタグで絞り込み（カンマ区切り、オプション）

**レスポンス例：**
```json
{
  "status": "success",
  "query": "AI政策",
  "results": [
    {
      "summary_id": "summary_20241201_143022",
      "title": "AI政策に関する会議",
      "summary": "AI政策の検討内容...",
      "expert_id": 1,
      "tag_ids": [1, 2, 3],
      "tag_ids_str": "1,2,3",
      "score": 0.85,
      "created_at": "2024-12-01T14:30:22+09:00"
    }
  ],
  "count": 1
}
```

### 3. 要約ベクトルの削除
```http
DELETE /api/summary/vector/{summary_id}
```

**レスポンス例：**
```json
{
  "status": "success",
  "message": "要約ベクトル (ID: summary_20241201_143022) を削除しました"
}
```

### 4. 統計情報取得
```http
GET /api/summary/statistics
```

**レスポンス例：**
```json
{
  "success": true,
  "total_vector_count": 1000,
  "summaries_vector_count": 50,
  "dimension": 1536,
  "index_fullness": 0.1,
  "namespaces": ["policy_tags", "summaries"]
}
```

## 使用方法

### 1. サーバー起動
```bash
cd backend
uvicorn app.main:app --reload
```

### 2. 要約生成とベクトル化（複数タグ）
```bash
curl -X POST "http://localhost:8000/api/summary/summary" \
  -H "Content-Type: application/json" \
  -d '{
    "minutes": "面談録の内容...",
    "expert_id": 1,
    "tag_ids": [1, 2, 3]
  }'
```

### 3. 類似検索
```bash
curl "http://localhost:8000/api/summary/search?query=AI政策&top_k=3"
```

### 4. エキスパートで絞り込み検索
```bash
curl "http://localhost:8000/api/summary/search?query=政策&expert_id=1&top_k=5"
```

### 5. 複数タグで絞り込み検索
```bash
curl "http://localhost:8000/api/summary/search?query=会議&tag_ids=1,2&top_k=5"
```

### 6. ベクトル削除
```bash
curl -X DELETE "http://localhost:8000/api/summary/vector/summary_20241201_143022"
```

### 7. 統計情報取得
```bash
curl "http://localhost:8000/api/summary/statistics"
```

## データ構造

### ベクトル化されるテキスト
```
Title: {要約タイトル}, Summary: {要約内容}, Expert ID: {エキスパートID}, Tag IDs: {カンマ区切りのタグID}
```

### メタデータ
```json
{
  "summary_id": "summary_20241201_143022",
  "title": "会議タイトル",
  "summary": "会議要約",
  "expert_id": 1,
  "tag_ids": "1,2,3",
  "type": "summary",
  "created_at": "2024-12-01T14:30:22+09:00"
}
```

## 複数タグIDの処理

### 保存時の処理
- 複数のタグIDはカンマ区切りの文字列としてPineconeに保存
- 例：`[1, 2, 3]` → `"1,2,3"`

### 検索時の処理
- 検索クエリで指定されたタグIDと、保存されているタグIDの共通部分をチェック
- 共通のタグIDが1つでもあれば検索結果に含める

### レスポンス形式
- `tag_ids`: 整数リストとして返す（例：`[1, 2, 3]`）
- `tag_ids_str`: 元のカンマ区切り文字列も保持（例：`"1,2,3"`）

## Pinecone Index設計

### 推奨設計：単一Index + Namespace分離

- **Index**: 1つのPinecone indexを使用
- **Namespace**: `summaries` で要約データを分離
- **Dimension**: 1536（OpenAI text-embedding-ada-002）
- **Metric**: cosine

### メリット
- コスト効率が良い（1つのindexで済む）
- 管理が簡単
- 既存のpolicy_tags実装と一貫性がある
- 必要に応じて異なるnamespace間での検索も可能

## 注意事項

1. **OpenAI API キー**: ベクトル化にはOpenAI APIキーが必要です
2. **Pinecone API キー**: ベクトル保存にはPinecone APIキーが必要です
3. **データ量**: 大量の要約をベクトル化する場合は、API制限に注意してください
4. **コスト**: OpenAI APIとPineconeの使用には料金が発生します
5. **expert_idとtag_ids**: 要約生成時には必ず指定してください
6. **複数タグ**: タグIDは単一のint、リスト、またはカンマ区切りの文字列で指定可能です

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
│   ├── services/
│   │   └── summary_vector.py      # 要約ベクトル化サービス
│   ├── api/routes/
│   │   └── summary.py             # 要約APIルート
│   └── schemas/
│       └── summary.py             # 要約スキーマ
└── SUMMARY_VECTOR_README.md       # このファイル
```

### 主要クラス
- `SummaryVectorService`: 要約ベクトル化の主要ロジック
- `SummaryRequest`: 要約リクエストスキーマ
- `SummaryResponse`: 要約レスポンススキーマ

### 主要メソッド
- `_normalize_tag_ids()`: タグIDをカンマ区切り文字列に正規化
- `_parse_tag_ids()`: カンマ区切り文字列を整数リストに変換
