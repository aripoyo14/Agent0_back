# OpenAI関連のインポート
import re
import json
from fastapi import HTTPException
from openai import OpenAI
from app.core.startup import get_client
from app.services.file_analyzer import extract_file_content
from app.services.file_analyzer_full import extract_file_content_full

def generate_ai_reply(comment_text: str, attachments_info: list[dict] | None = None, persona: str | None = None, instruction: str | None = None) -> str:
    """
    コメント本文と添付ファイル情報に対して、指定のペルソナで日本語の返信案を生成する。
    失敗時は例外を投げる。
    """
    try:
        client = get_client()
        system_prompt = (
            "あなたは政策形成を支援するアシスタントです。"
            "相手を尊重し、簡潔かつ具体的で、建設的な日本語の返信を作成してください。"
            "添付ファイルがある場合は、その内容も考慮して返信してください。"
        )
        if persona:
            system_prompt += f" ペルソナ: {persona}."
        
        # 添付ファイル情報を構築（AI返信生成時は完全版を使用）
        attachments_text = ""
        if attachments_info:
            attachments_text = "\n\n添付ファイル:\n"
            for i, att in enumerate(attachments_info, 1):
                file_name = att.get('file_name', 'Unknown')
                file_type = att.get('file_type', 'Unknown type')
                file_url = att.get('file_url', '')
                
                # AI返信生成時は完全版でファイル内容を解析
                if file_url and file_type != 'Unknown type':
                    try:
                        file_analysis = extract_file_content_full(file_url, file_type, file_name)
                        attachments_text += f"{i}. {file_name} ({file_type})\n"
                        attachments_text += f"   内容: {file_analysis.get('summary', '読み取り失敗')}\n"
                        
                        # キーポイントがある場合は追加
                        if file_analysis.get('key_points'):
                            attachments_text += f"   キーポイント:\n"
                            for j, point in enumerate(file_analysis['key_points'][:5], 1):  # 最大5個まで
                                attachments_text += f"     - {point}\n"
                        
                        # 構造情報がある場合は追加
                        if file_analysis.get('structure'):
                            structure = file_analysis['structure']
                            if 'total_pages' in structure:
                                attachments_text += f"   ページ数: {structure['total_pages']}ページ\n"
                            elif 'total_sheets' in structure:
                                attachments_text += f"   シート数: {structure['total_sheets']}シート\n"
                            elif 'total_paragraphs' in structure:
                                attachments_text += f"   段落数: {structure['total_paragraphs']}段落\n"
                        
                        # 詳細内容（最初の1000文字まで）
                        if file_analysis.get('content'):
                            content_preview = file_analysis['content'][:1000]
                            if len(file_analysis['content']) > 1000:
                                content_preview += "..."
                            attachments_text += f"   詳細: {content_preview}\n"
                            
                    except Exception as e:
                        attachments_text += f"{i}. {file_name} ({file_type}) - 読み取りエラー: {str(e)}\n"
                else:
                    attachments_text += f"{i}. {file_name} ({file_type})\n"
            
            attachments_text += "\n※添付ファイルの内容とキーポイントを考慮して返信してください。"

        user_prompt = (
            "以下のコメントに丁寧に返信してください。必要なら提案や次のアクションも示してください。\n\n"
            f"コメント:\n{comment_text}{attachments_text}"
        )
        if instruction:
            user_prompt += f"\n\n追加指示: {instruction}"

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content
        return content.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def generate_summary(text: str) -> dict:
    try:
        # clientを取得
        client = get_client()
            
        prompt = f"""
        あなたはプロのコンサルタントです。以下の打ち合わせ議事録から会議タイトルと要約を作成し、以下のJSONスキーマで出力してください。
        JSONスキーマ：
        {{
            "title": "会議タイトル",
            "summary": "会議要約"
        }}
        
        打ち合わせ議事録：
        {text}
        """
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes text."},
                {"role": "user", "content": prompt}
            ],
        )
        content = response.choices[0].message.content
        
        # まず、コードブロック（```json ... ```）を除去
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'\s*```', '', content)
        
        # JSONをパースして辞書に変換
        try:
            summary_dict = json.loads(content)
            return summary_dict
        except json.JSONDecodeError:
            # JSONパースに失敗した場合のフォールバック
            return {
                "title": "会議要約",
                "summary": content
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))