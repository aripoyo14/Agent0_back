# app/core/jwt.py
"""
 - JWT（JSON Web Token）を生成・検証するユーティリティモジュール。
 - ユーザーのログイン認証後にトークンを発行し、
   認証付きルートではトークンを検証してユーザー情報を取得する。
"""

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from app.core.config import settings

# 設定値の読み込み
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# アクセストークンを生成する関数 (指定されたデータを元にJWTアクセストークンを生成して返す。)
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt  # JWTトークン文字列を返す

# JWTトークンを検証し、有効であればペイロードを返す関数 (無効な場合は None を返す。)
def verify_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# JWTトークンをデコードしてペイロードを返す関数 (verify_access_tokenのエイリアスとして使用)
def decode_access_token(token: str) -> dict | None:
    return verify_access_token(token)
