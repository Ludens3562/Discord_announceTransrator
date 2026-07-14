"""PostgreSQL接続プールの生成とスキーマ初期化を提供するモジュール。

接続情報は環境変数から取得する。スキーマ初期化は冪等であり、
起動のたびに安全に実行できる。
"""

# 標準ライブラリ
import logging
import os

# サードパーティ
import asyncpg

# 設定可能な定数
DEFAULT_POSTGRES_PORT = 5432
POOL_MIN_SIZE = 1
POOL_MAX_SIZE = 5

logger = logging.getLogger(__name__)

# スキーマ定義（冪等）
_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS guild_settings (
        guild_id     BIGINT PRIMARY KEY,
        source_lang  TEXT NOT NULL DEFAULT 'EN',
        target_lang  TEXT NOT NULL DEFAULT 'JA',
        formality    TEXT NOT NULL DEFAULT 'more',
        provider     TEXT NOT NULL DEFAULT 'deepl',
        updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS monitored_channels (
        channel_id        BIGINT PRIMARY KEY,
        guild_id          BIGINT NOT NULL,
        provider_override TEXT,
        created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_monitored_channels_guild_id
        ON monitored_channels (guild_id);
    """,
)


class DatabaseConfigurationError(Exception):
    """データベース接続設定が不足・不正な場合に送出する例外。"""


async def create_pool() -> asyncpg.Pool:
    """環境変数からPostgreSQL接続プールを生成する。

    必要な環境変数:
        POSTGRES_HOST: 接続先ホスト名。
        POSTGRES_PORT: 接続先ポート番号（省略時は5432）。
        POSTGRES_USER: 接続ユーザー名。
        POSTGRES_PASSWORD: 接続パスワード。
        POSTGRES_DB: 接続先データベース名。

    Returns:
        生成した接続プール。

    Raises:
        DatabaseConfigurationError: 必須の環境変数が不足している場合、
            またはポート番号が整数として解釈できない場合。
    """
    host = os.getenv("POSTGRES_HOST")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    database = os.getenv("POSTGRES_DB")

    missing = [
        name
        for name, value in (
            ("POSTGRES_HOST", host),
            ("POSTGRES_USER", user),
            ("POSTGRES_PASSWORD", password),
            ("POSTGRES_DB", database),
        )
        if not value
    ]
    if missing:
        raise DatabaseConfigurationError(
            f"データベース接続に必要な環境変数が設定されていません: {', '.join(missing)}"
        )

    port_raw = os.getenv("POSTGRES_PORT", str(DEFAULT_POSTGRES_PORT))
    try:
        port = int(port_raw)
    except ValueError as error:
        raise DatabaseConfigurationError(
            f"POSTGRES_PORT が整数ではありません: {port_raw}"
        ) from error

    logger.info("データベース接続プールを作成します（host=%s, port=%s, db=%s）", host, port, database)
    pool: asyncpg.Pool = await asyncpg.create_pool(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        min_size=POOL_MIN_SIZE,
        max_size=POOL_MAX_SIZE,
    )
    logger.info("データベース接続プールを作成しました")
    return pool


async def init_schema(pool: asyncpg.Pool) -> None:
    """必要なテーブルとインデックスを冪等に作成する。

    Args:
        pool: スキーマ作成に使用する接続プール。
    """
    async with pool.acquire() as connection:
        async with connection.transaction():
            for statement in _SCHEMA_STATEMENTS:
                await connection.execute(statement)
    logger.info("データベーススキーマを初期化しました")
