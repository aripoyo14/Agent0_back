# OpenAI関連のインポート
import re
import json
from fastapi import HTTPException
from openai import OpenAI
from app.core.startup import get_client

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