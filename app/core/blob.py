from azure.storage.blob import BlobServiceClient
from uuid import uuid4
import os

AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_BLOB_CONTAINER = os.getenv("AZURE_BLOB_CONTAINER", "default-container")

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

# グローバル変数を初期化
blob_service_client = get_blob_service_client()
container_client = get_container_client()

def upload_video_to_blob(file, filename: str) -> str:
    if container_client is None:
        # Azure接続が設定されていない場合は、ローカルファイルパスを返す
        return f"local://{filename}"
    
    blob_client = container_client.get_blob_client(filename)
    blob_client.upload_blob(file, overwrite=True)
    return blob_client.url  # ←保存用URL