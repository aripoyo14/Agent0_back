### 概要
人物（姓+名）と所属（会社名+部署）から、書籍・登壇などの外部発信情報を取得するAPIを実装。Google Programmable Search Engine（CSE）で検索した候補URLをLLMで分類・整形し、必要に応じてDB（`expert_activities`）に保存します。

### エンドポイント
- メソッド/パス: `POST /api/outreach`
- 入力（Body）:
  - `last_name: string`（必須）
  - `first_name: string`（必須）
  - `companies_name: string | null`
  - `department: string | null`
  - `limit: number`（1〜50, 省略時10）
- 出力（配列）: 要素は以下のスキーマ
  - `category: string`（例: 書籍/登壇/講演/寄稿/インタビュー/論文。不明時は"外部発信"で補完）
  - `date: date | null`（`YYYY-MM-DD`、不明時は`null`）
  - `title: string`
  - `details: url`（情報ソースURL）

### 内部構成（主要ファイル）
- ルート: `app/api/routes/outreach.py`
- スキーマ: `app/schemas/outreach.py`
- サービス: `app/services/outreach.py`
- 設定: `app/core/config.py`

### 取得フロー（検索〜整形）
1) 検索クエリ生成
   - 氏名バリアント: `"{姓} {名}"`, `"{名} {姓}"`, `"{姓}{名}"`
   - 会社名・部署を付与
   - キーワード群（日/英）: 登壇/講演/講師, 寄稿/インタビュー/執筆, 書籍/出版/著書, 論文/学会/研究発表, keynote/talk/interview/publication
2) Google CSE検索（JSON API）
   - 会社URLがDBにある場合はドメイン限定（`siteSearch`）→ 0件なら全Webで再検索
   - 結果を `title/link/snippet/source` に正規化し、URL重複を除外
3) LLM整形（OpenAI）
   - 候補一覧を入力し、最大`limit`件に分類・整形
   - JSON Schemaを指定し、`title`/`details`必須、`date`はISO日付 or null
   - `category`は欠落時にサーバー側で"外部発信"を補完
4) レスポンスとして返却

### DB保存
- 一致するエキスパートが存在する場合のみ保存（`experts`）
  - 会社名で `companies` を解決 → `experts` を氏名（+会社ID一致があれば）で解決
  - `expert_activities` へ insert（URL重複はスキップ）
    - `event_date` ← `date`
    - `event_url` ← `details`
    - `title` ← `title`
    - `description` ← `category=...`（カテゴリ列が無いため格納）

### 設定（環境変数）
- `OPENAI_API_KEY`: OpenAI APIキー
- `GOOGLE_CSE_API_KEY`: Custom Search JSON APIのAPIキー
- `GOOGLE_CSE_CX`: CSE（検索エンジンID）
- `GOOGLE_CSE_ENDPOINT`（任意、既定: `https://www.googleapis.com/customsearch/v1`）

### セットアップ/起動
1) 依存関係インストール
   - `pip install -r backend/backend/requirements.txt`
2) 環境変数（.env）設定
3) 起動
   - `uvicorn app.main:app --reload`

### 観測性/デバッグ
- サービスに `find_outreach_with_debug` を追加
- ルートで以下のデバッグ情報をログ出力（`print`）
  - `queries`（使用クエリ）
  - `name_variants`（氏名バリアント）
  - `candidates_count`（CSE候補件数）
  - `llm_items_count`（LLM抽出件数）
  - `final_count`（返却件数）
  - `company_domain`（会社ドメインでsite限定した場合）
  - `saved_for_expert`（DB保存実施フラグ）

### 既知の制約
- CSEの検索品質に依存し、人物名の一致度が低い候補が混入する可能性
- LLM整形は厳格スキーマで拘束しているが、候補が不適切だと誤判定する場合あり

### 改善案（順次導入想定）
- 候補事前フィルタ: `title`/`snippet`に氏名バリアントを含むものに限定、PDF等を除外
- CSEエンジン側の対象サイト調整（出版社・学会・イベントサイトを優先）
- 専用API併用
  - 書籍: Google Books API
  - 論文: Crossref / Semantic Scholar API
  - イベント/登壇: Connpass / Doorkeeper API
- 会社名の英文表記・別名辞書の導入
- キャッシュ/レート制限/リトライ

### セキュリティ/キー制限の推奨
- Google Cloud ConsoleのAPIキーで
  - アプリケーション制限: サーバー送信元IP制限（推奨）
  - APIの制限: Custom Search APIのみに限定
- キーは環境ごとに分離し、Secret ManagerやCIのSecretsで管理

### 変更履歴（この実装での主な差分）
- 新規: `POST /api/outreach` 実装、DB保存連携
- 追加: `app/schemas/outreach.py`, `app/services/outreach.py`
- ルーター登録: `app/api/routes/outreach.py`, `app/main.py`
- 設定追加: `GOOGLE_CSE_API_KEY`, `GOOGLE_CSE_CX`, `GOOGLE_CSE_ENDPOINT`
- 依存整理: `beautifulsoup4` を削除。DuckDuckGo→Bing→Google CSEへ移行


