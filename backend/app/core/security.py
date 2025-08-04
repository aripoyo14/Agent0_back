""" 
 - パスワードのハッシュ化および検証を行うモジュール。
 - セキュリティ上、パスワードを平文で保存せず、安全な形式で保存するために使用。
"""

from passlib.context import CryptContext

# bcryptアルゴリズムを使用するハッシュコンテキストを定義
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# パスワードをハッシュ化する関数 (与えられた平文パスワードを bcrypt でハッシュ化して返す)
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# 入力されたパスワードとハッシュ値を照合する関数
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)