from azure.storage.blob import BlobServiceClient
from app.core.config import get_settings

settings = get_settings()
AZURE_CONNECTION_STRING = settings.azure_storage_connection_string
AZURE_BLOB_CONTAINER = settings.azure_blob_container
AZURE_MEETING_CONTAINER = settings.azure_meeting_container

# Azure接続文字列が設定されていない場合はNoneを返す関数を作成
def get_blob_service_client():
    if AZURE_CONNECTION_STRING:
        return BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    return None

def get_container_client():
    blob_client = get_blob_service_client()
    if blob_client:
        return blob_client.get_container_client(AZURE_BLOB_CONTAINER)
    return None

def get_meeting_container_client():
    blob_client = get_blob_service_client()
    if blob_client:
        return blob_client.get_container_client(AZURE_MEETING_CONTAINER)
    return None

# グローバル変数を初期化
blob_service_client = get_blob_service_client()
container_client = get_container_client()
meeting_container_client = get_meeting_container_client()

def upload_binary_to_blob(file, filename: str) -> str:
    if container_client is None:
        # Azure接続が設定されていない場合は、ローカルファイルパスを返す
        return f"local://{filename}"
    
    blob_client = container_client.get_blob_client(filename)
    blob_client.upload_blob(file, overwrite=True)
    return blob_client.url  # ←保存用URL

def upload_video_to_blob(file, filename: str) -> str:
    # 後方互換: 既存の動画アップロード呼び出しをサポート
    return upload_binary_to_blob(file, filename)

def upload_meeting_minutes_to_blob(file, filename: str) -> str:
    """面談録専用のアップロード関数"""
    if meeting_container_client is None:
        # Azure接続が設定されていない場合は、ローカルファイルパスを返す
        return f"local://{filename}"
    
    blob_client = meeting_container_client.get_blob_client(filename)
    blob_client.upload_blob(file, overwrite=True)
    return blob_client.url

def delete_blob(blob_name: str) -> bool:
    """Blobストレージからファイルを削除"""
    try:
        # Azure Blob Storageの削除処理
        # 実際の実装はAzure SDKを使用
        from azure.storage.blob import BlobServiceClient
        import os
        
        # 設定から接続文字列を取得
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "default")
        
        if not connection_string:
            print(f"⚠️ AZURE_STORAGE_CONNECTION_STRINGが設定されていません")
            return False
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        
        # Blobを削除
        blob_client.delete_blob()
        
        print(f"✅ Blobファイル削除成功: {blob_name}")
        return True
        
    except Exception as e:
        print(f"❌ Blobファイル削除失敗: {blob_name}, エラー: {e}")
        return False