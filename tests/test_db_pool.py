"""create_pool の環境変数バリデーションに関する単体テスト。

実データベースへは接続せず、必須環境変数が欠けた場合の異常系のみ検証する。
"""

# 標準ライブラリ
import asyncio

# サードパーティ
import pytest

# ローカルモジュール
from app.db.pool import DatabaseConfigurationError, create_pool


def test_create_pool_raises_when_env_missing(monkeypatch):
    """必須環境変数が未設定の場合に DatabaseConfigurationError を送出することを確認する（異常系）。"""
    for name in ("POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(DatabaseConfigurationError):
        asyncio.run(create_pool())


def test_create_pool_raises_on_invalid_port(monkeypatch):
    """POSTGRES_PORT が整数でない場合に DatabaseConfigurationError を送出することを確認する（異常系）。"""
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_USER", "user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pass")
    monkeypatch.setenv("POSTGRES_DB", "disbot")
    monkeypatch.setenv("POSTGRES_PORT", "not-a-number")

    with pytest.raises(DatabaseConfigurationError):
        asyncio.run(create_pool())
