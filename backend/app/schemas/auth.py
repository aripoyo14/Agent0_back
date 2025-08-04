# app/schemas/auth.py
"""
 - ログインに関連するデータスキーマを定義するモジュール。
 - 主に FastAPI のログインAPI（POST /login）で使用される、
   入力（メールアドレス・パスワード）と出力（JWTトークン）の構造を定義する。
"""

from pydantic import BaseModel, EmailStr

# ログインAPIのリクエストボディ用スキーマ
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# ログイン成功時に返すトークン情報のレスポンススキーマ
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"