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