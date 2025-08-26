# 主要APIへの監査ログ適用実装

## 概要

主要APIへの監査ログ適用を実装し、以下の3つのカテゴリでのセキュリティ追跡を可能にしました：

- [x] 検索・分析系API - 機密情報へのアクセス追跡
- [x] データ読み取り系API - 情報漏洩の追跡  
- [x] 権限変更系API - セキュリティ侵害の追跡

## 実装内容

### 1. 監査イベントタイプの拡張

`app/core/security/audit/models.py`に以下の新しいイベントタイプを追加：

#### 検索・分析系API
- `SEARCH_NETWORK_MAP` - 人脈マップ検索
- `SEARCH_MINUTES` - 面談録検索
- `SEARCH_POLICY_TAGS` - 政策タグ検索
- `SEARCH_EXPERTS` - エキスパート検索
- `SEARCH_POLICY_PROPOSALS` - 政策案検索
- `SEARCH_COMMENTS` - コメント検索
- `SEARCH_USERS` - ユーザー検索
- `SEARCH_DEPARTMENTS` - 部署検索
- `SEARCH_POSITIONS` - 役職検索

#### データ読み取り系API
- `READ_EXPERT_PROFILE` - エキスパートプロフィール読み取り
- `READ_EXPERT_INSIGHTS` - エキスパートインサイト読み取り
- `READ_USER_PROFILE` - ユーザープロフィール読み取り
- `READ_MEETING_DETAILS` - 面談詳細読み取り
- `READ_MEETING_EVALUATION` - 面談評価読み取り
- `READ_POLICY_PROPOSAL` - 政策案読み取り
- `READ_POLICY_COMMENTS` - 政策案コメント読み取り
- `READ_INVITATION_CODES` - 招待コード読み取り
- `READ_SECURITY_STATUS` - セキュリティ状況読み取り
- `READ_SECURITY_METRICS` - セキュリティメトリクス読み取り
- `READ_SECURITY_CONFIG` - セキュリティ設定読み取り

#### 権限変更系API
- `ROLE_ASSIGNMENT` - ロール割り当て
- `ROLE_REMOVAL` - ロール削除
- `PERMISSION_GRANT` - 権限付与
- `PERMISSION_REVOKE` - 権限剥奪
- `USER_ACTIVATION` - ユーザー有効化
- `USER_DEACTIVATION` - ユーザー無効化
- `EXPERT_ACTIVATION` - エキスパート有効化
- `EXPERT_DEACTIVATION` - エキスパート無効化
- `MFA_ENABLE` - MFA有効化
- `MFA_DISABLE` - MFA無効化
- `INVITATION_CODE_GENERATE` - 招待コード生成
- `INVITATION_CODE_DEACTIVATE` - 招待コード無効化

### 2. APIルートへの監査ログ適用

#### 検索・分析系API
- `search_network_map.py` - 人脈マップ検索API
- `cosmos_minutes.py` - 面談録検索・政策タグ検索API

#### データ読み取り系API
- `expert.py` - エキスパートプロフィール・インサイト読み取りAPI
- `user.py` - ユーザープロフィール読み取りAPI
- `meeting.py` - 面談詳細・一覧読み取りAPI
- `policy_proposal.py` - 政策案・投稿履歴読み取りAPI

#### 権限変更系API
- `user.py` - ユーザーロール変更API
- `invitation_code.py` - 招待コード生成・無効化API

### 3. 監査ログサービスの拡張

`app/core/security/audit/service.py`に以下の機能を追加：

- `get_logs_with_filters()` - フィルタリング条件付きログ取得
- `get_event_type_statistics()` - イベントタイプ別統計取得

### 4. 監査ログ表示APIの拡張

`app/core/security/audit/router.py`に以下の機能を追加：

- フィルタリング機能（イベントタイプ、リソース、ユーザーID、ユーザータイプ、成功/失敗、時間範囲）
- カテゴリ別統計表示（検索・分析系、データ読み取り系、権限変更系）
- 詳細情報表示（IPアドレス、ユーザーエージェント、セッションID）

### 5. 監査ログ設定の拡張

`app/core/security/audit/config.py`に以下の設定を追加：

- 各カテゴリの監査有効化設定
- アラート閾値設定
- 詳細レベル設定
- セッション・IP・ユーザーエージェント追跡設定

## 使用方法

### 1. 監査ログの確認

```bash
# 全監査ログの取得
GET /audit-logs/

# フィルタリング付きログ取得
GET /audit-logs/?event_type=search:network_map&hours=24&limit=50

# カテゴリ別統計
GET /audit-logs/categories

# 特定ログの詳細
GET /audit-logs/{log_id}
```

### 2. 監査ログのフィルタリング例

```bash
# 検索・分析系APIのログのみ
GET /audit-logs/?event_type=search:network_map

# 特定ユーザーの権限変更ログ
GET /audit-logs/?event_type=role:assignment&user_id=123

# 失敗したAPI呼び出し
GET /audit-logs/?success=false&hours=1
```

## セキュリティ効果

### 1. 機密情報アクセス追跡
- 人脈マップ、面談録、政策タグへのアクセスを詳細に記録
- 異常なアクセスパターンの検出が可能
- アクセス元のIPアドレスとユーザーエージェントを記録

### 2. 情報漏洩追跡
- プロフィール情報、インサイト、面談詳細の読み取りを記録
- 大量のデータ読み取りの検出が可能
- セッションIDによる追跡で不正アクセスの特定が可能

### 3. セキュリティ侵害追跡
- ロール変更、権限付与/剥奪、MFA設定変更を記録
- 権限昇格の試行を検出可能
- 招待コードの生成・無効化を追跡

## 今後の拡張予定

1. **リアルタイムアラート機能**
   - 閾値を超えたアクセス時の即座通知
   - 異常パターンの自動検出

2. **機械学習による異常検出**
   - ユーザーの通常パターン学習
   - 異常なアクセスパターンの自動検出

3. **レポート生成機能**
   - 日次・週次・月次のセキュリティレポート
   - カテゴリ別のアクセス統計

4. **統合ダッシュボード**
   - セキュリティ状況の可視化
   - リアルタイム監視画面

## 注意事項

1. **パフォーマンスへの影響**
   - 監査ログの記録は非同期で実行
   - データベースの負荷を最小限に抑制

2. **プライバシー保護**
   - 機密情報は自動的にマスキング
   - 個人情報の適切な取り扱い

3. **ログ保持期間**
   - デフォルトで365日間保持
   - 設定で調整可能

## 設定例

環境変数での設定：

```bash
# 監査ログの有効化
AUDIT_ENABLED=true

# 検索・分析系APIのアラート閾値
AUDIT_SEARCH_ANALYSIS_ALERT_THRESHOLD=100

# データ読み取り系APIのアラート閾値
AUDIT_DATA_READ_ALERT_THRESHOLD=50

# 権限変更系APIのアラート閾値
AUDIT_PERMISSION_CHANGES_ALERT_THRESHOLD=10

# 詳細レベル
AUDIT_DETAIL_LEVEL=detailed
```

この実装により、主要APIへの包括的な監査ログ適用が完了し、セキュリティ監視と追跡が大幅に強化されました。
