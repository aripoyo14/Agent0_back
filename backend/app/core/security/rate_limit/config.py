"""
レート制限の設定管理
"""

from pydantic import BaseModel, Field
from typing import Dict, Any

class RateLimitConfig(BaseModel):
    """レート制限の設定"""
    
    # 基本設定
    enabled: bool = Field(default=True, description="レート制限を有効にするか")
    default_max_requests: int = Field(default=100, description="デフォルトの最大リクエスト数")
    default_window_seconds: int = Field(default=60, description="デフォルトの時間枠（秒）")
    
    # ログインAPIの制限（3回間違えると1分間ログインできない）
    auth_login_max_requests: int = Field(default=3, description="ログインの最大試行回数")
    auth_login_window_seconds: int = Field(default=60, description="ログイン制限の時間枠（秒）")
    
    # ユーザー登録系APIの制限（厳格）
    user_register_max_requests: int = Field(default=3, description="ユーザー登録の最大試行回数")
    user_register_window_seconds: int = Field(default=3600, description="ユーザー登録制限の時間枠（秒）")
    
    # ファイルアップロード系APIの制限（厳格）
    file_upload_max_requests: int = Field(default=10, description="ファイルアップロードの最大試行回数")
    file_upload_window_seconds: int = Field(default=60, description="ファイルアップロード制限の時間枠（秒）")
    
    # 投稿系APIの制限（適度）
    comment_post_max_requests: int = Field(default=20, description="コメント投稿の最大試行回数")
    comment_post_window_seconds: int = Field(default=60, description="コメント投稿制限の時間枠（秒）")
    
    # 読み取り系APIの制限（緩い）
    read_api_max_requests: int = Field(default=100, description="読み取りAPIの最大試行回数")
    read_api_window_seconds: int = Field(default=60, description="読み取りAPI制限の時間枠（秒）")
    
    # グローバル制限
    global_ip_max_requests: int = Field(default=1000, description="IPアドレス別のグローバル最大リクエスト数")
    global_ip_window_seconds: int = Field(default=3600, description="グローバル制限の時間枠（秒）")
    
    # 監査設定
    log_violations: bool = Field(default=True, description="レート制限違反をログに記録するか")
    block_violations: bool = Field(default=True, description="レート制限違反をブロックするか")
    
    # エラーメッセージ
    error_messages: Dict[str, str] = Field(
        default={
            "auth_login": "ログイン試行回数が上限に達しました。1分後に再試行してください。",
            "user_register": "ユーザー登録試行回数が上限に達しました。1時間後に再試行してください。",
            "file_upload": "ファイルアップロード回数が上限に達しました。1分後に再試行してください。",
            "comment_post": "コメント投稿回数が上限に達しました。1分後に再試行してください。",
            "read_api": "読み取りAPIの利用回数が上限に達しました。1分後に再試行してください。",
            "global_limit": "リクエスト回数が上限に達しました。1時間後に再試行してください。"
        },
        description="エンドポイント別のエラーメッセージ"
    )
    
    class Config:
        """Pydantic設定"""
        # env_prefix = "RATE_LIMIT_"  # この行を削除またはコメントアウト
        case_sensitive = False

# デフォルト設定インスタンス
# デフォルト設定インスタンス
default_config = RateLimitConfig(
    enabled=True,
    auth_login_max_requests=3,
    auth_login_window_seconds=60,
    user_register_max_requests=3,
    user_register_window_seconds=3600,
    file_upload_max_requests=10,
    file_upload_window_seconds=60,
    comment_post_max_requests=20,
    comment_post_window_seconds=60,
    read_api_max_requests=100,
    read_api_window_seconds=60,
    global_ip_max_requests=1000,
    global_ip_window_seconds=3600,
    log_violations=True,
    block_violations=True
)
