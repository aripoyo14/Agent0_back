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
        
        # expertsテーブルの存在確認を追加
        try:
            result = connection.execute(text("SHOW TABLES LIKE 'experts'"))
            tables = result.fetchall()
            if tables:
                print("✅ expertsテーブルが存在します")
                
                # テーブル構造の確認
                result = connection.execute(text("DESCRIBE experts"))
                columns = result.fetchall()
                print("📋 expertsテーブルの構造:")
                for column in columns:
                    print(f"   - {column[0]}: {column[1]}")
                    
                # データ件数の確認
                result = connection.execute(text("SELECT COUNT(*) FROM experts"))
                count = result.fetchone()[0]
                print(f"📊 expertsテーブルのデータ件数: {count}件")
                
                # 登録したエキスパートの確認（実際に存在するメールアドレスでテスト）
                result = connection.execute(text("SELECT id, email, first_name, last_name, mfa_required, account_active FROM experts WHERE email = 'abe.nana@skywave.co.jp'"))
                expert = result.fetchone()
                if expert:
                    print(f"✅ 登録済みエキスパート: ID={expert[0]}, Email={expert[1]}, Name={expert[2]} {expert[3]}, MFA={expert[4]}, Active={expert[5]}")
                else:
                    print("⚠️  abe.nana@skywave.co.jp のエキスパートが見つかりません")
                
            else:
                print("⚠️  expertsテーブルが存在しません")
                print("   データベースマイグレーションが必要です")
                
        except Exception as e:
            print(f"❌ expertsテーブル確認エラー: {str(e)}")
            
        # threat_detectionsテーブルの存在確認と作成
        try:
            result = connection.execute(text("SHOW TABLES LIKE 'threat_detections'"))
            tables = result.fetchall()
            if tables:
                print("✅ threat_detectionsテーブルが存在します")
            else:
                print("⚠️  threat_detectionsテーブルが存在しません")
                print("   テーブルを作成中...")
                
                # threat_detectionsテーブルの作成
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS threat_detections (
                    id CHAR(36) PRIMARY KEY,
                    user_id CHAR(36) NOT NULL,
                    user_type VARCHAR(50) NOT NULL,
                    threat_type VARCHAR(100) NOT NULL,
                    threat_level ENUM('low', 'medium', 'high', 'critical') NOT NULL,
                    description TEXT,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    endpoint VARCHAR(255),
                    http_method VARCHAR(10),
                    request_data JSON,
                    response_data JSON,
                    confidence_score DECIMAL(5,2),
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP NULL,
                    status ENUM('active', 'resolved', 'false_positive') DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_user_id (user_id),
                    INDEX idx_threat_type (threat_type),
                    INDEX idx_threat_level (threat_level),
                    INDEX idx_detected_at (detected_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """
                
                connection.execute(text(create_table_sql))
                connection.commit()
                print("✅ threat_detectionsテーブルを作成しました")
                
        except Exception as e:
            print(f"❌ threat_detectionsテーブル確認・作成エラー: {str(e)}")
            
except ImportError as e:
    print(f"❌ インポートエラー: {str(e)}")
    print("   必要なパッケージがインストールされているか確認してください")
except Exception as e:
    print(f"❌ データベース接続エラー: {str(e)}")
    print("   環境変数の設定を確認してください")
