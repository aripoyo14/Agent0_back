import os
import uuid
from datetime import datetime
from typing import Optional
from io import BytesIO
from fastapi import UploadFile, HTTPException
from app.core.blob import upload_meeting_minutes_to_blob

# ファイル解析用ライブラリ
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

class FileUploadService:
    """ファイルアップロード処理サービス"""

    def __init__(self):
        self.allowed_extensions = {'.txt', '.doc', '.docx', '.pdf'}
        self.max_file_size = 10 * 1024 * 1024  # 10MB

    def validate_file(self, file: UploadFile) -> bool:
        """ファイルの妥当性をチェック"""
        # ファイルサイズチェック
        if file.size and file.size > self.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"ファイルサイズが大きすぎます。最大{self.max_file_size // (1024*1024)}MBまで"
            )

        # ファイル拡張子チェック
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in self.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"対応していないファイル形式です。対応形式: {', '.join(self.allowed_extensions)}"
            )

        return True

    def generate_filename(self, original_filename: str, meeting_id: str) -> str:
        """一意のファイル名を生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(original_filename)[1]
        unique_id = str(uuid.uuid4())[:8]
        
        return f"meetings/{meeting_id}/minutes_{timestamp}_{unique_id}{file_extension}"

    async def upload_minutes_file(self, file_content: bytes, filename: str, meeting_id: str) -> str:
        """議事録ファイルをアップロード"""
        # ファイル名を生成
        blob_filename = self.generate_filename(filename, meeting_id)

        try:
            # Azure Blob Storageにアップロード（面談録専用コンテナ）
            file_url = upload_meeting_minutes_to_blob(file_content, blob_filename)
            
            return file_url

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"ファイルアップロード中にエラーが発生しました: {str(e)}"
            )

    def extract_text_from_file(self, file_content: bytes, filename: str) -> str:
        """ファイルからテキストを抽出"""
        file_extension = os.path.splitext(filename)[1].lower()
        
        try:
            if file_extension == '.txt':
                # テキストファイル
                try:
                    return file_content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        return file_content.decode('shift_jis')
                    except UnicodeDecodeError:
                        return file_content.decode('utf-8', errors='ignore')
            
            elif file_extension == '.docx' and DOCX_AVAILABLE:
                # Wordファイル（.docx）
                doc = Document(BytesIO(file_content))
                text = []
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        text.append(paragraph.text)
                return '\n'.join(text)
            
            elif file_extension == '.pdf' and PDF_AVAILABLE:
                # PDFファイル
                pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
                text = []
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text.append(page_text)
                return '\n'.join(text)
            
            elif file_extension == '.doc':
                # 古いWordファイル（.doc）- 現在は未対応
                return f"[{filename}の内容を抽出中...] (.docファイルは現在未対応)"
            
            else:
                # 対応していないファイル形式
                if file_extension == '.docx' and not DOCX_AVAILABLE:
                    return f"[{filename}の内容を抽出中...] (python-docxライブラリがインストールされていません)"
                elif file_extension == '.pdf' and not PDF_AVAILABLE:
                    return f"[{filename}の内容を抽出中...] (PyPDF2ライブラリがインストールされていません)"
                else:
                    return f"[{filename}の内容を抽出中...] (対応していないファイル形式: {file_extension})"
        
        except Exception as e:
            return f"[{filename}の内容を抽出中...] (エラー: {str(e)})"

file_upload_service = FileUploadService()
