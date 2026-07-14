"""翻訳設定の永続化を担うリポジトリ層を提供するモジュール。

`ConfigRepository` はギルド設定と監視チャンネル設定へのCRUD操作を提供する。
SQLはカラム名を動的に組み立てず、静的な文で記述する。
"""

# 標準ライブラリ
import logging
from typing import Optional

# サードパーティ
import asyncpg

# ローカルモジュール
from app.db.models import ChannelTranslationSettings, GuildSettings

logger = logging.getLogger(__name__)

# 設定可能な定数（ギルド行が存在しない場合のフォールバック値）
DEFAULT_SOURCE_LANG = "EN"
DEFAULT_TARGET_LANG = "JA"
DEFAULT_FORMALITY = "more"
DEFAULT_PROVIDER = "deepl"


class ConfigRepository:
    """翻訳設定をPostgreSQLに永続化するリポジトリ。

    Attributes:
        pool: データベース接続プール。
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        """リポジトリを初期化する。

        Args:
            pool: 使用する接続プール。
        """
        self.pool: asyncpg.Pool = pool

    async def get_channel_translation_settings(
        self, channel_id: int
    ) -> Optional[ChannelTranslationSettings]:
        """監視チャンネルの解決済み翻訳設定を1回のクエリで取得する。

        `on_message` のホットパスで使用する。チャンネル上書きとギルド既定の
        優先順位はSQLのCOALESCEで解決する。

        Args:
            channel_id: 対象チャンネルID。

        Returns:
            監視対象の場合は解決済み設定。監視対象外の場合はNone。
        """
        row = await self.pool.fetchrow(
            """
            SELECT
                mc.channel_id,
                mc.guild_id,
                COALESCE(gs.source_lang, $2) AS source_lang,
                COALESCE(gs.target_lang, $3) AS target_lang,
                COALESCE(gs.formality, $4)   AS formality,
                COALESCE(mc.provider_override, gs.provider, $5) AS provider
            FROM monitored_channels mc
            LEFT JOIN guild_settings gs ON gs.guild_id = mc.guild_id
            WHERE mc.channel_id = $1;
            """,
            channel_id,
            DEFAULT_SOURCE_LANG,
            DEFAULT_TARGET_LANG,
            DEFAULT_FORMALITY,
            DEFAULT_PROVIDER,
        )
        if row is None:
            return None
        return ChannelTranslationSettings(
            channel_id=row["channel_id"],
            guild_id=row["guild_id"],
            source_lang=row["source_lang"],
            target_lang=row["target_lang"],
            formality=row["formality"],
            provider=row["provider"],
        )

    async def add_monitored_channel(self, channel_id: int, guild_id: int) -> bool:
        """監視チャンネルを追加する。

        Args:
            channel_id: 追加するチャンネルID。
            guild_id: チャンネルが属するギルドID。

        Returns:
            新規に追加した場合はTrue。既に監視対象だった場合はFalse。
        """
        row = await self.pool.fetchrow(
            """
            INSERT INTO monitored_channels (channel_id, guild_id)
            VALUES ($1, $2)
            ON CONFLICT (channel_id) DO NOTHING
            RETURNING channel_id;
            """,
            channel_id,
            guild_id,
        )
        return row is not None

    async def remove_monitored_channel(self, channel_id: int) -> bool:
        """監視チャンネルを削除する。

        Args:
            channel_id: 削除するチャンネルID。

        Returns:
            削除した場合はTrue。監視対象でなかった場合はFalse。
        """
        row = await self.pool.fetchrow(
            """
            DELETE FROM monitored_channels
            WHERE channel_id = $1
            RETURNING channel_id;
            """,
            channel_id,
        )
        return row is not None

    async def list_monitored_channels(self, guild_id: int) -> list[int]:
        """ギルド内の監視チャンネルID一覧を取得する。

        Args:
            guild_id: 対象ギルドID。

        Returns:
            監視チャンネルIDのリスト。
        """
        rows = await self.pool.fetch(
            """
            SELECT channel_id
            FROM monitored_channels
            WHERE guild_id = $1
            ORDER BY created_at;
            """,
            guild_id,
        )
        return [row["channel_id"] for row in rows]

    async def set_channel_provider_override(
        self, channel_id: int, provider: Optional[str]
    ) -> bool:
        """監視チャンネルのプロバイダー上書きを設定または解除する。

        Args:
            channel_id: 対象チャンネルID。
            provider: 設定するプロバイダー名。Noneの場合は上書きを解除する。

        Returns:
            対象チャンネルが監視対象で更新した場合はTrue。
            監視対象でなかった場合はFalse。
        """
        row = await self.pool.fetchrow(
            """
            UPDATE monitored_channels
            SET provider_override = $2
            WHERE channel_id = $1
            RETURNING channel_id;
            """,
            channel_id,
            provider,
        )
        return row is not None

    async def get_guild_settings(self, guild_id: int) -> GuildSettings:
        """ギルド設定を取得する。

        行が存在しない場合はハードコードされたデフォルト値を返し、
        レコードは新規作成しない（遅延作成）。

        Args:
            guild_id: 対象ギルドID。

        Returns:
            ギルド設定。行が無い場合はデフォルト値を持つ設定。
        """
        row = await self.pool.fetchrow(
            """
            SELECT guild_id, source_lang, target_lang, formality, provider
            FROM guild_settings
            WHERE guild_id = $1;
            """,
            guild_id,
        )
        if row is None:
            return GuildSettings(
                guild_id=guild_id,
                source_lang=DEFAULT_SOURCE_LANG,
                target_lang=DEFAULT_TARGET_LANG,
                formality=DEFAULT_FORMALITY,
                provider=DEFAULT_PROVIDER,
            )
        return GuildSettings(
            guild_id=row["guild_id"],
            source_lang=row["source_lang"],
            target_lang=row["target_lang"],
            formality=row["formality"],
            provider=row["provider"],
        )

    async def upsert_guild_language(
        self, guild_id: int, source_lang: str, target_lang: str
    ) -> None:
        """ギルドの翻訳元・翻訳先言語を設定する。

        Args:
            guild_id: 対象ギルドID。
            source_lang: 翻訳元言語コード。
            target_lang: 翻訳先言語コード。
        """
        await self.pool.execute(
            """
            INSERT INTO guild_settings (guild_id, source_lang, target_lang)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id) DO UPDATE
            SET source_lang = EXCLUDED.source_lang,
                target_lang = EXCLUDED.target_lang,
                updated_at = now();
            """,
            guild_id,
            source_lang,
            target_lang,
        )

    async def upsert_guild_formality(self, guild_id: int, formality: str) -> None:
        """ギルドの敬語レベルを設定する。

        Args:
            guild_id: 対象ギルドID。
            formality: 敬語レベル。
        """
        await self.pool.execute(
            """
            INSERT INTO guild_settings (guild_id, formality)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE
            SET formality = EXCLUDED.formality,
                updated_at = now();
            """,
            guild_id,
            formality,
        )

    async def upsert_guild_provider(self, guild_id: int, provider: str) -> None:
        """ギルドの既定プロバイダーを設定する。

        Args:
            guild_id: 対象ギルドID。
            provider: プロバイダー名。
        """
        await self.pool.execute(
            """
            INSERT INTO guild_settings (guild_id, provider)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE
            SET provider = EXCLUDED.provider,
                updated_at = now();
            """,
            guild_id,
            provider,
        )
