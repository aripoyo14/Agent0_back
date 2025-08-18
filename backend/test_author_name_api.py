#!/usr/bin/env python3
"""
コメント取得APIのテストスクリプト
投稿者名（author_name）が正しく取得されるかをテスト
"""

import requests
import json
from typing import List, Dict, Any

# APIベースURL
BASE_URL = "http://localhost:8000/api"

def test_get_comments_with_author_name():
    """
    コメント取得APIをテストして、author_nameフィールドが含まれているかを確認
    """
    print("=== コメント取得APIテスト ===")
    
    # 1. まず利用可能な政策提案を取得
    try:
        response = requests.get(f"{BASE_URL}/policy-proposals/")
        if response.status_code == 200:
            proposals = response.json()
            if proposals:
                # 最初の政策提案のIDを使用
                proposal_id = proposals[0]['id']
                print(f"テスト対象の政策提案ID: {proposal_id}")
                
                # 2. その政策提案のコメントを取得
                comments_response = requests.get(f"{BASE_URL}/policy-proposals/{proposal_id}/comments")
                
                if comments_response.status_code == 200:
                    comments = comments_response.json()
                    print(f"取得したコメント数: {len(comments)}")
                    
                    if comments:
                        # 最初のコメントの構造を確認
                        first_comment = comments[0]
                        print("\n=== 最初のコメントの構造 ===")
                        print(json.dumps(first_comment, indent=2, ensure_ascii=False))
                        
                        # author_nameフィールドの存在を確認
                        if 'author_name' in first_comment:
                            print(f"\n✅ author_nameフィールドが存在します: {first_comment['author_name']}")
                        else:
                            print("\n❌ author_nameフィールドが存在しません")
                        
                        # 全てのコメントでauthor_nameフィールドをチェック
                        all_have_author_name = all('author_name' in comment for comment in comments)
                        if all_have_author_name:
                            print("✅ 全てのコメントにauthor_nameフィールドが含まれています")
                        else:
                            print("❌ 一部のコメントにauthor_nameフィールドが含まれていません")
                            
                    else:
                        print("コメントが見つかりませんでした")
                else:
                    print(f"コメント取得エラー: {comments_response.status_code}")
                    print(comments_response.text)
            else:
                print("政策提案が見つかりませんでした")
        else:
            print(f"政策提案取得エラー: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ サーバーに接続できません。サーバーが起動しているか確認してください。")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

def test_alternative_comments_endpoint():
    """
    代替のコメント取得エンドポイントもテスト
    """
    print("\n=== 代替コメント取得APIテスト ===")
    
    try:
        # まず利用可能な政策提案を取得
        response = requests.get(f"{BASE_URL}/policy-proposals/")
        if response.status_code == 200:
            proposals = response.json()
            if proposals:
                proposal_id = proposals[0]['id']
                
                # 代替エンドポイントでコメントを取得
                comments_response = requests.get(f"{BASE_URL}/policy-proposal-comments/by-proposal/{proposal_id}")
                
                if comments_response.status_code == 200:
                    comments = comments_response.json()
                    print(f"代替エンドポイントで取得したコメント数: {len(comments)}")
                    
                    if comments:
                        first_comment = comments[0]
                        if 'author_name' in first_comment:
                            print(f"✅ 代替エンドポイントでもauthor_nameフィールドが存在します: {first_comment['author_name']}")
                        else:
                            print("❌ 代替エンドポイントでauthor_nameフィールドが存在しません")
                else:
                    print(f"代替エンドポイントエラー: {comments_response.status_code}")
                    
    except Exception as e:
        print(f"❌ 代替エンドポイントテストでエラーが発生しました: {e}")

if __name__ == "__main__":
    test_get_comments_with_author_name()
    test_alternative_comments_endpoint()
