# PolicyProposalComments数取得API ドキュメント

## 概要

このドキュメントでは、PolicyProposalComments数取得APIの使用方法について説明します。フロントエンドのダッシュボードページでPolicyProposalComments数を表示するために実装されました。

## 実装されたエンドポイント

### 特定の政策提案に対するPolicyProposalComments数取得API

**エンドポイント**: `GET /api/policy-proposal-comments/policy-proposals/{policy_proposal_id}/comment-count`

**説明**: 特定の政策提案に対するPolicyProposalComments数を取得するAPI

**パラメータ**:
- `policy_proposal_id`: 政策提案ID（パスパラメータ）

**レスポンス例**:
```json
{
  "policy_proposal_id": "policy-001",
  "comment_count": 157
}
```

**レスポンスフィールド**:
- `policy_proposal_id`: 政策提案ID
- `comment_count`: その政策提案に対するPolicyProposalComments数

## エラーハンドリング

**エラーレスポンス**:
```json
{
  "detail": "コメント数取得中にエラーが発生しました: エラー詳細"
}
```

**想定されるエラー**:
- `500`: サーバー内部エラー（データベース接続エラー等）

## フロントエンド連携例

### TypeScriptでの使用例

```typescript
// 特定の政策提案に対するPolicyProposalComments数取得
const getCommentCount = async (policyId: string) => {
  try {
    const response = await fetch(`/api/policy-proposal-comments/policy-proposals/${policyId}/comment-count`);
    const data = await response.json();
    // console.log('政策提案ID:', data.policy_proposal_id);
    // console.log('コメント数:', data.comment_count);
    return data.comment_count;
  } catch (error) {
    console.error('エラー:', error);
    return 0;
  }
};
```

### Reactでの使用例

```tsx
import React, { useState, useEffect } from 'react';

interface CommentCount {
  policy_proposal_id: string;
  comment_count: number;
}

interface CommentCountComponentProps {
  policyId: string;
}

const CommentCountComponent: React.FC<CommentCountComponentProps> = ({ policyId }) => {
  const [commentCount, setCommentCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCommentCount = async () => {
      try {
        const response = await fetch(`/api/policy-proposal-comments/policy-proposals/${policyId}/comment-count`);
        const data: CommentCount = await response.json();
        setCommentCount(data.comment_count);
      } catch (error) {
        console.error('データ取得エラー:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCommentCount();
  }, [policyId]);

  if (loading) {
    return <div>読み込み中...</div>;
  }

  return (
    <div>
      <h2>コメント統計</h2>
      <p>政策提案ID: {policyId}</p>
      <p>コメント数: {commentCount}</p>
    </div>
  );
};

export default CommentCountComponent;
```

## テスト

APIのテストは以下のコマンドで実行できます：

```bash
# サーバー起動
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 別ターミナルでテスト実行
python test_comment_count_api.py
```

## 実装詳細

### データベースクエリ

```sql
SELECT COUNT(*) FROM policy_proposal_comments 
WHERE policy_proposal_id = 'policy-001' AND is_deleted = false;
```

### パフォーマンス考慮事項

- 論理削除されたコメントは除外
- シンプルなCOUNTクエリで高速実行
- 必要に応じてインデックスを追加

### セキュリティ

- 入力値のバリデーション（不要）
- SQLインジェクション対策（SQLAlchemy ORM使用）

## 変更履歴

- 2025-01-27: 初回実装
  - 特定の政策提案に対するPolicyProposalComments数取得API
  - シンプルなレスポンス形式
  - 基本的なエラーハンドリング
