#!/usr/bin/env python3
"""
データベース接続テストスクリプト

使用方法:
python test_db_connection.py
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from app.db.database import engine
    from app.core.config import settings
    from sqlalchemy import text
    
    print("🔍 データベース接続をテスト中...")
    print(f"   ホスト: {settings.database_host}")
    print(f"   ポート: {settings.database_port}")
    print(f"   データベース: {settings.database_name}")
    print(f"   ユーザー: {settings.database_username}")
    
    # 接続テスト
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("✅ データベース接続成功！")
        
        # policy_tagsテーブルの存在確認
        try:
            result = connection.execute(text("SHOW TABLES LIKE 'policy_tags'"))
            tables = result.fetchall()
            if tables:
                print("✅ policy_tagsテーブルが存在します")
                
                # テーブル構造の確認
                result = connection.execute(text("DESCRIBE policy_tags"))
                columns = result.fetchall()
                print("📋 policy_tagsテーブルの構造:")
                for column in columns:
                    print(f"   - {column[0]}: {column[1]}")
                    
                # データ件数の確認
                result = connection.execute(text("SELECT COUNT(*) FROM policy_tags"))
                count = result.fetchone()[0]
                print(f"📊 policy_tagsテーブルのデータ件数: {count}件")
                
            else:
                print("⚠️  policy_tagsテーブルが存在しません")
                print("   以下のSQLでテーブルを作成してください:")
                print("""
CREATE TABLE policy_tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    embedding TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
                """)
                
        except Exception as e:
            print(f"❌ テーブル確認エラー: {str(e)}")
            
except ImportError as e:
    print(f"❌ インポートエラー: {str(e)}")
    print("   必要なパッケージがインストールされているか確認してください")
except Exception as e:
    print(f"❌ データベース接続エラー: {str(e)}")
    print("   環境変数の設定を確認してください")
