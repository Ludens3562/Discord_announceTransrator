"""翻訳BOT本体（TranslatorBot）を定義するモジュール。

DBプール・翻訳サービス・コマンドツリーの初期化は discord.py の
非同期フック `setup_hook` で行い、同期的なI/Oをコンストラクタに持たせない。
"""

# 標準ライブラリ
import logging
import os
from typing import Optional

# サードパーティ
import asyncpg
import discord
from discord.ext import commands

# ローカルモジュール
from app.commands.translate_group import TranslateGroup, handle_app_command_error
from app.db.pool import create_pool, init_schema
from app.db.repository import ConfigRepository
from app.message_handler import translate_and_reply
from app.providers.deepl_provider import DeepLProvider
from app.providers.google_provider import GoogleProvider
from app.providers.provider import Provider
from app.translation_service import TranslationService

logger = logging.getLogger(__name__)


class TranslatorBot(commands.Bot):
    """翻訳BOTのメインクラス。

    Attributes:
        pool: PostgreSQL接続プール。setup_hook で生成する。
        repository: 翻訳設定リポジトリ。
        translation_service: 翻訳サービス。
    """

    def __init__(self) -> None:
        """BOTを初期化する（外部I/Oは行わない）。"""
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

        self.pool: Optional[asyncpg.Pool] = None
        self.repository: Optional[ConfigRepository] = None
        self.translation_service: Optional[TranslationService] = None

    async def setup_hook(self) -> None:
        """非同期初期化フック。DB・翻訳サービス・コマンドツリーを構築する。"""
        self.pool = await create_pool()
        await init_schema(self.pool)
        self.repository = ConfigRepository(self.pool)
        self.translation_service = TranslationService(self._build_providers())

        self.tree.add_command(TranslateGroup())
        self.tree.on_error = handle_app_command_error
        logger.info("コマンドツリーを構築しました")

    def _build_providers(self) -> dict[str, Provider]:
        """環境変数に応じて利用可能な翻訳プロバイダーを構築する。

        Returns:
            プロバイダー名からインスタンスへの辞書。
        """
        providers: dict[str, Provider] = {}

        deepl_api_key = os.getenv("DEEPL_API_KEY")
        if deepl_api_key:
            providers["deepl"] = DeepLProvider(api_key=deepl_api_key)
        else:
            logger.warning("DEEPL_API_KEY が未設定のため DeepL プロバイダーを無効化します")

        # Google（googletrans）はAPIキー不要のため常に登録する
        providers["google"] = GoogleProvider()

        logger.info("翻訳プロバイダーを構築しました: %s", ", ".join(sorted(providers.keys())))
        return providers

    async def on_ready(self) -> None:
        """BOT起動完了時の処理。コマンドを同期する。"""
        if self.user is not None:
            logger.info("ログインしました: %s", self.user.name)
        await self.change_presence(activity=discord.Game(name="WATCHING CHANNELS"))

        dev_guild_id = os.getenv("DEV_GUILD_ID")
        if dev_guild_id:
            try:
                guild = discord.Object(id=int(dev_guild_id))
                synced = await self.tree.sync(guild=guild)
                logger.info("開発ギルド %s に %d 個のコマンドを同期しました", dev_guild_id, len(synced))
            except (discord.HTTPException, ValueError) as error:
                logger.error("開発ギルドへのコマンド同期に失敗しました: %s", error)
        else:
            try:
                synced = await self.tree.sync()
                logger.info("グローバルに %d 個のコマンドを同期しました", len(synced))
            except discord.HTTPException as error:
                logger.error("グローバルコマンド同期に失敗しました: %s", error)

    async def on_message(self, message: discord.Message) -> None:
        """メッセージ受信時の処理。監視対象なら翻訳して返信する。

        Args:
            message: 受信したメッセージ。
        """
        if message.author == self.user:
            return
        if self.repository is None or self.translation_service is None:
            return
        await translate_and_reply(message, self.repository, self.translation_service)

    async def close(self) -> None:
        """BOT終了時にDB接続プールを閉じる。"""
        if self.pool is not None:
            await self.pool.close()
            logger.info("データベース接続プールを閉じました")
        await super().close()
