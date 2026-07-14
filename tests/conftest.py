"""テスト共通のフィクスチャとフェイク実装を提供するモジュール。

実データベースやネットワークには接続せず、すべてフェイクで代替する。
"""

# 標準ライブラリ
from typing import Any, Optional

# サードパーティ
import pytest


class FakePool:
    """asyncpg.Pool の最小フェイク。

    呼び出された SQL と引数を記録し、あらかじめ設定した結果を返す。

    Attributes:
        calls: (メソッド名, SQL, 引数タプル) の呼び出し履歴。
        fetchrow_result: fetchrow が返す1行（dict）またはNone。
        fetch_result: fetch が返す行のリスト。
        execute_result: execute が返すステータス文字列。
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, tuple[Any, ...]]] = []
        self.fetchrow_result: Optional[dict[str, Any]] = None
        self.fetch_result: list[dict[str, Any]] = []
        self.execute_result: str = "EXECUTE"

    async def fetchrow(self, sql: str, *args: Any) -> Optional[dict[str, Any]]:
        """fetchrow のフェイク実装。"""
        self.calls.append(("fetchrow", sql, args))
        return self.fetchrow_result

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        """fetch のフェイク実装。"""
        self.calls.append(("fetch", sql, args))
        return self.fetch_result

    async def execute(self, sql: str, *args: Any) -> str:
        """execute のフェイク実装。"""
        self.calls.append(("execute", sql, args))
        return self.execute_result


@pytest.fixture
def fake_pool() -> FakePool:
    """新しい FakePool インスタンスを返すフィクスチャ。"""
    return FakePool()
