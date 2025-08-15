# Agent0_back

## 面談録アップロード機能

面談録をアップロードして、自動的にベクトル化と政策タグとの関連度計算を行う機能です。

## 環境変数設定

### 必須環境変数

1. **Azure Blob Storage設定**
   ```bash
   # Azure Storage Account接続文字列
   AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=your-account;AccountKey=your-key;EndpointSuffix=core.windows.net"
   
   # コンテナ名（既存ファイル用）
   AZURE_BLOB_CONTAINER="agent0"
   
   # 面談録専用コンテナ名
   AZURE_MEETING_CONTAINER="agent0"
   ```

2. **データベース設定**
   ```bash
   DATABASE_HOST=localhost
   DATABASE_PORT=3306
   DATABASE_NAME=agent0
   DATABASE_USERNAME=students
   DATABASE_PASSWORD=password123
   ```

3. **認証設定**
   ```bash
   SECRET_KEY=your-secret-key-here-make-it-long-and-secure
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

### 開発環境での設定

1. `backend/env.example`を`backend/.env`にコピー
2. 必要な環境変数を設定
3. Azure接続文字列を空にするとローカルファイルシステムに保存

### API使用方法

```bash
# 議事録アップロード
curl -X POST "http://localhost:8000/api/meetings/{meeting_id}/upload-minutes" \
  -H "Authorization: Bearer {token}" \
  -F "file=@minutes.txt" \
  -F "expert_id={expert_id}" \
  -F "tag_ids=1,2,3"
```