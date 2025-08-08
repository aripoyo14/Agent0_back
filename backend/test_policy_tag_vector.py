#!/usr/bin/env python3
"""
Policy Tags ベクトル化機能のテストスクリプト

使用方法:
python test_policy_tag_vector.py
"""

import requests
import json
import time

# API ベースURL
BASE_URL = "http://localhost:8000/api/policy-tags"

def test_vectorize():
    """全タグベクトル化機能のテスト"""
    print("🔍 全タグベクトル化機能をテスト中...")
    
    try:
        response = requests.post(f"{BASE_URL}/vectorize")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 全タグベクトル化成功: {result['message']}")
            print(f"   処理件数: {result['processed_count']}")
            print(f"   ネームスペース: {result['namespace']}")
            return True
        else:
            print(f"❌ 全タグベクトル化失敗: {response.status_code}")
            print(f"   エラー: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 全タグベクトル化テストエラー: {str(e)}")
        return False

def test_single_vectorize(tag_id=1):
    """個別タグベクトル化機能のテスト"""
    print(f"🔍 個別タグベクトル化機能をテスト中... (ID: {tag_id})")
    
    try:
        response = requests.post(f"{BASE_URL}/vectorize/{tag_id}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 個別タグベクトル化成功: {result['message']}")
            print(f"   タグID: {result['tag_id']}")
            print(f"   ネームスペース: {result['namespace']}")
            return True
        else:
            print(f"❌ 個別タグベクトル化失敗: {response.status_code}")
            print(f"   エラー: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 個別タグベクトル化テストエラー: {str(e)}")
        return False

def test_search(query="AI"):
    """検索機能のテスト"""
    print(f"🔍 検索機能をテスト中... (クエリ: '{query}')")
    
    try:
        response = requests.get(f"{BASE_URL}/search?query={query}&top_k=3")
        
        if response.status_code == 200:
            results = response.json()
            print(f"✅ 検索成功: {len(results)}件の結果")
            
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result['tag_name']} (ID: {result['tag_id']}, スコア: {result['score']:.3f})")
            return True
        else:
            print(f"❌ 検索失敗: {response.status_code}")
            print(f"   エラー: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 検索テストエラー: {str(e)}")
        return False

def test_list():
    """全タグ取得機能のテスト"""
    print("📋 全タグ取得機能をテスト中...")
    
    try:
        response = requests.get(f"{BASE_URL}/list")
        
        if response.status_code == 200:
            results = response.json()
            print(f"✅ 全タグ取得成功: {len(results)}件のタグ")
            
            for i, tag in enumerate(results[:5], 1):  # 最初の5件のみ表示
                print(f"   {i}. {tag['name']} (ID: {tag['id']})")
            
            if len(results) > 5:
                print(f"   ... 他 {len(results) - 5}件")
            return True
        else:
            print(f"❌ 全タグ取得失敗: {response.status_code}")
            print(f"   エラー: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 全タグ取得テストエラー: {str(e)}")
        return False

def test_create():
    """タグ作成機能のテスト"""
    print("➕ タグ作成機能をテスト中...")
    
    try:
        test_tag_name = f"テストタグ_{int(time.time())}"
        response = requests.post(f"{BASE_URL}/create?name={test_tag_name}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ タグ作成成功: {result['data']['name']} (ID: {result['data']['id']})")
            return result['data']['id']
        else:
            print(f"❌ タグ作成失敗: {response.status_code}")
            print(f"   エラー: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ タグ作成テストエラー: {str(e)}")
        return None

def test_delete(tag_id):
    """タグ削除機能のテスト"""
    if not tag_id:
        print("⚠️  削除テストをスキップ（作成されたタグIDがありません）")
        return False
        
    print(f"🗑️  タグ削除機能をテスト中... (ID: {tag_id})")
    
    try:
        response = requests.delete(f"{BASE_URL}/delete/{tag_id}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ タグ削除成功: {result['message']}")
            return True
        else:
            print(f"❌ タグ削除失敗: {response.status_code}")
            print(f"   エラー: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ タグ削除テストエラー: {str(e)}")
        return False

def test_statistics():
    """統計情報取得機能のテスト"""
    print("📊 統計情報取得機能をテスト中...")
    
    try:
        response = requests.get(f"{BASE_URL}/statistics")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 統計情報取得成功:")
            print(f"   総ベクトル数: {result['total_vector_count']}")
            print(f"   政策タグベクトル数: {result['policy_tags_vector_count']}")
            print(f"   次元数: {result['dimension']}")
            print(f"   インデックス使用率: {result['index_fullness']:.2%}")
            print(f"   ネームスペース: {', '.join(result['namespaces'])}")
            return True
        else:
            print(f"❌ 統計情報取得失敗: {response.status_code}")
            print(f"   エラー: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 統計情報取得テストエラー: {str(e)}")
        return False

def main():
    """メイン関数"""
    print("🚀 Policy Tags ベクトル化機能のテストを開始します")
    print("=" * 60)
    
    # テスト結果を記録
    test_results = []
    
    # 1. 全タグベクトル化テスト
    test_results.append(("全タグベクトル化", test_vectorize()))
    print()
    
    # 2. 個別タグベクトル化テスト
    test_results.append(("個別タグベクトル化", test_single_vectorize(1)))
    print()
    
    # 3. 検索テスト
    test_results.append(("検索", test_search("AI")))
    print()
    
    # 4. 全タグ取得テスト
    test_results.append(("全タグ取得", test_list()))
    print()
    
    # 5. タグ作成テスト
    created_tag_id = test_create()
    test_results.append(("タグ作成", created_tag_id is not None))
    print()
    
    # 6. 統計情報取得テスト
    test_results.append(("統計情報取得", test_statistics()))
    print()
    
    # 7. タグ削除テスト
    test_results.append(("タグ削除", test_delete(created_tag_id)))
    print()
    
    # 結果サマリー
    print("=" * 60)
    print("📋 テスト結果サマリー:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 結果: {passed}/{total} テストが成功")
    
    if passed == total:
        print("🎉 全てのテストが成功しました！")
    else:
        print("⚠️  一部のテストが失敗しました。サーバーの状態を確認してください。")

if __name__ == "__main__":
    main()
