## Cosmos Minutes: 実装サマリ（これまでに実行した変更）

### 概要
- 面談録 minutes を直接ベクトル化してCosmos DBへ保存し、そのベクトルとMySQLの政策タグベクトルから関連度を計算・保存する仕組みを実装。
- 関連度はEWMA（指数移動平均）で更新し、最新の内容を強調しつつ過去の履歴も緩やかに反映。

### 主要なAPI（minutesベース）
- POST `/api/cosmos-summary/minutes`（旧: `/summary`）
  - リクエスト: `minutes`(string), `expert_id`(uuid string), `tag_ids`(int|int[]|csv)
  - 処理: minutes優先でベクトル化→Cosmosへ保存→`tag_ids`対象の関連度をEWMAで更新
  - レスポンス: `summary_id`（保存ID）, `embedding_source`(`minutes`|`summary`), `vectorization_result.message` 等

- GET `/api/cosmos-summary/search`
  - minutesベクトルの類似検索（クエリ文字列を埋め込みにして検索）

- DELETE `/api/cosmos-summary/vector/{minutes_id}`（旧: `{summary_id}`）
  - 指定IDのベクトルをCosmosから削除

- 政策タグ関連
  - POST `/api/cosmos-summary/policy-tags/vectorize`（全タグ再ベクトル化）
  - POST `/api/cosmos-summary/policy-tags/vectorize/{tag_id}`（単一タグ再ベクトル化）
  - GET  `/api/cosmos-summary/policy-tags/search`
  - DELETE `/api/cosmos-summary/policy-tags/vector/{tag_id}`

### DBスキーマ（MySQL）
- `policy_tags`
  - 既存: `id (int)`, `name (varchar)`, `embedding (text)`, `created_at`, `updated_at`
  - 追加: `description (text)`, `keywords (text)`
  - ベクトル化は `name + description + keywords` を結合して埋め込み

- `experts_policy_tags`（関連度保存先）
  - 実テーブル前提: `id char(36) PK`, `expert_id char(36)`, `policy_tag_id int`, `relation_score decimal(3,2)`, `created_at`, `updated_at`
  - インデックス: `(expert_id, policy_tag_id)`

### 実装したロジック（要点）
- minutes直埋め込み
  - `OpenAIEmbeddings(model="text-embedding-3-small")`
  - 埋め込み対象は `raw_minutes` を最優先。無い場合に限り `title + summary` を使用

- 関連度計算と保存
  - `experts_policy_tags` への保存は、対象 `tag_ids` のみ計算
  - EWMA: `s_new = (1 - α) * s_old + α * s_now`（α=0.13 初期設定、保存時は小数点2桁）
  - 既存行があれば更新、無ければ新規作成（アップサート）

### 変更した代表的なファイル
- `app/services/cosmos_vector.py`
  - 追加/変更: `vectorize_minutes(...)`（旧`vectorize_summary`を置換）
  - minutes優先のベクトル化、レスポンスの`embedding_source`追加、ログ/文言のminutes統一
  - 政策タグ側のベクトル化を `name + description + keywords` へ拡張
  - EWMAによる関連度アップサート処理を実装

- `app/api/routes/cosmos_summary.py`
  - POST `/minutes` ハンドラ（`minutes`）
  - GET `/search` ハンドラ（`search_minutes`）
  - DELETE `/vector/{minutes_id}` ハンドラ（`delete_minutes_vector`）
  - ルータタグを `Cosmos Minutes` に変更

- `app/models/experts_policy_tags.py`
  - スキーマを実DBに整合（`id char(36)`, `expert_id char(36)`, `relation_score decimal(3,2)`）
  - 説明文を「関連度（EWMA）」へ更新

- `app/crud/experts_policy_tags.py`
  - `get_by_expert_and_tags`, `upsert_ewma` を追加
  - 既存削除→挿入から、EWMAアップサート方式へ

- `app/models/policy_tag.py`
  - `description`, `keywords` カラムを追加（モデル定義）

### マイグレーション（Workbench用SQL例）
```sql
ALTER TABLE policy_tags
  ADD COLUMN description TEXT NULL AFTER name,
  ADD COLUMN keywords   TEXT NULL AFTER description;

-- experts_policy_tags が既存と異なる場合の一例
-- ALTER TABLE experts_policy_tags MODIFY expert_id CHAR(36) NOT NULL;
```

### 使い方（例）
1) 政策タグの埋め込みを最新化（description/keywords 反映）
```bash
curl -X POST "http://127.0.0.1:8000/api/cosmos-summary/policy-tags/vectorize"
```

2) minutesをPOST（PowerShell例）
```powershell
$json = @'
{
  "minutes": "（面談録テキスト）",
  "expert_id": "b5036a94-7590-11f0-8789-00224816f8e3",
  "tag_ids": [1,5,10]
}
'@
curl -X POST "http://127.0.0.1:8000/api/cosmos-summary/minutes" -H "Content-Type: application/json" --data "$json"
```

3) 結果確認（MySQL）
```sql
SELECT expert_id, policy_tag_id, relation_score, created_at
FROM experts_policy_tags
WHERE expert_id = 'b5036a94-7590-11f0-8789-00224816f8e3'
ORDER BY updated_at DESC
LIMIT 20;
```

### 運用・調整ポイント
- **αの調整**: 直近を強調したい場合はα↑（例: 0.3〜0.5）。安定性重視はα↓。
- **タグ表現強化**: `description/keywords` を充実させ、専門語や同義語を含めると精度向上。
- **モデル**: さらに精度が必要なら `text-embedding-3-large` を検討（コスト注意）。

### 既知の注意
- 一部開発用ドキュメントに旧`/summary`表記が残る場合がありますが、実APIは `/minutes` が正。
- 依存パッケージ解決に関するリンタ警告は動作に影響しません（仮想環境での再インストールで解消）。


