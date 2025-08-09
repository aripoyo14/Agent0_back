# Pinecone から Azure Cosmos DB への移行ガイド

このドキュメントでは、現在のPineconeベクトル検索システムをAzure Cosmos DBに移行するための手順を説明します。

## 1. Azure Cosmos DB の種類選択

### 推奨: Azure Cosmos DB for MongoDB vCore

**理由:**
- **ベクトル検索機能**: ネイティブでベクトル検索をサポート
- **MongoDB API**: 既存のMongoDB知識を活用可能
- **スケーラビリティ**: 自動スケーリング機能
- **統合ソリューション**: ベクトルデータとメタデータを同じDBで管理

### 他の選択肢
- **Azure Cosmos DB for NoSQL**: ベクトル検索機能なし
- **Azure Cosmos DB for PostgreSQL**: ベクトル検索機能あり（pgvector使用）
- **Azure Cosmos DB for Apache Cassandra**: ベクトル検索機能なし

## 2. Azure Cosmos DB for MongoDB vCore のセットアップ

### 2.1 Azure Portalでのアカウント作成

1. **Azure Portal**にログイン
2. **「Azure Cosmos DB」**を検索
3. **「Azure Cosmos DB for MongoDB vCore」**を選択
4. **「作成」**をクリック

### 2.2 基本設定

```
リソースグループ: 既存のリソースグループを選択
アカウント名: [your-account-name]-cosmos-mongo
リージョン: 東日本 (Japan East)
容量モード: プロビジョニング済み
最小 RU/s: 1000
```

### 2.3 ネットワーク設定

```
ネットワーク接続: パブリック エンドポイント
ファイアウォール: すべてのネットワークからのアクセスを許可
```

### 2.4 バックアップ設定

```
バックアップ ポリシー: 継続的
バックアップ間隔: 1分
バックアップ保持期間: 7日
```

## 3. データベースとコレクションの作成

### 3.1 データベースの作成

1. **データエクスプローラー**を選択
2. **「新しいデータベース」**をクリック
3. 設定:
   ```
   データベース名: vector_db
   プロビジョニング済みスループット: 有効
   RU/s: 1000
   ```

### 3.2 コレクションの作成

1. **「新しいコレクション」**をクリック
2. 設定:
   ```
   データベース: vector_db
   コレクション名: vectors
   パーティションキー: /type
   プロビジョニング済みスループット: 有効
   RU/s: 1000
   ```

### 3.3 ベクトル検索インデックスの作成

コレクション作成時に以下の設定を追加:

```json
{
  "vectorSearchOptions": {
    "vector": "vectorSearch",
    "dimensions": 1536,
    "metric": "cosine"
  }
}
```

## 4. 接続設定の取得

### 4.1 接続文字列の取得

1. **「キー」**セクションに移動
2. **「プライマリ接続文字列」**をコピー
3. 形式: `mongodb://[account-name]:[key]@[account-name].mongo.cosmos.azure.com:10255/?ssl=true&replicaSet=globaldb&retrywrites=false&maxIdleTimeMS=120000&appName=@[account-name]@`

### 4.2 環境変数の設定

`.env`ファイルに以下を追加:

```env
# Azure Cosmos DB for MongoDB vCore
COSMOS_CONNECTION_STRING=your-cosmos-connection-string
COSMOS_DATABASE_NAME=vector_db
COSMOS_COLLECTION_NAME=vectors
```

## 5. 実装手順

### 5.1 依存関係の追加

`requirements.txt`に追加:
```
pymongo==4.6.1
```

### 5.2 設定ファイルの更新

`app/core/config.py`に追加:
```python
# Azure Cosmos DB
cosmos_connection_string: str = Field(default="", alias="COSMOS_CONNECTION_STRING")
cosmos_database_name: str = Field(default="vector_db", alias="COSMOS_DATABASE_NAME")
cosmos_collection_name: str = Field(default="vectors", alias="COSMOS_COLLECTION_NAME")
```

### 5.3 サービスクラスの作成

`app/services/cosmos_vector.py`を作成:
- `CosmosVectorService`クラス
- ベクトル化機能
- 検索機能
- 統計情報取得機能

### 5.4 APIルートの作成

`app/api/routes/cosmos_summary.py`を作成:
- 要約生成とベクトル化
- 類似検索
- ベクトル削除
- 統計情報取得

### 5.5 メインアプリケーションの更新

`app/main.py`にルートを追加:
```python
from app.api.routes import cosmos_summary
app.include_router(cosmos_summary.router, prefix="/api")
```

## 6. データ移行手順

### 6.1 既存データのエクスポート

1. Pineconeから既存のベクトルデータをエクスポート
2. メタデータとベクトルを分離
3. Cosmos DB形式に変換

### 6.2 データのインポート

1. Cosmos DBにドキュメント形式でインポート
2. ベクトルフィールドの検証
3. インデックスの確認

### 6.3 動作確認

1. 検索機能のテスト
2. パフォーマンスの確認
3. エラーハンドリングの確認

## 7. 設定変更

### 7.1 環境変数の切り替え

開発環境:
```env
# Pinecone (開発用)
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=your-pinecone-environment
PINECONE_INDEX=your-pinecone-index-name

# Cosmos DB (本番用)
COSMOS_CONNECTION_STRING=your-cosmos-connection-string
COSMOS_DATABASE_NAME=vector_db
COSMOS_COLLECTION_NAME=vectors
```

### 7.2 サービスの切り替え

設定に基づいてPineconeまたはCosmos DBを使用:
```python
if settings.use_cosmos_db:
    vector_service = cosmos_vector_service
else:
    vector_service = pinecone_vector_service
```

## 8. コスト比較

### 8.1 Pinecone
- **料金体系**: ベクトル数とクエリ数に基づく
- **無料枠**: 月100,000ベクトル、月100,000クエリ
- **有料**: $0.10/1000ベクトル、$0.10/1000クエリ

### 8.2 Azure Cosmos DB for MongoDB vCore
- **料金体系**: RU/s（Request Units per second）に基づく
- **無料枠**: なし
- **有料**: 約$0.008/100 RU/s/時間

### 8.3 コスト最適化
- **自動スケーリング**: 使用量に応じて自動調整
- **リザーブドキャパシティ**: 長期使用で割引
- **地理的分散**: 必要に応じて設定

## 9. パフォーマンス考慮事項

### 9.1 ベクトル検索の最適化
- **インデックス設定**: 適切な次元数とメトリック
- **パーティションキー**: 効率的なデータ分散
- **RU/s設定**: ワークロードに応じた調整

### 9.2 スケーラビリティ
- **自動スケーリング**: トラフィックに応じた自動調整
- **地理的分散**: グローバルアクセス対応
- **マルチリージョン**: 可用性の向上

## 10. セキュリティ設定

### 10.1 ネットワークセキュリティ
- **ファイアウォール**: 特定IPからのアクセスのみ許可
- **プライベートエンドポイント**: VNet内からのアクセス
- **サービスエンドポイント**: Azureサービスからのアクセス

### 10.2 認証・認可
- **接続文字列**: 適切な権限を持つキーの使用
- **RBAC**: Azure ADを使用したロールベースアクセス制御
- **キーローテーション**: 定期的なキーの更新

## 11. 監視とログ

### 11.1 Azure Monitor
- **メトリクス**: RU/s、レイテンシー、エラー率
- **ログ**: クエリログ、エラーログ
- **アラート**: パフォーマンス閾値の設定

### 11.2 アプリケーションログ
- **ベクトル化処理**: 成功・失敗ログ
- **検索処理**: クエリ時間、結果数
- **エラーハンドリング**: 詳細なエラー情報

## 12. 移行チェックリスト

### 12.1 事前準備
- [ ] Azure Cosmos DBアカウントの作成
- [ ] データベースとコレクションの作成
- [ ] ベクトル検索インデックスの設定
- [ ] 接続文字列の取得と設定

### 12.2 実装
- [ ] 依存関係の追加
- [ ] 設定ファイルの更新
- [ ] サービスクラスの実装
- [ ] APIルートの実装
- [ ] メインアプリケーションの更新

### 12.3 テスト
- [ ] 単体テストの作成
- [ ] 統合テストの実行
- [ ] パフォーマンステスト
- [ ] エラーハンドリングの確認

### 12.4 移行
- [ ] 既存データのエクスポート
- [ ] データのインポート
- [ ] 動作確認
- [ ] 本番環境へのデプロイ

### 12.5 運用
- [ ] 監視設定
- [ ] アラート設定
- [ ] バックアップ設定
- [ ] セキュリティ設定

## 13. トラブルシューティング

### 13.1 よくある問題
- **接続エラー**: 接続文字列の確認
- **インデックスエラー**: ベクトル検索インデックスの確認
- **パフォーマンス問題**: RU/s設定の調整
- **認証エラー**: キーの権限確認

### 13.2 デバッグ方法
- **ログ確認**: アプリケーションログの確認
- **メトリクス確認**: Azure Monitorでの監視
- **クエリ分析**: データエクスプローラーでの確認

## 14. 参考資料

- [Azure Cosmos DB for MongoDB vCore ドキュメント](https://docs.microsoft.com/azure/cosmos-db/mongodb/)
- [ベクトル検索の概要](https://docs.microsoft.com/azure/cosmos-db/mongodb/vector-search)
- [MongoDB API リファレンス](https://docs.microsoft.com/azure/cosmos-db/mongodb/mongodb-introduction)
- [パフォーマンス最適化](https://docs.microsoft.com/azure/cosmos-db/mongodb/performance-tips)
