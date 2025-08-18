"""
暗号化サービスの使用例
"""
from .service import encryption_service

def example_usage():
    """暗号化サービスの基本的な使用例"""
    
    # 1. テキストデータの暗号化・復号化
    sensitive_text = "機密情報：パスワード123"
    print(f"元のテキスト: {sensitive_text}")
    
    encrypted_text = encryption_service.encrypt_data(sensitive_text)
    print(f"暗号化後: {encrypted_text}")
    
    decrypted_text = encryption_service.decrypt_data(encrypted_text)
    print(f"復号化後: {decrypted_text}")
    
    # 2. ファイルの暗号化・復号化
    test_file_path = "test_file.txt"
    encrypted_file_path = "test_file.encrypted"
    decrypted_file_path = "test_file_decrypted.txt"
    
    # テストファイルを作成
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("これは機密ファイルです。\n暗号化して保護します。")
    
    # ファイルを暗号化
    encrypted_data = encryption_service.encrypt_file(test_file_path)
    with open(encrypted_file_path, "wb") as f:
        f.write(encrypted_data)
    print(f"ファイル暗号化完了: {encrypted_file_path}")
    
    # ファイルを復号化
    with open(encrypted_file_path, "rb") as f:
        encrypted_file_data = f.read()
    
    encryption_service.decrypt_file(encrypted_file_data, decrypted_file_path)
    print(f"ファイル復号化完了: {decrypted_file_path}")
    
    # 復号化されたファイルの内容を確認
    with open(decrypted_file_path, "r", encoding="utf-8") as f:
        decrypted_content = f.read()
    print(f"復号化された内容: {decrypted_content}")

if __name__ == "__main__":
    example_usage()
