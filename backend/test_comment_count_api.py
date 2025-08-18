#!/usr/bin/env python3
"""
PolicyProposalComments数取得APIのテストスクリプト
"""

import requests
import json
from datetime import datetime

# ベースURL
BASE_URL = "http://localhost:8000"

def test_comment_count_api():
    """特定の政策提案に対するPolicyProposalComments数取得APIのテスト"""
    print("=== 特定の政策提案に対するPolicyProposalComments数取得APIテスト ===")
    
    # テスト用の政策提案ID（実際のIDに置き換える必要があります）
    test_policy_id = "test-policy-001"
    
    try:
        response = requests.get(f"{BASE_URL}/api/policy-proposal-comments/policy-proposals/{test_policy_id}/comment-count")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("レスポンス:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print(f"政策提案ID: {data.get('policy_proposal_id', '')}")
            print(f"コメント数: {data.get('comment_count', 0)}")
        else:
            print(f"エラー: {response.text}")
            
    except Exception as e:
        print(f"エラー: {e}")
    
    print()

def test_server_health():
    """サーバーの健全性チェック"""
    print("=== サーバー健全性チェック ===")
    
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"レスポンス: {data}")
        else:
            print(f"エラー: {response.text}")
            
    except Exception as e:
        print(f"エラー: {e}")
    
    print()

def main():
    """メイン関数"""
    print("PolicyProposalComments数取得APIテスト開始")
    print(f"テスト対象URL: {BASE_URL}")
    print(f"テスト実行時刻: {datetime.now()}")
    print("=" * 50)
    
    # サーバー健全性チェック
    test_server_health()
    
    # コメント数取得APIテスト
    test_comment_count_api()
    
    print("テスト完了")

if __name__ == "__main__":
    main()
